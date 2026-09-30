"""Mode rules: what spawns, what wins the stage and what the HUD shows."""
from . import gfx
from .campaign import BOSS_ORDER, SECTORS, endless_spec

FRAMES = 60


class Rules:
    def __init__(self, world):
        self.w = world
        self.spec = world.spec
        self.win_timer = 0
        self.tier = 0                  # time-attack weapon tier

    # ---- hooks -----------------------------------------------------------
    def start(self):
        pass

    def update(self):
        pass

    def on_kill(self, enemy):
        pass

    def on_fragment(self):
        pass

    def on_boss_dead(self, boss):
        pass

    def hud(self):
        return {"label": "", "sub": "", "progress": None}

    # ---- helpers ----------------------------------------------------------
    def spawn_rate(self):
        return self.w.cfg["spawn"] + 0.0016 * self.w.level

    def spawn_step(self, cap=None, weights=None, rate=None):
        w = self.w
        cap = self.spec.max_enemies if cap is None else cap
        if self.win_timer > 0 or w.state != "playing" or len(w.enemies) >= cap:
            return
        if w.rng.random() < (self.spawn_rate() if rate is None else rate):
            weights = weights or self.spec.weights
            kinds = list(weights)
            kind = w.rng.choices(kinds, weights=[weights[k] for k in kinds])[0]
            elite = self.spec.elite_chance > 0 and kind != "comet" and w.rng.random() < self.spec.elite_chance
            w.spawn_enemy(kind, elite=elite)

    def power_spawn(self, chance=0.0009):
        w = self.w
        if self.win_timer == 0 and w.rng.random() < chance and len([p for p in w.pickups if p.kind == "power"]) < 2:
            pt = w.free_point(100)
            w.spawn_pickup("power", pt.x, pt.y, w.random_power(), life=900)

    def begin_win(self, delay=50):
        """Stage cleared: pop what is left, then hand over to the scene."""
        w = self.w
        if self.win_timer:
            return
        self.win_timer = delay
        for e in w.enemies[:]:
            w.fx.explosion(e.pos.x, e.pos.y, e.color, 0.8)
        w.enemies.clear()
        w.ebullets.clear()
        w.hazards.clear()
        w.emit("sfx", "clear")
        w.emit("stage_clear")

    def tick_win(self):
        if self.win_timer > 0:
            self.win_timer -= 1
            if self.win_timer == 0:
                self.w.state = "won"


class StoryRules(Rules):
    """Collect N golden fragments while the sector's enemies hunt you."""

    def start(self):
        self.w.spawn_fragment()

    def update(self):
        self.tick_win()
        self.spawn_step()
        self.power_spawn()

    def on_fragment(self):
        w = self.w
        if w.fragments >= self.spec.goal:
            self.begin_win()
        else:
            w.spawn_fragment()

    def hud(self):
        goal = max(1, self.spec.goal)
        return {"label": "SYNC", "sub": "%d / %d" % (min(self.w.fragments, goal), goal), "progress": min(1.0, self.w.fragments / goal)}


