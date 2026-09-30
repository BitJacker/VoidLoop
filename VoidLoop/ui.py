"""Menu widgets shared by every screen (mouse + keyboard driven)."""
import math

import pygame

from . import gfx
from .settings import W, H


class Item:
    """One row of a Menu.

    kind: "action"  - returns its key when activated
          "choice"  - cycles through ``values`` [(value, label), ...]
          "slider"  - 0..1 value
          "toggle"  - on/off
    ``label`` may be a string or a zero-argument callable (re-evaluated every frame).
    """

    def __init__(self, key, label, kind="action", values=None, get=None, set=None, step=0.1, enabled=True, color=None,
                 hint=None, icon=None, on_change=None):
        self.key = key
        self.label = label
        self.kind = kind
        self.values = values or []
        self.get = get
        self.set = set
        self.step = step
        self.enabled = enabled
        self.color = color
        self.hint = hint
        self.icon = icon
        self.on_change = on_change
        self.rect = pygame.Rect(0, 0, 0, 0)

    def text(self):
        return self.label() if callable(self.label) else self.label

    def is_enabled(self):
        return self.enabled() if callable(self.enabled) else self.enabled


class Menu:
    def __init__(self, app, items, cx, y, width=520, item_h=50, gap=10, size=20, color=gfx.GREEN, align="center"):
        self.app = app
        self.items = items
        self.cx, self.y, self.width, self.item_h, self.gap = cx, y, width, item_h, gap
        self.size = size
        self.color = color
        self.sel = 0
        self.t = 0
        self.align = align
        self.layout()
        self._skip_disabled(1)

    def layout(self):
        y = self.y
        for it in self.items:
            it.rect = pygame.Rect(self.cx - self.width // 2, y, self.width, self.item_h)
            y += self.item_h + self.gap

    def _skip_disabled(self, step):
        for _ in range(len(self.items)):
            if self.items[self.sel].is_enabled():
                return
            self.sel = (self.sel + step) % len(self.items)

    def _move(self, step):
        self.sel = (self.sel + step) % len(self.items)
        self._skip_disabled(step)
        self.app.audio.play("ui_move")

    # ---- values ---------------------------------------------------------------------
    def _adjust(self, it, direction):
        if not it.is_enabled():
            return
        if it.kind == "choice" and it.values:
            cur = it.get()
            idx = next((i for i, (v, _) in enumerate(it.values) if v == cur), 0)
            new = it.values[(idx + direction) % len(it.values)][0]
            it.set(new)
        elif it.kind == "slider":
            it.set(max(0.0, min(1.0, round((it.get() + direction * it.step) * 100) / 100)))
        elif it.kind == "toggle":
            it.set(not it.get())
        else:
            return
        self.app.audio.play("ui_move")
        if it.on_change:
            it.on_change(it)

    # ---- events -------------------------------------------------------------------------
    def event(self, e):
        """Returns the key of an activated action item, else None."""
        if e.type == pygame.MOUSEMOTION:
            cur = self.items[self.sel]
            if e.buttons[0] and cur.kind == "slider" and cur.is_enabled():      # dragging a slider
                bar = self._bar_rect(cur)
                if bar.inflate(40, 40).collidepoint(e.pos):
                    cur.set(max(0.0, min(1.0, (e.pos[0] - bar.x) / bar.w)))
                    if cur.on_change:
                        cur.on_change(cur)
                return None
            for i, it in enumerate(self.items):
                if it.rect.collidepoint(e.pos) and it.is_enabled():
                    if i != self.sel:
                        self.sel = i
                        self.app.audio.play("ui_move")
                    break
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, it in enumerate(self.items):
                if it.rect.collidepoint(e.pos) and it.is_enabled():
                    self.sel = i
                    if it.kind == "slider":
                        bar = self._bar_rect(it)
                        if bar.inflate(20, 30).collidepoint(e.pos):
                            it.set(max(0.0, min(1.0, (e.pos[0] - bar.x) / bar.w)))
                            self.app.audio.play("ui_move")
                            if it.on_change:
                                it.on_change(it)
                            return None
                    return self._activate(it)
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self._move(-1)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self._move(1)
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust(self.items[self.sel], -1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust(self.items[self.sel], 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._activate(self.items[self.sel])
        return None

    def _activate(self, it):
        if not it.is_enabled():
            self.app.audio.play("ui_error")
            return None
        if it.kind == "action":
            self.app.audio.play("ui_select")
            return it.key
        self._adjust(it, 1)
        return None

    def update(self):
        self.t += 1

    # ---- drawing --------------------------------------------------------------------------
    def _bar_rect(self, it):
        return pygame.Rect(it.rect.right - 230, it.rect.centery - 6, 200, 12)

    def draw(self, surf):
        for i, it in enumerate(self.items):
            self.draw_item(surf, it, i == self.sel)

    def draw_item(self, surf, it, selected):
        enabled = it.is_enabled()
        base = it.color or self.color
        col = base if enabled else gfx.GRAY
        r = it.rect
        if selected and enabled:
            k = 0.75 + 0.25 * math.sin(self.t * 0.18)
            gfx.panel(surf, r.inflate(8, 4), gfx.scale_color(col, k), fill=(*gfx.scale_color(col, 0.16), 225), border=2, cut=10)
            gfx.draw_glow(surf, r.center, int(r.w * 0.55), col, 0.10)
        else:
            gfx.panel(surf, r, gfx.scale_color(col, 0.42), fill=(6, 10, 20, 190), border=1, cut=10, halo=False)
        label = it.text()
        tcol = gfx.WHITE if (selected and enabled) else gfx.scale_color(col, 0.85)
        x0 = r.x + 22
        if it.icon:
            gfx.draw_icon(surf, it.icon, r.x + 30, r.centery, 10, tcol)
            x0 = r.x + 56
        if it.kind == "action":
            if self.align == "center" and not it.icon:
                gfx.draw_text(surf, label, r.center, "display", self.size, tcol, "center")
            else:
                gfx.draw_text(surf, label, (x0, r.centery), "display", self.size, tcol, "midleft")
            return
        gfx.draw_text(surf, label, (x0, r.centery), "display", self.size - 3, tcol, "midleft")
        value = it.get()
        if it.kind == "choice":
            text = next((lbl for v, lbl in it.values if v == value), str(value))
            if callable(text):
                text = text()
            rx = r.right - 26
            gfx.draw_text(surf, text, (rx - 26, r.centery), "mono", 22, tcol, "midright")
            if selected and enabled:
                gfx.draw_icon(surf, "arrow_l", rx - 26 - gfx.text_width(text, "mono", 22) - 18, r.centery, 7, col)
                gfx.draw_icon(surf, "arrow_r", rx - 4, r.centery, 7, col)
        elif it.kind == "slider":
            bar = self._bar_rect(it)
            gfx.bar(surf, bar, value, col, border=gfx.scale_color(col, 0.6), border_w=1)
            gfx.draw_text(surf, "%d%%" % int(round(value * 100)), (bar.x - 12, r.centery), "mono", 20, tcol, "midright")
            pygame.draw.circle(surf, gfx.WHITE, (bar.x + int(bar.w * value), bar.centery), 8)
        elif it.kind == "toggle":
            pill = pygame.Rect(r.right - 90, r.centery - 12, 64, 24)
            on = bool(value)
            pygame.draw.rect(surf, gfx.scale_color(col, 0.35 if on else 0.12), pill, border_radius=12)
            pygame.draw.rect(surf, col if on else gfx.GRAY, pill, 2, border_radius=12)
            knob_x = pill.right - 13 if on else pill.x + 13
            pygame.draw.circle(surf, gfx.WHITE if on else (130, 130, 140), (knob_x, pill.centery), 8)


def draw_header(surf, title, subtitle=None, color=gfx.GREEN, y=58):
    gfx.glow_text(surf, title, (W // 2, y), "title", 44, color, "center", 0.65)
    if subtitle:
        gfx.draw_text(surf, subtitle, (W // 2, y + 44), "mono", 20, gfx.scale_color(color, 0.8), "center")
    pygame.draw.line(surf, gfx.scale_color(color, 0.5), (W // 2 - 260, y + (72 if subtitle else 44)), (W // 2 + 260, y + (72 if subtitle else 44)), 1)


def draw_hint(surf, text, y=H - 34, color=(130, 150, 170)):
    gfx.draw_text(surf, text, (W // 2, y), "mono", 17, color, "center")
