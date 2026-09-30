"""A Run is one play-through of a game mode: it owns the loadout, the progress and the flow between scenes."""
from . import campaign
from .achievements import stage_check
from .campaign import STORY_STAGES, STAGES_PER_SECTOR
from .i18n import i18n
from .scenes.base import sequence
from .settings import DIFFICULTIES
from .weapons import Loadout

GLITCH_BY_SECTOR = (0.0, 0.0, 0.03, 0.06, 0.16, 0.24)


class Run:
    def __init__(self, app, mode, difficulty, players, story=None):
        self.app = app
        self.mode = mode
        self.difficulty = difficulty
        self.cfg = DIFFICULTIES[difficulty]
        self.players = 2 if players == 2 else 1
        self.story = story
        if story is not None:
            self.loadout = Loadout.from_story(story)
            self.index = story["stage"]
            self.loop = story.get("loop", 1)
        else:
            self.loadout = Loadout(["BLASTER"] if mode != "HORDE" else [])
            self.index = 0
            self.loop = 1
        self.ta_level = 1
        self.carry = {}
        self.score = 0
        self.kills = 0
        self.frames = 0
        self.best_combo = 0
        self.stages = 0
        self.record = False
        self.finished = False

    # ---- specs --------------------------------------------------------------------------
    def spec(self):
        m = self.mode
        if m == "STORY":
            return campaign.story_spec(self.index, self.loop)
        if m == "ENDLESS":
            return campaign.endless_spec(1)
        if m == "TIME_ATTACK":
            return campaign.time_attack_spec(self.ta_level, self.carry)
        if m == "BOSS_RUSH":
            return campaign.boss_rush_spec(self.index)
        return campaign.horde_spec(self.index + 1)

    @property
    def sector(self):
        return self.spec().sector

    # ---- dialogue helpers --------------------------------------------------------------------
    def dialogue(self, key, once=True):
        """A scene factory for a story dialogue - or None when it doesn't exist or was already seen."""
        from .scenes.story import DialogueScene
        if not i18n.has_scene(key):
            return None
        if once and self.story is not None:
            if key in self.story["seen"]:
                return None
            self.story["seen"].append(key)
        lines = i18n.scene(key)
        if not lines:
            return None
        sector = min(self.index, STORY_STAGES - 1) // STAGES_PER_SECTOR if self.mode == "STORY" else 0
        return lambda done: DialogueScene(self.app, lines, done, sector=sector, glitch=GLITCH_BY_SECTOR[sector])

    # ---- flow ------------------------------------------------------------------------------------
    def begin(self):
        if self.mode == "STORY":
            sequence(self.app, self.story_intro())
        else:
            self.play_next()

    def play_next(self):
        from .scenes.play import PlayScene
        self.app.go(PlayScene(self.app, self, self.spec()))

    def story_intro(self):
        """Everything shown before the current story stage, ending with the stage itself."""
        from .scenes.play import PlayScene
        from .scenes.story import SectorCard
        idx = min(self.index, STORY_STAGES - 1)
        sector, k = divmod(idx, STAGES_PER_SECTOR)
        out = []
        if idx == 0:
            f = self.dialogue("prologue")
            if f:
                out.append(f)
        if k == 0:
            out.append(lambda done, s=sector: SectorCard(self.app, s, done))
            f = self.dialogue("s%d_intro" % (sector + 1))
            if f:
                out.append(f)
        if k == STAGES_PER_SECTOR - 1:
            f = self.dialogue("s%d_boss_intro" % (sector + 1))
            if f:
                out.append(f)
        spec = self.spec()
        out.append(lambda done: PlayScene(self.app, self, spec))
        return out

    def absorb(self, world, cleared):
        """Fold a finished stage into the statistics and the run totals."""
        st = self.app.save
        st.add_stat("kills", world.kills)
        st.add_stat("fragments", world.fragments)
        st.add_stat("dashes", world.dashes)
        st.add_stat("grazes", world.grazes)
        st.add_stat("playtime", world.time / 60.0)
        st.max_stat("best_combo", world.best_combo)
        if cleared and world.spec.kind == "boss":
            st.add_stat("bosses")
        if not cleared:
            st.add_stat("deaths")
        self.score += world.score
        self.kills += world.kills
        self.frames += world.time
        self.best_combo = max(self.best_combo, world.best_combo)
        if cleared:
            self.stages += 1
        stage_check(self.app, self, world, cleared)

    def save_story(self):
        if self.story is None:
            return
        self.loadout.to_story(self.story)
        self.story["stage"] = min(self.index, STORY_STAGES - 1)
        self.app.save.data["story"] = self.story
        self.app.save.save()

    # ---- stage results -----------------------------------------------------------------------------
    def stage_won(self, world):
        from .scenes.results import ResultsScene
        from .scenes.shop import ShopScene
        app = self.app
        self.absorb(world, True)
        mode = self.mode
        if mode == "STORY":
            cleared = self.index
            sector, k = divmod(cleared, STAGES_PER_SECTOR)
            self.index += 1
            factories = [lambda done: ResultsScene(app, self, world, done)]
            if cleared == 0:
                self.loadout.grant("BLASTER")
                f = self.dialogue("weapon_unlock")
                if f:
                    factories.append(f)
            if k == 1:
                f = self.dialogue("s%d_mid" % (sector + 1))
                if f:
                    factories.append(f)
            if k == STAGES_PER_SECTOR - 1:
                f = self.dialogue("s%d_boss_defeat" % (sector + 1))
                if f:
                    factories.append(f)
            if cleared >= STORY_STAGES - 1:
                from .scenes.story import EndingScene
                self.finished = True
                self.save_story()
                factories.append(lambda done: EndingScene(app, self))
                sequence(app, factories)
                return
            self.save_story()
            factories.append(lambda done: ShopScene(app, self, done))
            factories.extend(self.story_intro())
            sequence(app, factories)
        elif mode == "TIME_ATTACK":
            rules = world.rules
            self.carry = {"time_left": rules.time_left, "kills": rules.kills_before + world.kills}
            self.ta_level += 1
            self.play_next()
        else:                                        # BOSS_RUSH / HORDE
            self.index += 1
            from .scenes.play import PlayScene
            spec = self.spec()
            sequence(app, [lambda done: ResultsScene(app, self, world, done), lambda done: ShopScene(app, self, done),
                           lambda done: PlayScene(app, self, spec)])

    def stage_failed(self, world):
        from .scenes.results import GameOverScene, SummaryScene
        self.absorb(world, False)
        self.app.save.save()
        if self.mode == "STORY":
            self.app.go(GameOverScene(self.app, self, world))
        else:
            extra = {"stage": self.index + 1 if self.mode != "TIME_ATTACK" else self.ta_level, "time": int(self.frames / 60)}
            self.record = self.app.save.submit_score(self.mode, self.difficulty, self.score, extra)
            self.app.save.save()
            self.app.go(SummaryScene(self.app, self, world))

    def retry(self):
        """Story: play the failed stage again."""
        sequence(self.app, self.story_intro())

    def finish_story(self, choice):
        """After the ending: unlock achievements and roll the story over into a New Game+ loop."""
        app = self.app
        app.unlock("loop_breaker" if choice == "break" else "loop_keeper")
        app.save.add_stat("loops")
        carry = dict(self.story) if self.story else None
        app.save.start_story(self.difficulty, self.players, self.loop + 1, carry)
        app.save.save()

    def quit_to_menu(self):
        from .scenes.title import MainMenu
        self.app.go(MainMenu(self.app))
