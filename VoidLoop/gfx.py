"""Drawing helpers: fonts, text, neon shapes, additive glow, panels and icons.

Everything in VoidLoop is drawn with vector primitives (no bitmap art), so the
look is defined here: dark backgrounds, bright neon outlines and additive glow.
"""
import math
import random

import pygame

from .paths import asset_path
from .settings import W, H

# --- palette -----------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (70, 76, 92)
DARK = (8, 12, 24)
CYAN = (0, 255, 255)
GOLD = (255, 215, 60)
RED = (255, 60, 80)
ORANGE = (255, 150, 30)
PINK = (255, 100, 200)
PURPLE = (180, 60, 255)
GREEN = (0, 255, 150)
BLUE = (0, 150, 255)
ICE = (150, 235, 255)
LIME = (170, 255, 60)
YELLOW = (255, 240, 60)
SILVER = (150, 165, 190)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t), int(c1[2] + (c2[2] - c1[2]) * t))


def scale_color(c, k):
    return (clamp(int(c[0] * k), 0, 255), clamp(int(c[1] * k), 0, 255), clamp(int(c[2] * k), 0, 255))


def mix_white(c, k):
    """Brighten a colour towards white by ``k`` (0..1)."""
    return lerp_color(c, WHITE, k)


def pulse(t, speed=1.0, lo=0.0, hi=1.0):
    """Smooth 0..1 oscillation; ``t`` is in frames."""
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t * speed * 0.1))


def from_angle(angle, length=1.0):
    return math.cos(angle) * length, math.sin(angle) * length


def poly_points(cx, cy, radius, sides, rotation=0.0):
    step = math.tau / sides
    return [(cx + math.cos(rotation + i * step) * radius, cy + math.sin(rotation + i * step) * radius)
            for i in range(sides)]


# --- fonts & text ---------------------------------------------------------------
_FONT_FILES = {
    "title": "Orbitron-Black.ttf",
    "display": "Orbitron-Bold.ttf",
    "mono": "ShareTechMono-Regular.ttf",
}
_font_cache = {}
_text_cache = {}


def font(kind, size):
    key = (kind, size)
    f = _font_cache.get(key)
    if f is None:
        try:
            f = pygame.font.Font(str(asset_path("fonts", _FONT_FILES[kind])), size)
        except Exception:                      # missing file: fall back to pygame's built-in font
            f = pygame.font.Font(None, int(size * 1.3))
        _font_cache[key] = f
    return f


def render(text, kind="mono", size=18, color=WHITE):
    key = (text, kind, size, color)
    img = _text_cache.get(key)
    if img is None:
        if len(_text_cache) > 900:
            _text_cache.clear()
        img = font(kind, size).render(text, True, color)
        _text_cache[key] = img
    return img


def text_width(text, kind="mono", size=18):
    return font(kind, size).size(text)[0]


