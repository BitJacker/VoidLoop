"""Stage results, game over and run summary screens."""
import math
import random

import pygame

from .. import biomes, gfx
from ..i18n import i18n, T
from ..settings import W, H
from ..ui import Menu, Item, draw_header, draw_hint
from .base import Scene, is_confirm, is_click, is_back
from .story import DialogueBox

RANK_COLORS = {"S": gfx.GOLD, "A": gfx.GREEN, "B": gfx.CYAN, "C": gfx.GRAY}


def rank_for(hits):
    return "S" if hits == 0 else "A" if hits <= 1 else "B" if hits <= 3 else "C"


def fmt_time(frames):
    s = int(frames // 60)
    return "%02d:%02d" % (s // 60, s % 60)


class ResultsScene(Scene):
    """Stage cleared."""
    music = None

    def __init__(self, app, run, world, done):
        super().__init__(app)
        self.run = run
        self.world = world
        self.done = done
        self.bg = biomes.make_background(world.sector)
        self.rank = rank_for(world.hits_taken)
        self.rows = [
            ("results.time", fmt_time(world.time)),
            ("results.kills", str(world.kills)),
            ("results.combo", "x%d" % world.best_combo),
            ("results.hits", str(world.hits_taken)),
            ("results.coins", "+%d" % world.coins_earned),
            ("results.score", "{:,}".format(world.score)),
        ]
        self._finished = False

    def enter(self):
        self.app.audio.play("clear")

    def finish(self):
        if not self._finished:
            self._finished = True
            self.done()

    def event(self, e):
        if (is_confirm(e) or is_click(e)) and self.t > 50:
            self.finish()

    def update(self):
        super().update()
        self.bg.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 0), 130), (0, 0))
        world = self.world
        col = world.biome.main
        draw_header(surf, T("results.title"), T("sector.%s.name" % world.biome.id), col)
        gfx.panel(surf, (W // 2 - 400, 170, 800, 410), col, fill=(4, 8, 18, 220), border=2, cut=16)
        y = 208
        for i, (key, value) in enumerate(self.rows):
            k = min(1.0, max(0.0, (self.t - 10 - i * 7) / 12))
            if k <= 0:
                continue
            gfx.draw_text(surf, T(key), (W // 2 - 340, y), "mono", 26, gfx.scale_color(gfx.WHITE, k))
            gfx.draw_text(surf, value, (W // 2 + 10, y), "display", 24, gfx.scale_color(gfx.GOLD if key == "results.score" else gfx.WHITE, k), "topright")
            pygame.draw.line(surf, gfx.scale_color(col, 0.25 * k), (W // 2 - 340, y + 36), (W // 2 + 10, y + 36), 1)
            y += 54
        if self.t > 60:
            k = min(1.0, (self.t - 60) / 14)
            size = int(150 - 40 * k + (1 - k) * 60)
            rc = RANK_COLORS[self.rank]
            gfx.glow_text(surf, self.rank, (W // 2 + 250, 340), "title", max(80, size), gfx.scale_color(rc, k), "center", 0.9)
            gfx.draw_text(surf, T("results.rank"), (W // 2 + 250, 250), "mono", 20, gfx.scale_color(gfx.WHITE, k), "center")
        if self.t > 50:
            a = 0.5 + 0.5 * math.sin(self.t * 0.12)
            draw_hint(surf, T("results.continue"), H - 60, gfx.scale_color(gfx.WHITE, 0.5 + 0.5 * a))


class GameOverScene(Scene):
    """Story mode death: a few last words, then retry."""
    music = None

    def __init__(self, app, run, world):
        super().__init__(app)
        self.run = run
        self.world = world
        self.bg = biomes.make_background(world.sector)
        lines = i18n.pick_scene("game_over")
        self.box = DialogueBox(app, lines, glitch=0.12)
        self.tip = None
        tips = i18n.tl("tips")
        if tips:
            self.tip = random.choice(tips)
        self.menu = Menu(app, [Item("retry", lambda: T("over.retry"), color=gfx.GREEN), Item("menu", lambda: T("over.menu"), color=gfx.RED)],
                         W // 2, 500, 460, 56, 12, 22)
        self.talking = True

    def enter(self):
        self.app.audio.stop_music(500)

    def event(self, e):
        if self.talking:
            if is_confirm(e) or is_click(e):
                if self.box.advance():
                    self.talking = False
            elif is_back(e):
                self.talking = False
            return
        key = self.menu.event(e)
        if key == "retry":
            self.run.retry()
        elif key == "menu":
            self.run.save_story()
            self.run.quit_to_menu()

    def update(self):
        super().update()
        self.bg.update()
        if self.talking:
            self.box.update()
        else:
            self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((30, 0, 6), 170), (0, 0))
        jitter = 3 if (self.t // 4) % 6 == 0 else 0
        gfx.glow_text(surf, T("over.title"), (W // 2 + jitter, 140), "title", 60, gfx.RED, "center", 0.7)
        gfx.draw_text(surf, T("over.stage", stage=self.world.spec.index + 1 if self.world.spec.mode == "STORY" else 1), (W // 2, 200), "mono", 20, (200, 140, 150), "center")
        self.box.draw(surf, self.t, pygame.Rect(140, 250, W - 280, 200))
        if not self.talking:
            self.menu.draw(surf)
        if self.tip:
            gfx.draw_text(surf, T("over.tip"), (W // 2, H - 96), "display", 14, (150, 170, 190), "center")
            for i, ln in enumerate(gfx.wrap_text(self.tip, "mono", 19, 900)):
                gfx.draw_text(surf, ln, (W // 2, H - 72 + i * 22), "mono", 19, (190, 205, 220), "center")


class SummaryScene(Scene):
    """End of a non-story run (Endless / Time Attack / Boss Rush / Horde)."""
    music = None

    def __init__(self, app, run, world):
        super().__init__(app)
        self.run = run
        self.world = world
        self.bg = biomes.make_background(world.sector)
        self.timeout = getattr(world.rules, "timed_out", False)
        best = app.save.best(run.mode, run.difficulty)
        self.best = best["score"] if best else 0
        self.menu = Menu(app, [Item("again", lambda: T("summary.again"), color=gfx.GREEN), Item("menu", lambda: T("over.menu"), color=gfx.RED)],
                         W // 2, 575, 460, 54, 12, 22)
        stage_key = {"ENDLESS": "summary.level", "TIME_ATTACK": "summary.level", "BOSS_RUSH": "summary.bosses", "HORDE": "summary.rounds"}[run.mode]
        if run.mode == "ENDLESS":
            reached = world.rules.level
        elif run.mode == "TIME_ATTACK":
            reached = run.ta_level
        elif run.mode == "BOSS_RUSH":
            reached = run.index
        else:
            reached = "%d.%d" % (run.index + 1, max(0, world.rules.wave))
        self.rows = [(stage_key, str(reached)), ("results.time", fmt_time(run.frames)), ("results.kills", str(run.kills)),
                     ("results.combo", "x%d" % run.best_combo), ("summary.score", "{:,}".format(run.score))]

    def enter(self):
        self.app.audio.stop_music(500)
        self.app.audio.play("gameover" if not self.run.record else "win")

    def event(self, e):
        key = self.menu.event(e)
        if key == "again":
            new = type(self.run)(self.app, self.run.mode, self.run.difficulty, self.run.players)
            new.begin()
        elif key == "menu":
            self.run.quit_to_menu()

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 10), 150), (0, 0))
        title = T("summary.timeup") if self.timeout else T("summary.title")
        draw_header(surf, title, T("mode.%s" % self.run.mode.lower()), gfx.RED if not self.run.record else gfx.GOLD)
        gfx.panel(surf, (W // 2 - 340, 170, 680, 330), gfx.CYAN, fill=(4, 8, 18, 220), border=2, cut=14)
        y = 196
        for i, (key, value) in enumerate(self.rows):
            k = min(1.0, max(0.0, (self.t - 6 - i * 6) / 10))
            gfx.draw_text(surf, T(key), (W // 2 - 300, y), "mono", 25, gfx.scale_color(gfx.WHITE, k))
            gfx.draw_text(surf, value, (W // 2 + 300, y), "display", 23, gfx.scale_color(gfx.GOLD if key == "summary.score" else gfx.WHITE, k), "topright")
            y += 48
        if self.run.record:
            a = 0.6 + 0.4 * math.sin(self.t * 0.2)
            gfx.glow_text(surf, T("summary.record"), (W // 2, 520), "display", 28, gfx.scale_color(gfx.GOLD, a), "center", 0.8)
        elif self.best:
            gfx.draw_text(surf, T("summary.best", n="{:,}".format(self.best)), (W // 2, 520), "mono", 20, (170, 190, 210), "center")
        self.menu.draw(surf)
