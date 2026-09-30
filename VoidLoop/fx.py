"""Visual effects: sparks, debris, shock rings, floating texts, screen shake/flash."""
import math
import random

import pygame

from . import gfx

MAX_PARTICLES = 700


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "kind", "drag", "rot", "vrot")

    def __init__(self, x, y, vx, vy, life, color, size, kind, drag=0.96):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color = color
        self.size = size
        self.kind = kind
        self.drag = drag
        self.rot = random.random() * math.tau
        self.vrot = random.uniform(-0.3, 0.3)


class FX:
    def __init__(self):
        self.parts = []
        self.rings = []      # [x, y, r0, r1, life, max, color, width]
        self.texts = []      # [x, y, vy, life, max, text, color, size]
        self.shake = 0.0
        self.flash = 0.0
        self.flash_color = (255, 255, 255)

    def clear(self):
        self.parts.clear()
        self.rings.clear()
        self.texts.clear()
        self.shake = 0.0
        self.flash = 0.0

    # ---- emitters ----------------------------------------------------------
    def burst(self, x, y, color, n=12, speed=4.0, size=3, life=(18, 36), kind="spark", angle=0.0, spread=math.tau, drag=0.95):
        room = MAX_PARTICLES - len(self.parts)
        if room <= 0:
            return
        for _ in range(min(n, room)):
            a = angle + random.uniform(-spread / 2, spread / 2)
            v = speed * random.uniform(0.35, 1.0)
            self.parts.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v, random.randint(*life), color, size, kind, drag))

    def explosion(self, x, y, color, scale=1.0):
        n = int(14 * scale)
        self.burst(x, y, color, n=n, speed=5.5 * scale, size=3, kind="spark")
        self.burst(x, y, gfx.mix_white(color, 0.5), n=max(3, n // 3), speed=3.2 * scale, size=4, kind="dot", life=(14, 26))
        self.burst(x, y, color, n=max(3, n // 3), speed=4.5 * scale, size=5, kind="debris", life=(28, 50))
        self.ring(x, y, color, 6, 34 * scale + 10, 18, 3)

    def ring(self, x, y, color, r0=6, r1=60, life=20, width=3):
        if len(self.rings) < 60:
            self.rings.append([x, y, r0, r1, life, life, color, width])

    def text(self, x, y, text, color=gfx.WHITE, size=16):
        if len(self.texts) < 40:
            self.texts.append([x, y, -0.9, 46, 46, text, color, size])

    def add_shake(self, amount):
        self.shake = min(22.0, max(self.shake, amount))

    def add_flash(self, color, amount=0.6):
        self.flash_color = color
        self.flash = max(self.flash, amount)

    # ---- simulation ---------------------------------------------------------
    def update(self):
        parts = self.parts
        i = 0
        while i < len(parts):
            p = parts[i]
            p.x += p.vx
            p.y += p.vy
            p.vx *= p.drag
            p.vy *= p.drag
            p.rot += p.vrot
            p.life -= 1
            if p.life <= 0:
                parts[i] = parts[-1]
                parts.pop()
            else:
                i += 1
        for r in self.rings[:]:
            r[4] -= 1
            if r[4] <= 0:
                self.rings.remove(r)
        for t in self.texts[:]:
            t[1] += t[2]
            t[2] *= 0.96
            t[3] -= 1
            if t[3] <= 0:
                self.texts.remove(t)
        self.shake *= 0.86
        if self.shake < 0.3:
            self.shake = 0.0
        self.flash *= 0.88
        if self.flash < 0.02:
            self.flash = 0.0

    def shake_offset(self, enabled=True):
        if not enabled or self.shake <= 0:
            return 0, 0
        s = self.shake
        return int(random.uniform(-s, s)), int(random.uniform(-s, s))

    # ---- drawing -------------------------------------------------------------------
    def draw(self, surf):
        for x, y, r0, r1, life, mx, color, width in self.rings:
            k = 1.0 - life / mx
            radius = int(r0 + (r1 - r0) * (1 - (1 - k) ** 2))
            c = gfx.scale_color(color, 1.0 - k)
            pygame.draw.circle(surf, c, (int(x), int(y)), max(1, radius), max(1, int(width * (1 - k)) + 1))
        for p in self.parts:
            k = p.life / p.max
            c = gfx.scale_color(p.color, 0.25 + 0.75 * k)
            if p.kind == "spark":
                pygame.draw.line(surf, c, (p.x, p.y), (p.x - p.vx * 1.8, p.y - p.vy * 1.8), max(1, int(p.size * k)))
            elif p.kind == "dot":
                r = max(1, int(p.size * k + 0.5))
                pygame.draw.circle(surf, c, (int(p.x), int(p.y)), r)
                if p.size >= 4 and k > 0.4:
                    gfx.draw_glow(surf, (p.x, p.y), r * 4, p.color, 0.5 * k)
            else:  # debris
                r = max(1.5, p.size * (0.4 + 0.6 * k))
                pts = [(p.x + math.cos(p.rot + a) * r, p.y + math.sin(p.rot + a) * r) for a in (0.0, 2.3, 4.2)]
                pygame.draw.polygon(surf, c, pts)
        for x, y, vy, life, mx, text, color, size in self.texts:
            gfx.draw_text(surf, text, (x, y), "display", size, color, "center", shadow=True, alpha=min(255, int(life / mx * 400)))
