"""Sector hazards: data currents, laser gates, telegraphed blasts, portals, glitch stripes, gravity wells."""
import math

import pygame
from pygame import Vector2

from . import gfx
from .settings import W, H

PLAYER_START = (W // 2, int(H * 0.68))


def dist_point_segment(p, a, b):
    ab = b - a
    denom = ab.length_squared()
    if denom == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return p.distance_to(a + ab * t)


class Hazard:
    done = False

    def update(self, world):
        pass

    def draw_floor(self, surf, t):
        pass

    def draw(self, surf, t):
        pass

    def force_at(self, pos, r):
        return None

    def pull_bullet(self, b):
        pass


class CurrentLane(Hazard):
    """A band of fast data that drags everything inside along its direction."""

    def __init__(self, rect, direction, strength=1.6, color=(0, 165, 255)):
        self.rect = pygame.Rect(rect)
        self.dir = Vector2(direction).normalize()
        self.strength = strength
        self.color = color
        self._band = None

    def force_at(self, pos, r):
        if self.rect.collidepoint(pos.x, pos.y):
            return self.dir * self.strength
        return None

    def draw_floor(self, surf, t):
        if self._band is None:
            band = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            band.fill((*self.color, 26))
            pygame.draw.rect(band, (*self.color, 90), band.get_rect(), 2)
            self._band = band
        surf.blit(self._band, self.rect.topleft)
        d, p = self.dir, Vector2(-self.dir.y, self.dir.x)
        cx, cy = self.rect.center
        length = abs(d.x) * self.rect.w + abs(d.y) * self.rect.h
        across = abs(p.x) * self.rect.w + abs(p.y) * self.rect.h
        col = gfx.scale_color(self.color, 0.55)
        surf.set_clip(self.rect)
        spacing = 64
        shift = (t * 3.2) % spacing
        s = -length / 2 - spacing
        while s < length / 2 + spacing:
            o = -across / 2 + 20
            while o < across / 2:
                c = Vector2(cx, cy) + d * (s + shift) + p * o
                tip, l, r = c + d * 9, c - d * 7 + p * 11, c - d * 7 - p * 11
                pygame.draw.lines(surf, col, False, [l, tip, r], 3)
                o += 44
            s += spacing
        surf.set_clip(None)


class LaserGate(Hazard):
    """A beam between two emitters that cycles off -> warning -> on."""

    def __init__(self, a, b, offset=0, off=150, warn=48, on=80, color=(255, 95, 40)):
        self.a, self.b = Vector2(a), Vector2(b)
        self.offset = offset
        self.off, self.warn, self.on = off, warn, on
        self.cycle = off + warn + on
        self.color = color

    def state(self, t):
        k = (t + self.offset) % self.cycle
        if k < self.off:
            return "off"
        if k < self.off + self.warn:
            return "warn"
        return "on"

    def update(self, world):
        if self.state(world.time) != "on":
            return
        for p in world.alive_players():
            if p.vulnerable() and dist_point_segment(p.pos, self.a, self.b) < 6 + p.r:
                world.hurt_player(p, 1, p.pos, "laser")

    def draw(self, surf, t):
        state = self.state(t)
        a, b = (int(self.a.x), int(self.a.y)), (int(self.b.x), int(self.b.y))
        col = self.color
        if state == "off":
            pygame.draw.line(surf, gfx.scale_color(col, 0.22), a, b, 1)
        elif state == "warn":
            blink = int(t / 4) % 2 == 0
            gfx.dashed_line(surf, a, b, gfx.scale_color(col, 0.9 if blink else 0.45), 2, 12, 10, t * 2)
        else:
            gfx.neon_line(surf, a, b, gfx.mix_white(col, 0.4), 5)
            pygame.draw.line(surf, gfx.WHITE, a, b, 2)
            mid = (self.a + self.b) / 2
            gfx.draw_glow(surf, mid, int(self.a.distance_to(self.b) / 2) + 20, col, 0.25)
        for e in (a, b):
            pygame.draw.rect(surf, (30, 12, 10), (e[0] - 8, e[1] - 8, 16, 16))
            pygame.draw.rect(surf, col if state != "off" else gfx.scale_color(col, 0.5), (e[0] - 8, e[1] - 8, 16, 16), 2)


class Blast(Hazard):
    """A telegraphed circular strike: warning circle, then damage (and optional shards)."""

    def __init__(self, x, y, r, delay, color, dmg=1, shards=0, shard_speed=4.0, label="strike"):
        self.pos = Vector2(x, y)
        self.r = r
        self.delay = self.total = delay
        self.color = color
        self.dmg = dmg
        self.shards = shards
        self.shard_speed = shard_speed
        self.boom = 0
        self.label = label

    def update(self, world):
        if self.boom > 0:
            self.boom -= 1
            self.done = self.boom == 0
            return
        self.delay -= 1
        if self.delay <= 0:
            self.boom = 14
            world.fx.explosion(self.pos.x, self.pos.y, self.color, 1.6)
            world.fx.add_shake(6)
            world.emit("sfx", "blast")
            for p in world.alive_players():
                if p.vulnerable() and p.pos.distance_to(self.pos) < self.r + p.r:
                    world.hurt_player(p, self.dmg, self.pos, self.label)
            if self.shards:
                base = world.rng.random() * math.tau
                for i in range(self.shards):
                    a = base + i * math.tau / self.shards
                    world.enemy_bullet(self.pos.x, self.pos.y, a, self.shard_speed, r=4, color=self.color, kind="shard")

    def draw_floor(self, surf, t):
        x, y = int(self.pos.x), int(self.pos.y)
        if self.boom > 0:
            k = 1 - self.boom / 14
            pygame.draw.circle(surf, gfx.mix_white(self.color, 0.6 * (1 - k)), (x, y), int(self.r * (0.6 + 0.6 * k)), max(1, int(6 * (1 - k))))
            gfx.draw_glow(surf, (x, y), int(self.r * 1.6), self.color, 0.8 * (1 - k))
            return
        k = 1 - self.delay / self.total
        blink = self.delay < 24 and int(t / 3) % 2 == 0
        col = gfx.WHITE if blink else self.color
        pygame.draw.circle(surf, gfx.scale_color(col, 0.5 + 0.5 * k), (x, y), int(self.r), 2)
        pygame.draw.circle(surf, gfx.scale_color(col, 0.35 + 0.4 * k), (x, y), max(2, int(self.r * k)), 1)
        gfx.draw_glow(surf, (x, y), int(self.r * 1.2), self.color, 0.12 + 0.35 * k)
        for a in range(4):
            ang = math.pi / 4 + a * math.pi / 2
            pygame.draw.line(surf, gfx.scale_color(col, 0.6), (x + math.cos(ang) * self.r * 0.75, y + math.sin(ang) * self.r * 0.75),
                             (x + math.cos(ang) * self.r * 1.05, y + math.sin(ang) * self.r * 1.05), 2)


class BlastRain(Hazard):
    """Keeps dropping telegraphed blasts near the players."""

    def __init__(self, interval, count, r, delay, color, shards=0, shard_speed=4.0, spread=190, label="strike"):
        self.interval, self.count, self.r, self.delay = interval, count, r, delay
        self.color, self.shards, self.shard_speed, self.spread, self.label = color, shards, shard_speed, spread, label
        self.timer = int(interval * 0.6)

    def update(self, world):
        self.timer -= 1
        if self.timer > 0:
            return
        self.timer = int(self.interval * world.rng.uniform(0.8, 1.2))
        targets = world.alive_players()
        if not targets:
            return
        for _ in range(self.count):
            t = world.rng.choice(targets)
            ang, dist = world.rng.random() * math.tau, world.rng.uniform(0, self.spread)
            x = min(max(t.pos.x + math.cos(ang) * dist, 60), W - 60)
            y = min(max(t.pos.y + math.sin(ang) * dist, 90), H - 60)
            world.add_hazard(Blast(x, y, self.r, self.delay, self.color, 1, self.shards, self.shard_speed, self.label))


class PortalPair(Hazard):
    """Two linked gates. Players entering one come out of the other."""
    R = 28

    def __init__(self, a, b, color_a=(255, 65, 240), color_b=(70, 255, 200)):
        self.a, self.b = Vector2(a), Vector2(b)
        self.colors = (color_a, color_b)
        self.cool = {}

    def update(self, world):
        for p in world.alive_players():
            cd = self.cool.get(p.id, 0)
            if cd > 0:
                self.cool[p.id] = cd - 1
                continue
            for src, dst in ((self.a, self.b), (self.b, self.a)):
                if p.pos.distance_to(src) < self.R - 6:
                    d = p.vel.normalize() if p.vel.length() > 0.5 else Vector2(0, 1)
                    world.fx.burst(p.pos.x, p.pos.y, self.colors[0], 12, 4)
                    p.pos = Vector2(dst) + d * (self.R + 10)
                    p.pos.x = min(max(p.pos.x, p.r), W - p.r)
                    p.pos.y = min(max(p.pos.y, p.r), H - p.r)
                    self.cool[p.id] = 50
                    world.fx.burst(p.pos.x, p.pos.y, self.colors[1], 12, 4)
                    world.emit("sfx", "portal")
                    break

    def draw_floor(self, surf, t):
        for pos, col in zip((self.a, self.b), self.colors):
            x, y = int(pos.x), int(pos.y)
            gfx.draw_glow(surf, (x, y), 60, col, 0.45)
            pygame.draw.circle(surf, (2, 0, 6), (x, y), self.R - 4)
            for i in range(3):
                a = t * (0.09 + i * 0.03) * (1 if i % 2 else -1)
                r = self.R - i * 6
                rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
                pygame.draw.arc(surf, gfx.scale_color(col, 1.0 - i * 0.22), rect, a, a + 3.6, 3)


class Stripe(Hazard):
    """A full-height (or full-width) glitch bar: warning, then damage."""

    def __init__(self, pos, width, vertical=True, delay=60, active=22, color=(255, 65, 240)):
        self.vertical = vertical
        self.delay, self.active = delay, active
        self.age = 0
        self.color = color
        self.rect = pygame.Rect(int(pos - width / 2), 0, int(width), H) if vertical else pygame.Rect(0, int(pos - width / 2), W, int(width))
        self._warn = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._warn.fill((*color, 46))
        self._hot = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._hot.fill((*color, 200))

    def update(self, world):
        self.age += 1
        if self.delay <= self.age < self.delay + self.active:
            for p in world.alive_players():
                if p.vulnerable() and self.rect.inflate(p.r * 2, p.r * 2).collidepoint(p.pos.x, p.pos.y):
                    world.hurt_player(p, 1, p.pos, "glitch")
        if self.age >= self.delay + self.active:
            self.done = True

    def draw(self, surf, t):
        if self.age < self.delay:
            if int(t / 3) % 2 == 0 or self.age < self.delay - 20:
                surf.blit(self._warn, self.rect.topleft)
            pygame.draw.rect(surf, gfx.scale_color(self.color, 0.9), self.rect, 2)
        else:
            surf.blit(self._hot, self.rect.topleft)
            for i in range(10):
                if self.vertical:
                    y = (i * 97 + t * 31) % H
                    pygame.draw.rect(surf, gfx.WHITE, (self.rect.x, y, self.rect.w, 3))
                else:
                    x = (i * 131 + t * 37) % W
                    pygame.draw.rect(surf, gfx.WHITE, (x, self.rect.y, 3, self.rect.h))


class StripeRain(Hazard):
    def __init__(self, interval, width=70, delay=60, color=(255, 65, 240)):
        self.interval, self.width, self.delay, self.color = interval, width, delay, color
        self.timer = int(interval * 0.7)

    def update(self, world):
        self.timer -= 1
        if self.timer > 0:
            return
        self.timer = int(self.interval * world.rng.uniform(0.8, 1.25))
        targets = world.alive_players()
        if not targets:
            return
        t = world.rng.choice(targets)
        vertical = world.rng.random() < 0.65
        pos = t.pos.x if vertical else t.pos.y
        pos += world.rng.uniform(-60, 60)
        world.add_hazard(Stripe(pos, self.width, vertical, self.delay, 22, self.color))


class GravityWell(Hazard):
    """A slowly drifting singularity that drags players and bullets towards it."""
    CORE = 18

    def __init__(self, center, radius=300, strength=2.6, phase=0.0, color=(190, 140, 255), drift=(110, 70)):
        self.c0 = Vector2(center)
        self.radius, self.strength, self.phase, self.color = radius, strength, phase, color
        self.drift = drift
        self.t = 0
        self.pos = self._path(0)

    def _path(self, t):
        return self.c0 + Vector2(math.cos(t * 0.006 + self.phase) * self.drift[0], math.sin(t * 0.009 + self.phase) * self.drift[1])

    def update(self, world):
        self.t += 1
        self.pos = self._path(self.t)
        for p in world.alive_players():
            if p.vulnerable() and p.pos.distance_to(self.pos) < self.CORE + p.r:
                push = (p.pos - self.pos)
                push = push.normalize() * 14 if push.length() > 0 else Vector2(0, -14)
                p.vel = Vector2(push)
                world.hurt_player(p, 1, self.pos, "void")

    def force_at(self, pos, r):
        d = self.pos - pos
        dist = d.length()
        if dist >= self.radius or dist < 1:
            return None
        return d / dist * (self.strength * (1 - dist / self.radius) ** 1.4)

    def pull_bullet(self, b):
        dx, dy = self.pos.x - b.x, self.pos.y - b.y
        dist = math.hypot(dx, dy)
        if 1 < dist < self.radius:
            k = 0.16 * (1 - dist / self.radius)
            b.vx += dx / dist * k
            b.vy += dy / dist * k

    def draw_floor(self, surf, t):
        x, y = int(self.pos.x), int(self.pos.y)
        gfx.draw_glow(surf, (x, y), int(self.radius * 0.9), self.color, 0.20)
        for i in range(4):
            r = 120 - i * 26
            a = -t * (0.05 + i * 0.02)
            for k in range(5):
                a0 = a + k * math.tau / 5
                rect = pygame.Rect(x - r, y - r, r * 2, r * 2)
                pygame.draw.arc(surf, gfx.scale_color(self.color, 0.25 + 0.14 * i), rect, a0, a0 + 0.8, 2)
        pygame.draw.circle(surf, (0, 0, 0), (x, y), self.CORE)
        pygame.draw.circle(surf, gfx.scale_color(self.color, 0.9), (x, y), self.CORE + 2, 2)


# ---------------------------------------------------------------------------------------
def make_hazards(biome, rng, intensity=0.5, level=1):
    """The hazards of a sector. ``intensity`` is 0..1+ (grows through the sector)."""
    out = []
    kind = biome.hazard
    sx, sy = PLAYER_START
    if kind == "current":
        count = 2 if intensity < 0.9 else 3
        ys = rng.sample([120, 210, 330, 420, 560, 640], count)
        for i, y in enumerate(sorted(ys)):
            if abs(y - sy) < 70:
                y = 150 + 60 * i
            out.append(CurrentLane((0, y - 45, W, 90), (1 if i % 2 == 0 else -1, 0), 1.3 + 0.35 * intensity, biome.main))
    elif kind == "laser":
        count = 2 if intensity < 0.9 else 3
        for i in range(count):
            offset = i * 70
            if rng.random() < 0.5:
                y = rng.randint(140, 620)
                if abs(y - sy) < 60:
                    y = 160
                x0 = rng.choice((90, 380, 640, 820))
                out.append(LaserGate((x0, y), (x0 + rng.randint(300, 420), y), offset, color=biome.main))
            else:
                x = rng.randint(140, W - 140)
                if abs(x - sx) < 80:
                    x = 200
                y0 = rng.choice((60, 230))
                out.append(LaserGate((x, y0), (x, y0 + rng.randint(300, 420)), offset, color=biome.main))
    elif kind == "ice":
        out.append(BlastRain(max(70, int(170 - 40 * intensity - level)), 1 if intensity < 0.9 else 2, 54, 70, biome.main, shards=6,
                             shard_speed=3.8, label="ice"))
    elif kind == "portal":
        out.append(PortalPair((110, int(H * 0.45)), (W - 110, int(H * 0.45))))
        out.append(StripeRain(max(150, int(300 - 60 * intensity)), 70, 60, biome.main))
    elif kind == "gravity":
        out.append(GravityWell((W * 0.28, H * 0.34), 300, 2.4, 0.0, biome.main))
        if intensity >= 0.75:
            out.append(GravityWell((W * 0.74, H * 0.4), 300, 2.4, 2.1, biome.main))
        out.append(BlastRain(max(120, int(240 - 50 * intensity)), 1, 60, 80, biome.accent, shards=0, label="void"))
    return out
