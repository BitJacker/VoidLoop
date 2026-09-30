"""Story scenes: dialogues, sector title cards, the final choice and the credits."""
import math
import random

import pygame

from .. import biomes, gfx
from ..i18n import i18n, T
from ..settings import W, H
from ..ui import Menu, Item
from .base import Scene, is_back, is_confirm, is_click, sequence

STYLE_COLORS = {
    "system": (0, 220, 255),
    "void": (190, 120, 255),
    "boss_sentinel": (0, 255, 150),
    "boss_weaver": (0, 165, 255),
    "boss_inferno": (255, 110, 50),
    "boss_cryo": (140, 230, 255),
    "boss_glitch": (255, 65, 240),
    "boss_origin": (200, 150, 255),
    "narrator": (190, 200, 220),
    "default": (230, 235, 245),
}
BLIP_BY_STYLE = {"system": "blip2", "void": "blip3", "echo": "blip1"}
GLITCH_CHARS = "#%&$@?<>/\\|01*+="


def style_color(app, style):
    if style == "echo":
        return app.settings.color            # ECHO speaks in your colour - it is you
    return STYLE_COLORS.get(style, STYLE_COLORS["default"])


def draw_portrait(surf, style, cx, cy, size, t, color):
    """A small animated emblem for every voice in the story."""
    s = size
    pygame.draw.rect(surf, (4, 8, 16), (cx - s, cy - s, s * 2, s * 2))
    if style == "system":
        for k in range(4):
            r = pygame.Rect(0, 0, s * (1.5 - k * 0.32), s * (1.5 - k * 0.32))
            r.center = (cx, cy)
            pygame.draw.rect(surf, gfx.scale_color(color, 0.35 + 0.15 * k), r, 2)
        y = cy - s + (t * 1.7) % (s * 2)
        pygame.draw.line(surf, color, (cx - s, y), (cx + s, y), 1)
        pygame.draw.circle(surf, gfx.WHITE, (cx, cy), max(3, int(s * 0.14)))
    elif style == "echo":
        gfx.draw_logo(surf, cx, cy, s * 0.85, t / 60.0, color, gfx.mix_white(color, 0.5))
    elif style == "void":
        pygame.draw.circle(surf, (0, 0, 2), (cx, cy), int(s * 0.7))
        for k in range(4):
            a = t * 0.04 * (1 if k % 2 else -1) + k
            rect = pygame.Rect(0, 0, s * (1.7 - k * 0.3), s * (1.7 - k * 0.3))
            rect.center = (cx, cy)
            pygame.draw.arc(surf, gfx.scale_color(color, 0.5 + 0.12 * k), rect, a, a + 3.3, 2)
    elif style == "boss_sentinel":
        gfx.neon_poly(surf, gfx.poly_points(cx, cy, s * 0.85, 8, t * 0.01), color, 2, halo=False)
        pygame.draw.circle(surf, gfx.WHITE, (cx, cy), int(s * 0.3))
        pygame.draw.circle(surf, color, (cx, cy), int(s * 0.13))
    elif style == "boss_weaver":
        tips = [(cx + math.cos(t * 0.02 + i * math.tau / 8) * s * 0.85, cy + math.sin(t * 0.02 + i * math.tau / 8) * s * 0.85) for i in range(8)]
        for i, tip in enumerate(tips):
            pygame.draw.line(surf, color, (cx, cy), tip, 1)
            pygame.draw.line(surf, gfx.scale_color(color, 0.5), tip, tips[(i + 2) % 8], 1)
        pygame.draw.circle(surf, gfx.WHITE, (cx, cy), int(s * 0.16))
    elif style == "boss_inferno":
        pygame.draw.rect(surf, gfx.scale_color(color, 0.3), (cx - s * 0.9, cy - s * 0.35, s * 1.8, s * 0.7))
        pygame.draw.rect(surf, color, (cx - s * 0.9, cy - s * 0.35, s * 1.8, s * 0.7), 2)
        for i in range(5):
            h = s * (0.25 + 0.15 * math.sin(t * 0.3 + i * 1.7))
            pygame.draw.polygon(surf, (255, 190, 70), [(cx - s * 0.8 + i * s * 0.4 - 8, cy - s * 0.35), (cx - s * 0.8 + i * s * 0.4, cy - s * 0.35 - h),
                                                      (cx - s * 0.8 + i * s * 0.4 + 8, cy - s * 0.35)])
        pygame.draw.circle(surf, gfx.WHITE, (cx, cy), int(s * 0.14))
    elif style == "boss_cryo":
        pts = [(cx + math.cos(t * 0.01 + i * math.tau / 12) * (s * 0.9 if i % 2 == 0 else s * 0.42),
                cy + math.sin(t * 0.01 + i * math.tau / 12) * (s * 0.9 if i % 2 == 0 else s * 0.42)) for i in range(12)]
        pygame.draw.polygon(surf, color, pts, 2)
        pygame.draw.circle(surf, gfx.WHITE, (cx, cy), int(s * 0.14))
    elif style == "boss_glitch":
        jit = int(t / 3) % 5
        for dx, col in ((-4 + jit, (255, 65, 240)), (4 - jit, (70, 255, 200))):
            for k in range(4):
                pygame.draw.rect(surf, col, (cx - s * 0.6 + dx, cy - s * 0.8 + k * s * 0.4, s * 1.2 - k * 8, s * 0.28), 2)
    elif style == "boss_origin":
        for i in range(20):
            a = t * 0.02 + i * math.tau / 20
            pygame.draw.line(surf, gfx.scale_color(color, 0.7), (cx + math.cos(a) * s * 0.6, cy + math.sin(a) * s * 0.6),
                             (cx + math.cos(a) * s * (0.85 + 0.1 * math.sin(t * 0.1 + i)), cy + math.sin(a) * s * (0.85 + 0.1 * math.sin(t * 0.1 + i))), 2)
        pygame.draw.circle(surf, (0, 0, 2), (cx, cy), int(s * 0.55))
        pygame.draw.circle(surf, color, (cx, cy), int(s * 0.55), 2)
    else:
        pygame.draw.circle(surf, gfx.scale_color(color, 0.6), (cx, cy), int(s * 0.5), 2)
    pygame.draw.rect(surf, color, (cx - s, cy - s, s * 2, s * 2), 2)
    for (x, y, dx, dy) in ((cx - s, cy - s, 1, 1), (cx + s, cy - s, -1, 1), (cx - s, cy + s, 1, -1), (cx + s, cy + s, -1, -1)):
        pygame.draw.lines(surf, gfx.WHITE, False, [(x + dx * 9, y), (x, y), (x, y + dy * 9)], 2)