class BossRules(Rules):
    def start(self):
        w = self.w
        w.spawn_boss(self.spec.boss, self.spec.boss_scale * w.cfg["boss"])

    def update(self):
        w = self.w
        self.tick_win()
        if w.boss is not None and not w.boss.dying and self.spec.max_enemies:
            self.spawn_step(cap=min(self.spec.max_enemies, 3), rate=0.0035)
        self.power_spawn(0.0006)

    def on_boss_dead(self, boss):
        w = self.w
        w.add_coins(50)
        w.add_score(5000 * (self.spec.sector + 1) * (1 + self.spec.index // 6 if self.spec.mode == "BOSS_RUSH" else 1), boss.pos.xy, gfx.GOLD)
        w.fx.text(boss.pos.x, boss.pos.y - 40, "+50", gfx.GOLD, 26)
        for dx in (-40, 40):
            w.spawn_pickup("heart", boss.pos.x + dx, boss.pos.y + 30, life=1200)
        w.emit("boss_dead", boss.id)
        self.begin_win(70)

    def hud(self):
        return {"label": "BOSS", "sub": "", "progress": None}


class EndlessRules(Rules):
    """Survive. Every 40 seconds the level rises; every 3 levels the sector changes; bosses drop in every 6."""
    LEVEL_FRAMES = 2400

    def start(self):
        self.level = 1
        self.frames = 0
        self.total_frames = 0

    def update(self):
        w = self.w
        self.total_frames += 1
        if w.boss is None:
            self.frames += 1
            if self.frames >= self.LEVEL_FRAMES:
                self.level_up()
            self.spawn_step(cap=self.spec.max_enemies, rate=self.spawn_rate())
        else:
            self.spawn_step(cap=3, rate=0.004, weights={"drone": 70, "comet": 30})
        if self.total_frames % 30 == 0:
            w.add_score(self.level, None, popup=False)
        self.power_spawn(0.0012)

    def level_up(self):
        w = self.w
        old_sector = w.sector
        self.level += 1
        self.frames = 0
        w.level = self.level
        w.spec = self.spec = endless_spec(self.level)
        w.enemies_shoot = w.spec.shooting
        w.add_coins(3 + self.level // 2)
        w.emit("level", self.level)
        w.emit("sfx", "level")
        if w.spec.sector != old_sector:
            w.load_sector(w.spec.sector)
        if self.level % 6 == 0:
            n = self.level // 6 - 1
            w.spawn_boss(BOSS_ORDER[n % SECTORS], (1.0 + 0.3 * (n // SECTORS)) * w.cfg["boss"])

    def on_boss_dead(self, boss):
        w = self.w
        w.add_coins(50)
        w.add_score(3000 * self.level, boss.pos.xy, gfx.GOLD)
        for dx in (-40, 40):
            w.spawn_pickup("heart", boss.pos.x + dx, boss.pos.y + 30, life=1200)
        w.emit("boss_dead", boss.id)

    def hud(self):
        secs = self.total_frames // FRAMES
        return {"label": "LEVEL %d" % self.level, "sub": "%02d:%02d" % (secs // 60, secs % 60),
                "progress": self.frames / self.LEVEL_FRAMES}


class TimeAttackRules(Rules):
    """Race the clock: fragments and kills buy time, every level asks for more fragments."""

    def start(self):
        w = self.w
        carry = self.spec.carry
        self.time_left = carry.get("time_left", 180 * FRAMES)
        self.kills_before = carry.get("kills", 0)
        self.tier = min(4, self.kills_before // 10)
        self.timed_out = False
        w.spawn_fragment()

    def update(self):
        w = self.w
        self.tick_win()
        if self.win_timer == 0:
            self.time_left -= 1
            if self.time_left <= 0:
                self.time_left = 0
                self.timed_out = True
                w.state = "failed"
                w.emit("timeout")
                return
            if self.time_left in (600, 300, 180, 120, 60):
                w.emit("sfx", "tick")
        self.spawn_step()
        self.power_spawn(0.0012)

    def on_kill(self, enemy):
        self.time_left += FRAMES
        total = self.kills_before + self.w.kills
        tier = min(4, total // 10)
        if tier > self.tier:
            self.tier = tier
            self.w.emit("tier", tier)
            self.w.emit("sfx", "level")
            self.w.fx.text(self.w.players[0].pos.x, self.w.players[0].pos.y - 40, "WEAPON UP!", gfx.GOLD, 20)

    def on_fragment(self):
        w = self.w
        self.time_left += 3 * FRAMES
        if w.fragments >= self.spec.goal:
            self.time_left += 10 * FRAMES
            self.begin_win(40)
        else:
            w.spawn_fragment()

    def hud(self):
        goal = max(1, self.spec.goal)
        secs = self.time_left / FRAMES
        return {"label": "%02d:%04.1f" % (int(secs // 60), secs % 60), "sub": "%d / %d" % (min(self.w.fragments, goal), goal),
                "progress": min(1.0, self.w.fragments / goal), "danger": self.time_left < 15 * FRAMES}


class HordeRules(Rules):
    """Ten waves of enemies; the plasma mace is your only weapon."""
    WAVES = 10

    def start(self):
        self.wave = 0
        self.remaining = 0
        self.break_timer = 100
        self.frame = 0

    def wave_size(self, wave):
        return 5 + self.spec.index * 2 + wave * 3

    def update(self):
        w = self.w
        self.tick_win()
        if self.win_timer:
            return
        self.frame += 1
        if self.break_timer > 0:
            self.break_timer -= 1
            if self.break_timer == 0:
                self.wave += 1
                self.remaining = self.wave_size(self.wave)
                w.emit("wave", self.wave)
                w.emit("sfx", "level")
            return
        alive = len(w.enemies)
        if self.remaining > 0 and alive < self.spec.max_enemies and self.frame % 10 == 0:
            for _ in range(min(3, self.remaining, self.spec.max_enemies - alive)):
                kinds = list(self.spec.weights)
                kind = w.rng.choices(kinds, weights=[self.spec.weights[k] for k in kinds])[0]
                elite = (self.wave in (5, 10) and kind != "comet" and w.rng.random() < 0.3) or \
                    (self.spec.elite_chance and w.rng.random() < self.spec.elite_chance and kind != "comet")
                w.spawn_enemy(kind, elite=elite)
                self.remaining -= 1
        if self.remaining == 0 and alive == 0 and self.wave > 0:
            w.add_coins(3 + self.wave)
            w.fx.text(w.players[0].pos.x, w.players[0].pos.y - 40, "WAVE CLEAR", gfx.GREEN, 20)
            if self.wave >= self.WAVES:
                self.begin_win(60)
            else:
                self.break_timer = 150
                for p in w.alive_players():
                    p.energy = min(100.0, p.energy + 25)
        self.power_spawn(0.0010)

    def hud(self):
        total = self.wave_size(self.wave) if self.wave else 1
        left = self.remaining + len(self.w.enemies)
        return {"label": "WAVE %d/%d" % (max(1, self.wave), self.WAVES), "sub": "%d" % left,
                "progress": 1 - left / max(1, total) if self.wave else 0.0}


def make_rules(world):
    kind = world.spec.kind
    cls = {"fragments": StoryRules, "boss": BossRules, "endless": EndlessRules, "timeattack": TimeAttackRules, "horde": HordeRules}[kind]
    return cls(world)