def draw_text(surf, text, pos, kind="mono", size=18, color=WHITE, anchor="topleft", shadow=False, alpha=255):
    """Draw text; ``anchor`` is any pygame.Rect attribute (topleft, center, midtop ...)."""
    if not text:
        return pygame.Rect(pos[0], pos[1], 0, 0)
    img = render(text, kind, size, color)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    if shadow:
        surf.blit(render(text, kind, size, (0, 0, 0)), rect.move(2, 2))
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def wrap_text(text, kind, size, max_width):
    """Greedy word wrap -> list of lines."""
    f = font(kind, size)
    lines, current = [], ""
    for word in text.split(" "):
        trial = word if not current else current + " " + word
        if f.size(trial)[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def glow_text(surf, text, pos, kind="display", size=32, color=GREEN, anchor="center", strength=0.8):
    """Neon text with a soft halo (cached per string)."""
    key = ("glow", text, kind, size, color, strength)
    img = _text_cache.get(key)
    if img is None:
        core = font(kind, size).render(text, True, color)
        pad = size
        w, h = core.get_width() + pad * 2, core.get_height() + pad * 2
        halo = pygame.Surface((w, h)).convert()
        halo.fill((0, 0, 0))
        tinted = font(kind, size).render(text, True, scale_color(color, strength))
        halo.blit(tinted, (pad, pad))
        small = pygame.transform.smoothscale(halo, (max(1, w // 4), max(1, h // 4)))
        blur = pygame.transform.smoothscale(small, (w, h))
        blur2 = pygame.transform.smoothscale(pygame.transform.smoothscale(halo, (max(1, w // 8), max(1, h // 8))), (w, h))
        out = pygame.Surface((w, h)).convert()
        out.fill((0, 0, 0))
        out.blit(blur2, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        out.blit(blur, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        out.blit(blur, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        out.set_colorkey(None)
        # store as (halo, core, pad)
        img = (out, core, pad)
        if len(_text_cache) > 900:
            _text_cache.clear()
        _text_cache[key] = img
    halo, core, pad = img
    rect = halo.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surf.blit(halo, rect, special_flags=pygame.BLEND_RGB_ADD)
    surf.blit(core, (rect.x + pad, rect.y + pad))
    return pygame.Rect(rect.x + pad, rect.y + pad, core.get_width(), core.get_height())


# --- additive glow ---------------------------------------------------------------
_glow_base = None
_glow_cache = {}


def _base_gradient(size=96):
    global _glow_base
    if _glow_base is None:
        surf = pygame.Surface((size, size)).convert()
        c = size / 2.0
        for y in range(size):
            for x in range(size):
                d = math.hypot(x + 0.5 - c, y + 0.5 - c) / c
                v = max(0.0, 1.0 - d)
                v = v ** 2.2
                g = int(255 * v)
                surf.set_at((x, y), (g, g, g))
        _glow_base = surf
    return _glow_base


def glow_sprite(radius, color):
    radius = max(4, int(radius) // 2 * 2)
    key = (radius, color)
    spr = _glow_cache.get(key)
    if spr is None:
        if len(_glow_cache) > 400:
            _glow_cache.clear()
        spr = pygame.transform.smoothscale(_base_gradient(), (radius * 2, radius * 2))
        spr.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        _glow_cache[key] = spr
    return spr


def draw_glow(surf, pos, radius, color, k=1.0):
    """Additive radial glow centred on ``pos`` (k scales the brightness)."""
    if k <= 0.02 or radius < 3:
        return
    c = (min(255, int(color[0] * k)) // 12 * 12, min(255, int(color[1] * k)) // 12 * 12, min(255, int(color[2] * k)) // 12 * 12)
    if c[0] + c[1] + c[2] < 24:
        return
    spr = glow_sprite(radius, c)
    r = spr.get_width() // 2
    surf.blit(spr, (int(pos[0]) - r, int(pos[1]) - r), special_flags=pygame.BLEND_RGB_ADD)


# --- neon primitives ----------------------------------------------------------------
def neon_poly(surf, pts, color, width=2, fill=None, halo=True):
    if fill is not None:
        pygame.draw.polygon(surf, fill, pts)
    if halo:
        pygame.draw.polygon(surf, scale_color(color, 0.16), pts, width + 6)
        pygame.draw.polygon(surf, scale_color(color, 0.38), pts, width + 3)
    pygame.draw.polygon(surf, color, pts, width)


def neon_circle(surf, pos, radius, color, width=2, fill=None, halo=True):
    p = (int(pos[0]), int(pos[1]))
    radius = max(1, int(radius))
    if fill is not None:
        pygame.draw.circle(surf, fill, p, radius)
    if halo:
        pygame.draw.circle(surf, scale_color(color, 0.16), p, radius + 3, width + 4)
        pygame.draw.circle(surf, scale_color(color, 0.38), p, radius + 1, width + 2)
    pygame.draw.circle(surf, color, p, radius, width)


def neon_line(surf, a, b, color, width=2, halo=True):
    if halo:
        pygame.draw.line(surf, scale_color(color, 0.16), a, b, width + 6)
        pygame.draw.line(surf, scale_color(color, 0.4), a, b, width + 3)
    pygame.draw.line(surf, color, a, b, width)


def neon_rect(surf, rect, color, width=2, fill=None, halo=True):
    rect = pygame.Rect(rect)
    if fill is not None:
        pygame.draw.rect(surf, fill, rect)
    if halo:
        pygame.draw.rect(surf, scale_color(color, 0.16), rect.inflate(6, 6), width + 4)
        pygame.draw.rect(surf, scale_color(color, 0.38), rect.inflate(3, 3), width + 2)
    pygame.draw.rect(surf, color, rect, width)


def dashed_line(surf, a, b, color, width=2, dash=12, gap=8, offset=0.0):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    pos = -(offset % (dash + gap))
    while pos < length:
        s, e = max(pos, 0.0), min(pos + dash, length)
        if e > s:
            pygame.draw.line(surf, color, (a[0] + ux * s, a[1] + uy * s), (a[0] + ux * e, a[1] + uy * e), width)
        pos += dash + gap


def alpha_rect(surf, rect, rgba, border_radius=0):
    rect = pygame.Rect(rect)
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(tmp, rgba, tmp.get_rect(), border_radius=border_radius)
    surf.blit(tmp, rect)


def alpha_circle(surf, pos, radius, rgba, width=0):
    radius = max(1, int(radius))
    tmp = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(tmp, rgba, (radius + 2, radius + 2), radius, width)
    surf.blit(tmp, (int(pos[0]) - radius - 2, int(pos[1]) - radius - 2))


def gradient_surface(size, top, bottom):
    w, h = size
    surf = pygame.Surface(size).convert()
    for y in range(h):
        pygame.draw.line(surf, lerp_color(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
    return surf


# --- panels & bars -----------------------------------------------------------------------
_panel_cache = {}


def cut_corner_points(rect, cut):
    x, y, w, h = rect
    return [(x + cut, y), (x + w - cut, y), (x + w, y + cut), (x + w, y + h - cut),
            (x + w - cut, y + h), (x + cut, y + h), (x, y + h - cut), (x, y + cut)]


def panel(surf, rect, color, fill=(6, 10, 22, 205), border=2, cut=10, halo=True):
    """Cyber-style panel with cut corners and a neon border."""
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, fill, cut)
    bg = _panel_cache.get(key)
    if bg is None:
        if len(_panel_cache) > 200:
            _panel_cache.clear()
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(bg, fill, cut_corner_points((0, 0, rect.w, rect.h), cut))
        _panel_cache[key] = bg
    surf.blit(bg, rect.topleft)
    pts = cut_corner_points(rect, cut)
    if halo:
        pygame.draw.polygon(surf, scale_color(color, 0.22), pts, border + 4)
    pygame.draw.polygon(surf, color, pts, border)


def bar(surf, rect, frac, color, bg=(18, 22, 36), border=None, border_w=2):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, bg, rect)
    fill_w = int(rect.w * clamp(frac, 0.0, 1.0))
    if fill_w > 0:
        pygame.draw.rect(surf, color, (rect.x, rect.y, fill_w, rect.h))
        pygame.draw.rect(surf, mix_white(color, 0.45), (rect.x, rect.y, fill_w, max(1, rect.h // 4)))
    if border:
        pygame.draw.rect(surf, border, rect, border_w)


# --- icons -----------------------------------------------------------------------------------
def _heart_points():
    pts = []
    for i in range(36):
        t = i / 36 * math.tau
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 17.0, -y / 17.0))
    return pts


_HEART = _heart_points()


def draw_heart(surf, cx, cy, size, color, filled=True):
    pts = [(cx + x * size, cy + y * size + size * 0.08) for x, y in _HEART]
    if filled:
        pygame.draw.polygon(surf, scale_color(color, 0.35), pts, 0)
        pygame.draw.polygon(surf, color, pts, 0)
        pygame.draw.polygon(surf, mix_white(color, 0.55), [(cx - size * 0.55, cy - size * 0.4), (cx - size * 0.25, cy - size * 0.62),
                                                          (cx - size * 0.1, cy - size * 0.38)], 0)
    else:
        pygame.draw.polygon(surf, scale_color(color, 0.5), pts, 2)


def draw_icon(surf, name, cx, cy, size, color):
    """Small vector icons used by the HUD, shop and power-ups."""
    s = size
    if name == "shield":
        pts = [(cx, cy - s), (cx + s * 0.85, cy - s * 0.45), (cx + s * 0.7, cy + s * 0.35), (cx, cy + s), (cx - s * 0.7, cy + s * 0.35),
               (cx - s * 0.85, cy - s * 0.45)]
        pygame.draw.polygon(surf, color, pts, 2)
        pygame.draw.polygon(surf, scale_color(color, 0.4), [(cx, cy - s * 0.55), (cx + s * 0.45, cy - s * 0.25), (cx + s * 0.35, cy + s * 0.2),
                                                            (cx, cy + s * 0.55), (cx - s * 0.35, cy + s * 0.2), (cx - s * 0.45, cy - s * 0.25)])
    elif name == "speed":
        pts = [(cx + s * 0.2, cy - s), (cx - s * 0.6, cy + s * 0.1), (cx - s * 0.05, cy + s * 0.1), (cx - s * 0.25, cy + s),
               (cx + s * 0.6, cy - s * 0.15), (cx + s * 0.05, cy - s * 0.15)]
        pygame.draw.polygon(surf, color, pts)
    elif name == "double":
        for dx in (-0.45, 0.45):
            pygame.draw.polygon(surf, color, [(cx + dx * s, cy - s * 0.9), (cx + dx * s + s * 0.28, cy + s * 0.5), (cx + dx * s - s * 0.28, cy + s * 0.5)])
        pygame.draw.line(surf, color, (cx - s * 0.9, cy + s * 0.85), (cx + s * 0.9, cy + s * 0.85), 2)
    elif name == "rapid":
        for i in range(3):
            y = cy - s * 0.7 + i * s * 0.6
            pygame.draw.lines(surf, color, False, [(cx - s * 0.7, y + s * 0.3), (cx, y - s * 0.1), (cx + s * 0.7, y + s * 0.3)], 3)
    elif name == "heart":
        draw_heart(surf, cx, cy, s * 0.95, color)
    elif name == "bomb":
        pygame.draw.circle(surf, color, (int(cx), int(cy + s * 0.2)), int(s * 0.7))
        pygame.draw.line(surf, WHITE, (cx + s * 0.35, cy - s * 0.35), (cx + s * 0.7, cy - s * 0.8), 2)
        for a in range(0, 360, 90):
            dx, dy = from_angle(math.radians(a + 45), s * 0.32)
            pygame.draw.line(surf, GOLD, (cx + s * 0.7, cy - s * 0.8), (cx + s * 0.7 + dx, cy - s * 0.8 + dy), 2)
    elif name == "freeze":
        for a in range(0, 180, 60):
            dx, dy = from_angle(math.radians(a), s)
            pygame.draw.line(surf, color, (cx - dx, cy - dy), (cx + dx, cy + dy), 2)
        pygame.draw.circle(surf, color, (int(cx), int(cy)), max(2, int(s * 0.28)), 2)
    elif name == "magnet":
        rect = pygame.Rect(cx - s * 0.7, cy - s * 0.75, s * 1.4, s * 1.5)
        pygame.draw.arc(surf, color, rect, math.pi, math.tau, 5)
        pygame.draw.line(surf, color, (cx - s * 0.7, cy), (cx - s * 0.7, cy + s * 0.7), 5)
        pygame.draw.line(surf, color, (cx + s * 0.7, cy), (cx + s * 0.7, cy + s * 0.7), 5)
        pygame.draw.line(surf, WHITE, (cx - s * 0.7, cy + s * 0.55), (cx - s * 0.7, cy + s * 0.75), 5)
        pygame.draw.line(surf, WHITE, (cx + s * 0.7, cy + s * 0.55), (cx + s * 0.7, cy + s * 0.75), 5)
    elif name == "coin":
        pygame.draw.circle(surf, color, (int(cx), int(cy)), int(s * 0.85))
        pygame.draw.circle(surf, scale_color(color, 0.55), (int(cx), int(cy)), int(s * 0.55), 2)
    elif name == "fragment":
        pts = [(cx, cy - s), (cx + s * 0.7, cy), (cx, cy + s), (cx - s * 0.7, cy)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, mix_white(color, 0.6), pts, 2)
    elif name == "blaster":
        pygame.draw.rect(surf, color, (cx - s * 0.9, cy - s * 0.2, s * 1.8, s * 0.4))
    elif name == "twin":
        for dy in (-0.45, 0.45):
            pygame.draw.rect(surf, color, (cx - s * 0.9, cy + dy * s - s * 0.13, s * 1.8, s * 0.26))
    elif name == "spread":
        for a in (-28, 0, 28):
            dx, dy = from_angle(math.radians(a), s)
            pygame.draw.line(surf, color, (cx - s * 0.7, cy), (cx - s * 0.7 + dx * 1.5, cy + dy * 1.5), 3)
    elif name == "pierce":
        pygame.draw.line(surf, color, (cx - s, cy), (cx + s * 0.6, cy), 3)
        pygame.draw.polygon(surf, color, [(cx + s, cy), (cx + s * 0.4, cy - s * 0.35), (cx + s * 0.4, cy + s * 0.35)])
    elif name == "mace":
        pygame.draw.line(surf, GRAY, (cx - s * 0.8, cy + s * 0.8), (cx + s * 0.2, cy - s * 0.2), 4)
        pygame.draw.circle(surf, color, (int(cx + s * 0.35), int(cy - s * 0.35)), int(s * 0.5))
    elif name == "dash":
        for i in range(3):
            pygame.draw.line(surf, scale_color(color, 0.4 + 0.3 * i), (cx - s + i * s * 0.35, cy - s * 0.5 + i * s * 0.5),
                             (cx + s * 0.4 + i * s * 0.35, cy - s * 0.5 + i * s * 0.5), 3)
    elif name == "pulse":
        for r, k in ((1.0, 0.4), (0.62, 0.7), (0.25, 1.0)):
            pygame.draw.circle(surf, scale_color(color, k), (int(cx), int(cy)), max(1, int(s * r)), 2)
    elif name == "skull":
        pygame.draw.circle(surf, color, (int(cx), int(cy - s * 0.1)), int(s * 0.8))
        pygame.draw.rect(surf, color, (cx - s * 0.4, cy + s * 0.4, s * 0.8, s * 0.5))
        for dx in (-0.32, 0.32):
            pygame.draw.circle(surf, BLACK, (int(cx + dx * s), int(cy - s * 0.1)), max(2, int(s * 0.2)))
    elif name == "lock":
        pygame.draw.rect(surf, color, (cx - s * 0.6, cy - s * 0.1, s * 1.2, s * 0.9))
        pygame.draw.arc(surf, color, (cx - s * 0.4, cy - s * 0.9, s * 0.8, s * 1.1), 0, math.pi, 3)
    elif name == "check":
        pygame.draw.lines(surf, color, False, [(cx - s * 0.7, cy), (cx - s * 0.2, cy + s * 0.6), (cx + s * 0.8, cy - s * 0.6)], 4)
    elif name == "star":
        pts = []
        for i in range(10):
            r = s if i % 2 == 0 else s * 0.42
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pygame.draw.polygon(surf, color, pts)
    elif name == "play":
        pygame.draw.polygon(surf, color, [(cx - s * 0.6, cy - s * 0.8), (cx + s * 0.8, cy), (cx - s * 0.6, cy + s * 0.8)])
    elif name == "tri_down":
        pygame.draw.polygon(surf, color, [(cx - s * 0.8, cy - s * 0.5), (cx + s * 0.8, cy - s * 0.5), (cx, cy + s * 0.6)])
    elif name == "arrow_l":
        pygame.draw.polygon(surf, color, [(cx + s * 0.6, cy - s * 0.8), (cx - s * 0.7, cy), (cx + s * 0.6, cy + s * 0.8)])
    elif name == "arrow_r":
        pygame.draw.polygon(surf, color, [(cx - s * 0.6, cy - s * 0.8), (cx + s * 0.7, cy), (cx - s * 0.6, cy + s * 0.8)])
    elif name == "cross":
        pygame.draw.line(surf, color, (cx - s * 0.7, cy - s * 0.7), (cx + s * 0.7, cy + s * 0.7), 4)
        pygame.draw.line(surf, color, (cx + s * 0.7, cy - s * 0.7), (cx - s * 0.7, cy + s * 0.7), 4)
    else:
        pygame.draw.circle(surf, color, (int(cx), int(cy)), int(s * 0.6), 2)


# --- ship drawing ------------------------------------------------------------------------------
def ship_points(cx, cy, angle, size):
    """Arrow-head ship polygon pointing along ``angle``."""
    pts = []
    for da, r in ((0.0, 1.35), (2.45, 1.0), (math.pi, 0.45), (-2.45, 1.0)):
        a = angle + da
        pts.append((cx + math.cos(a) * size * r, cy + math.sin(a) * size * r))
    return pts


def draw_ship(surf, cx, cy, angle, size, color, thrust=0.0, t=0.0, flash=False):
    """Neon delta ship with engine flame. ``thrust`` 0..1 lengthens the flame."""
    if thrust > 0.02:
        flick = 0.75 + 0.25 * math.sin(t * 1.7) + random.random() * 0.15
        back = angle + math.pi
        tip = (cx + math.cos(back) * size * (0.7 + 1.5 * thrust * flick), cy + math.sin(back) * size * (0.7 + 1.5 * thrust * flick))
        l = (cx + math.cos(back + 0.5) * size * 0.5, cy + math.sin(back + 0.5) * size * 0.5)
        r = (cx + math.cos(back - 0.5) * size * 0.5, cy + math.sin(back - 0.5) * size * 0.5)
        pygame.draw.polygon(surf, ORANGE if not flash else WHITE, [l, tip, r])
        inner = (cx + math.cos(back) * size * (0.6 + 0.9 * thrust * flick), cy + math.sin(back) * size * (0.6 + 0.9 * thrust * flick))
        pygame.draw.polygon(surf, (255, 240, 180), [(cx + math.cos(back + 0.25) * size * 0.45, cy + math.sin(back + 0.25) * size * 0.45), inner,
                                                     (cx + math.cos(back - 0.25) * size * 0.45, cy + math.sin(back - 0.25) * size * 0.45)])
    pts = ship_points(cx, cy, angle, size)
    body = scale_color(color, 0.22) if not flash else (255, 255, 255)
    neon_poly(surf, pts, color if not flash else WHITE, 2, fill=body)
    # cockpit
    nx, ny = cx + math.cos(angle) * size * 0.35, cy + math.sin(angle) * size * 0.35
    pygame.draw.circle(surf, mix_white(color, 0.7), (int(nx), int(ny)), max(2, int(size * 0.2)))


# --- overlays ---------------------------------------------------------------------------------------
_overlay_cache = {}


def _vignette_small(strength):
    w, h = 96, 54
    small = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            dx, dy = (x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1
            d = math.sqrt(dx * dx * 0.85 + dy * dy)
            a = clamp((d - 0.55) / 0.85, 0.0, 1.0) ** 1.6
            small.set_at((x, y), (0, 0, 0, int(a * 255 * strength)))
    return small


def vignette(strength=0.75):
    key = ("vig", int(strength * 100))
    surf = _overlay_cache.get(key)
    if surf is None:
        surf = pygame.transform.smoothscale(_vignette_small(strength), (W, H))
        _overlay_cache[key] = surf
    return surf


def crt_overlay():
    """Scanlines + vignette in a single alpha overlay (one blit per frame)."""
    surf = _overlay_cache.get("crt")
    if surf is None:
        surf = vignette(0.7).copy()
        line = pygame.Surface((W, 1), pygame.SRCALPHA)
        line.fill((0, 0, 0, 46))
        for y in range(0, H, 3):
            surf.blit(line, (0, y))
        _overlay_cache["crt"] = surf
    return surf


def tint_overlay(color, alpha):
    key = ("tint", color)
    surf = _overlay_cache.get(key)
    if surf is None:
        surf = pygame.Surface((W, H)).convert()
        surf.fill(color)
        _overlay_cache[key] = surf
    surf.set_alpha(clamp(int(alpha), 0, 255))
    return surf


# --- logo -------------------------------------------------------------------------------------
def ring_segment(surf, color, cx, cy, r0, r1, a0, a1):
    steps = max(6, int(abs(a1 - a0) * r1 / 5))
    pts = [(cx + math.cos(a0 + (a1 - a0) * i / steps) * r1, cy + math.sin(a0 + (a1 - a0) * i / steps) * r1) for i in range(steps + 1)]
    pts += [(cx + math.cos(a1 - (a1 - a0) * i / steps) * r0, cy + math.sin(a1 - (a1 - a0) * i / steps) * r0) for i in range(steps + 1)]
    pygame.draw.polygon(surf, color, pts)


def draw_logo(surf, cx, cy, r, t=0.0, color=GREEN, accent=CYAN):
    """The VoidLoop emblem: two counter-rotating broken rings around a void."""
    thick = max(2.0, r * 0.15)
    for k, (col, radius, speed, gaps) in enumerate(((color, r, 0.012, 3), (accent, r * 0.68, -0.02, 2))):
        span = math.tau / gaps
        for i in range(gaps):
            a0 = t * speed * 60 + i * span
            ring_segment(surf, col, cx, cy, radius - thick, radius, a0, a0 + span * 0.72)
    pygame.draw.circle(surf, (0, 4, 8), (int(cx), int(cy)), max(2, int(r * 0.34)))
    pygame.draw.circle(surf, color, (int(cx), int(cy)), max(2, int(r * 0.34)), max(1, int(r * 0.05)))
    pygame.draw.circle(surf, WHITE, (int(cx), int(cy)), max(1, int(r * 0.09)))