class DialogueBox:
    """Typewriter text with speaker name and portrait."""
    SPEED = 1.15                       # characters per frame

    def __init__(self, app, lines, glitch=0.0):
        self.app = app
        self.lines = lines
        self.glitch = glitch
        self.i = 0
        self.chars = 0.0
        self.blip = 0
        self._wrapped = {}

    @property
    def line(self):
        return self.lines[self.i] if self.i < len(self.lines) else None

    def finished_typing(self):
        line = self.line
        return line is None or self.chars >= len(line.text)

    def update(self):
        line = self.line
        if line is None:
            return
        before = int(self.chars)
        self.chars = min(len(line.text), self.chars + self.SPEED)
        if int(self.chars) != before and int(self.chars) % 2 == 0 and line.text[max(0, int(self.chars) - 1)] != " ":
            self.app.audio.play(BLIP_BY_STYLE.get(line.style, "blip1"))

    def advance(self):
        """Complete the current line, or move to the next. Returns True when the whole scene is over."""
        if self.line is None:
            return True
        if not self.finished_typing():
            self.chars = len(self.line.text)
            return False
        self.i += 1
        self.chars = 0.0
        return self.i >= len(self.lines)

    def _wrap(self, text, width):
        key = (text, width)
        if key not in self._wrapped:
            self._wrapped[key] = gfx.wrap_text(text, "mono", 25, width)
        return self._wrapped[key]

    def _glitched(self, text, style, t):
        if self.glitch <= 0 or style == "narrator":
            return text
        p = self.glitch * (1.0 if style in ("system", "void") or style.startswith("boss") else 0.4)
        rng = random.Random(int(t / 5) * 131 + len(text))
        out = []
        for ch in text:
            out.append(rng.choice(GLITCH_CHARS) if ch != " " and rng.random() < p * 0.35 else ch)
        return "".join(out)

    def draw(self, surf, t, rect):
        line = self.line
        color = style_color(self.app, line.style) if line else gfx.WHITE
        gfx.panel(surf, rect, color, fill=(4, 8, 18, 232), border=2, cut=14)
        if line is None:
            return
        left = rect.x + 28
        if line.speaker:
            draw_portrait(surf, line.style, rect.x + 92, rect.centery - 6, 52, t, color)
            left = rect.x + 176
            gfx.draw_text(surf, line.speaker, (left, rect.y + 22), "display", 22, color)
            pygame.draw.line(surf, gfx.scale_color(color, 0.5), (left, rect.y + 54), (rect.right - 40, rect.y + 54), 1)
        else:
            gfx.draw_text(surf, "// ", (left, rect.y + 22), "display", 22, color)
        shown = int(self.chars)
        text = self._glitched(line.text, line.style, t)
        y = rect.y + 68
        pos = 0
        for ln in self._wrap(line.text, rect.right - left - 40):
            idx = line.text.find(ln, pos)
            if idx < 0:
                idx = pos
            pos = idx + len(ln)
            n = shown - idx
            if n <= 0:
                break
            gfx.draw_text(surf, text[idx:idx + min(len(ln), n)], (left, y), "mono", 25, gfx.WHITE)
            y += 32
        if self.finished_typing():
            k = 0.5 + 0.5 * math.sin(t * 0.2)
            gfx.draw_icon(surf, "tri_down", rect.right - 46, rect.bottom - 34 + k * 4, 9, gfx.scale_color(color, 0.6 + 0.4 * k))


class DialogueScene(Scene):
    def __init__(self, app, lines, done, sector=0, glitch=0.0):
        super().__init__(app)
        self.box = DialogueBox(app, lines, glitch)
        self.done = done
        self.sector = sector
        self.bg = biomes.make_background(sector)
        self._finished = False

    def enter(self):
        if self.app.audio.current is None:
            self.app.audio.play_music(biomes.BIOMES[self.sector].music)

    def finish(self):
        if not self._finished:
            self._finished = True
            self.done()

    def event(self, e):
        if is_back(e):
            self.finish()
        elif is_confirm(e) or is_click(e):
            if self.box.advance():
                self.finish()

    def update(self):
        super().update()
        self.bg.update()
        self.box.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 0), 120), (0, 0))
        pygame.draw.rect(surf, (0, 0, 0), (0, 0, W, 70))
        pygame.draw.rect(surf, (0, 0, 0), (0, H - 70, W, 70))
        self.box.draw(surf, self.t, pygame.Rect(90, H - 290, W - 180, 200))
        gfx.draw_text(surf, "%d / %d" % (min(self.box.i + 1, len(self.box.lines)), len(self.box.lines)), (W - 100, 92), "mono", 16, (120, 140, 160), "topright")
        gfx.draw_text(surf, T("dialog.skip"), (W - 100, H - 52), "mono", 16, (120, 140, 160), "bottomright")


class SectorCard(Scene):
    """"SECTOR 02 - DATA STREAM" title card."""

    def __init__(self, app, sector, done):
        super().__init__(app)
        self.sector = sector
        self.biome = biomes.BIOMES[sector]
        self.done = done
        self.bg = biomes.make_background(sector)
        self.music = self.biome.music
        self._finished = False

    def finish(self):
        if not self._finished:
            self._finished = True
            self.done()

    def event(self, e):
        if (is_confirm(e) or is_back(e) or is_click(e)) and self.t > 30:
            self.finish()

    def update(self):
        super().update()
        self.bg.update()
        if self.t > 230:
            self.finish()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 0), 110), (0, 0))
        b = self.biome
        k = min(1.0, self.t / 40)
        fade = min(1.0, max(0.0, (230 - self.t) / 25))
        w = int(520 * k)
        pygame.draw.line(surf, gfx.scale_color(b.main, fade), (W // 2 - w, 262), (W // 2 + w, 262), 2)
        pygame.draw.line(surf, gfx.scale_color(b.main, fade), (W // 2 - w, 470), (W // 2 + w, 470), 2)
        if self.t > 10:
            gfx.draw_text(surf, T("sector.label", n=self.sector + 1), (W // 2, 300), "display", 30, gfx.scale_color(b.accent, fade), "center")
        if self.t > 24:
            a = min(1.0, (self.t - 24) / 24) * fade
            gfx.glow_text(surf, T("sector.%s.name" % b.id).upper(), (W // 2, 372), "title", 58, gfx.scale_color(b.main, a), "center", 0.7)
        if self.t > 70:
            a = min(1.0, (self.t - 70) / 30) * fade
            gfx.draw_text(surf, T("sector.%s.sub" % b.id), (W // 2, 436), "mono", 22, gfx.scale_color(gfx.WHITE, a), "center")


class EndingScene(Scene):
    """After the last boss: break the loop, or keep it?"""
    music = "s6"

    def __init__(self, app, run):
        super().__init__(app)
        self.run = run
        self.bg = biomes.make_background(5)
        self.menu = Menu(app, [Item("break", lambda: T("ending.break"), color=gfx.GREEN),
                               Item("keep", lambda: T("ending.keep"), color=gfx.PURPLE)], W // 2, 430, 640, 60, 14, 20)
        self.chosen = None

    def event(self, e):
        if self.chosen:
            return
        key = self.menu.event(e)
        if key:
            self.chosen = key
            run = self.run
            app = self.app
            lines = i18n.scene("ending_" + key)
            factories = []
            if lines:
                factories.append(lambda done: DialogueScene(app, lines, done, sector=5, glitch=0.05))
            factories.append(lambda done: CreditsScene(app, run, key))
            sequence(app, factories)

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 0), 100), (0, 0))
        gfx.glow_text(surf, T("ending.title"), (W // 2, 150), "title", 46, (200, 150, 255), "center", 0.7)
        lines = gfx.wrap_text(T("ending.prompt"), "mono", 24, 860)
        y = 232
        for ln in lines:
            gfx.draw_text(surf, ln, (W // 2, y), "mono", 24, gfx.WHITE, "center")
            y += 34
        self.menu.draw(surf)


class CreditsScene(Scene):
    music = "menu"

    def __init__(self, app, run, choice):
        super().__init__(app)
        self.run = run
        self.choice = choice
        self.bg = biomes.TitleBG()
        stats = app.save.stats
        mins = int(stats["playtime"] // 60)
        self.lines = [("title", "VOID LOOP"), ("mono", T("credits.ending_" + choice)), ("gap", ""),
                      ("head", T("credits.stats")),
                      ("mono", T("credits.kills", n=int(stats["kills"]))),
                      ("mono", T("credits.deaths", n=int(stats["deaths"]))),
                      ("mono", T("credits.time", n=mins)), ("gap", "")]
        for entry in i18n.tl("credits.lines"):
            if entry.startswith("#"):
                self.lines.append(("head", entry[1:].strip()))
            elif entry == "":
                self.lines.append(("gap", ""))
            else:
                self.lines.append(("mono", entry))
        self.lines += [("gap", ""), ("gap", ""), ("title", T("credits.thanks")), ("gap", ""), ("mono", T("credits.loop_" + choice))]
        self.scroll = 0.0
        self._finished = False

    def finish(self):
        if not self._finished:
            self._finished = True
            self.run.finish_story(self.choice)
            self.run.quit_to_menu()

    def event(self, e):
        if (is_back(e) or is_confirm(e) or is_click(e)) and self.t > 60:
            if self.scroll > 200:
                self.finish()

    def update(self):
        super().update()
        self.bg.update()
        self.scroll += 1.1
        total = sum(80 if k == "title" else 48 if k == "head" else 22 if k == "gap" else 36 for k, _ in self.lines)
        if self.scroll > total + H:
            self.finish()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 0), 90), (0, 0))
        gfx.draw_logo(surf, W // 2, 110, 60, self.t / 60.0, gfx.GREEN, gfx.CYAN)
        y = H - self.scroll + 200
        for kind, text in self.lines:
            if kind == "title":
                if -80 < y < H:
                    gfx.glow_text(surf, text, (W // 2, y), "title", 44, gfx.GREEN, "center", 0.6)
                y += 80
            elif kind == "head":
                if -40 < y < H:
                    gfx.draw_text(surf, text, (W // 2, y), "display", 22, gfx.CYAN, "center")
                y += 48
            elif kind == "gap":
                y += 22
            else:
                if -40 < y < H:
                    gfx.draw_text(surf, text, (W // 2, y), "mono", 22, gfx.WHITE, "center")
                y += 36
        pygame.draw.rect(surf, (0, 0, 0), (0, 0, W, 60))
