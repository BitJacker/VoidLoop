"""The six sector bosses.

Each boss scripts its attacks as Python generators: every ``yield n`` means
"wait n frames", which keeps bullet patterns easy to read and tweak.
"""
import math

import pygame
from pygame import Vector2

from . import gfx
from .enemies import Enemy
from .hazards import Blast, Stripe
from .settings import W, H


class Beam:
    """A telegraphed sweeping laser that starts at the boss."""

    def __init__(self, angle, delta, warn=46, active=90, color=(255, 95, 40)):
        self.angle, self.delta, self.warn, self.active, self.color = angle, delta, warn, active, color
        self.age = 0
        self.done = False

    def update(self, boss, world):
        self.age += 1
        if self.age > self.warn:
            self.angle += self.delta
            for p in world.alive_players():
                if p.vulnerable():
                    a = boss.pos
                    b = a + Vector2(math.cos(self.angle), math.sin(self.angle)) * 1600
                    ab = b - a
                    t = max(0.0, min(1.0, (p.pos - a).dot(ab) / ab.length_squared()))
                    if p.pos.distance_to(a + ab * t) < 9 + p.r:
                        world.hurt_player(p, 1, p.pos, "beam")
        if self.age > self.warn + self.active:
            self.done = True

    def draw(self, surf, boss, t):
        a = boss.pos
        b = a + Vector2(math.cos(self.angle), math.sin(self.angle)) * 1600
        end_angle = self.angle + self.delta * self.active if self.age <= self.warn else self.angle + self.delta * max(0, self.warn + self.active - self.age)
        if self.age <= self.warn:
            k = 0.5 + 0.5 * (int(t / 3) % 2)
            gfx.dashed_line(surf, a, b, gfx.scale_color(self.color, 0.55 * k + 0.2), 2, 16, 12, t * 4)
        else:
            gfx.neon_line(surf, a, b, gfx.mix_white(self.color, 0.35), 8)
            pygame.draw.line(surf, gfx.WHITE, a, b, 3)
        # the area that is still going to be swept
        far = a + Vector2(math.cos(end_angle), math.sin(end_angle)) * 1600
        gfx.dashed_line(surf, a, far, gfx.scale_color(self.color, 0.42), 1, 10, 14, 0)
        steps = 10
        pts = [a]
        for i in range(steps + 1):
            ang = self.angle + (end_angle - self.angle) * i / steps
            pts.append(a + Vector2(math.cos(ang), math.sin(ang)) * 900)
        pygame.draw.lines(surf, gfx.scale_color(self.color, 0.25), False, pts[1:], 1)


class Boss:
    id = "sentinel"
    color = gfx.GREEN
    base_hp = 100
    r = 54
    thresholds = (0.66, 0.33)
    attacks = {1: ("a_burst",), 2: ("a_burst",), 3: ("a_burst",)}
    cooldowns = {1: 70, 2: 52, 3: 38}

    def __init__(self, world, hp_scale=1.0):
        self.pos = Vector2(W / 2, -130)
        self.anchor = Vector2(W / 2, 170)
        self.hp = self.max_hp = max(10, int(self.base_hp * hp_scale))
        self.phase = 1
        self.t = 0
        self.flash = 0
        self.intro = 110
        self.invuln_t = 0
        self.fading = False
        self.dying = False
        self.death_t = 0
        self.gone = False
        self.script = None
        self.wait = 60
        self.busy_move = False
        self.beams = []
        self.telegraph = None
        self.look = 0.0

    # ---- state ----------------------------------------------------------
    @property
    def invuln(self):
        return self.intro > 0 or self.invuln_t > 0 or self.fading

    def collide_circle(self, x, y, r):
        return (self.pos.x - x) ** 2 + (self.pos.y - y) ** 2 < (self.r + r) ** 2

    # ---- helpers for attacks ---------------------------------------------
    def aim(self, world, jitter=0.0):
        p = world.nearest_player(self.pos)
        if p is None:
            return math.pi / 2
        d = p.pos - self.pos
        return math.atan2(d.y, d.x) + jitter

    def random_target(self, world):
        players = world.alive_players()
        return world.rng.choice(players) if players else None

    def fire(self, world, angle, speed, r=6, color=None, kind="orb", **kw):
        return world.enemy_bullet(self.pos.x, self.pos.y, angle, speed, r=r, color=color or gfx.mix_white(self.color, 0.25), kind=kind, **kw)

    def ring(self, world, n, speed, offset=0.0, r=6, **kw):
        for i in range(n):
            self.fire(world, offset + i * math.tau / n, speed, r, **kw)

    def fan(self, world, angle, n, spread, speed, r=6, **kw):
        for i in range(n):
            a = angle + (i - (n - 1) / 2) * (spread / max(1, n - 1))
            self.fire(world, a, speed, r, **kw)

    def strike_near_players(self, world, n, r, delay, color, shards=0, shard_speed=3.6, spread=170):
        for _ in range(n):
            p = self.random_target(world)
            if p is None:
                return
            a = world.rng.random() * math.tau
            d = world.rng.uniform(0, spread)
            x = min(max(p.pos.x + math.cos(a) * d, 60), W - 60)
            y = min(max(p.pos.y + math.sin(a) * d, 90), H - 60)
            world.add_hazard(Blast(x, y, r, delay, color, 1, shards, shard_speed, "boss"))

    # ---- to override ---------------------------------------------------------
    def move(self, world, slow):
        pass

    def on_intro_end(self, world):
        pass

    def draw_body(self, surf, t, flash):
        pass

    # ---- frame update -------------------------------------------------------------
    def update(self, world):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.dying:
            self.update_dying(world)
            return
        slow = world.enemy_slow
        if self.intro > 0:
            self.intro -= 1
            self.pos += (self.anchor - self.pos) * 0.045
            if self.intro == 0:
                self.on_intro_end(world)
            return
        if self.invuln_t > 0:
            self.invuln_t -= 1
        for b in self.beams[:]:
            b.update(self, world)
            if b.done:
                self.beams.remove(b)
        self.check_phase(world)
        if not self.busy_move:
            self.move(world, slow)
        self.pos.x = min(max(self.pos.x, 60), W - 60)
        self.pos.y = min(max(self.pos.y, 60), H - 120)
        p = world.nearest_player(self.pos)
        if p is not None:
            d = p.pos - self.pos
            self.look = math.atan2(d.y, d.x)
        self.wait -= slow
        if self.wait <= 0:
            if self.script is None:
                names = self.attacks.get(self.phase) or self.attacks[max(self.attacks)]
                self.script = getattr(self, world.rng.choice(names))(world)
            try:
                self.wait = next(self.script) or 1
            except StopIteration:
                self.script = None
                self.busy_move = False
                self.telegraph = None
                self.wait = self.cooldowns.get(self.phase, 50) * (0.85 + 0.3 * world.rng.random())

    def check_phase(self, world):
        frac = self.hp / self.max_hp
        new_phase = 1 + sum(1 for th in self.thresholds if frac <= th)
        if new_phase > self.phase:
            self.phase = new_phase
            self.script = None
            self.busy_move = False
            self.wait = 80
            self.invuln_t = 50
            self.fading = False
            world.ebullets.clear()
            world.fx.add_flash(self.color, 0.7)
            world.fx.add_shake(12)
            world.fx.ring(self.pos.x, self.pos.y, self.color, 20, 320, 30, 6)
            world.emit("sfx", "boss_phase")
            world.emit("bark", "boss_phase")
            pt = world.free_point(120)
            world.spawn_pickup("power", pt.x, pt.y, world.random_power(), life=1000)
            if any(p.alive and p.hp < p.max_hp for p in world.players) or any(not p.alive for p in world.players):
                world.spawn_pickup("heart", pt.x + 40, pt.y, life=1000)

    def start_dying(self, world):
        self.dying = True
        self.death_t = 0
        self.script = None
        self.beams.clear()
        world.ebullets.clear()
        world.hazards[:] = [h for h in world.hazards if not isinstance(h, (Blast, Stripe))]

    def update_dying(self, world):
        self.death_t += 1
        if self.death_t % 5 == 0:
            a, d = world.rng.random() * math.tau, world.rng.uniform(0, self.r)
            world.fx.explosion(self.pos.x + math.cos(a) * d, self.pos.y + math.sin(a) * d, self.color, 1.6)
            world.emit("sfx", "explode")
            world.fx.add_shake(7)
        if self.death_t >= 110:
            world.fx.explosion(self.pos.x, self.pos.y, self.color, 4.5)
            world.fx.burst(self.pos.x, self.pos.y, gfx.WHITE, 60, 12, 4, life=(30, 60))
            world.fx.add_flash(gfx.WHITE, 1.0)
            world.fx.add_shake(20)
            self.gone = True

    # ---- drawing ---------------------------------------------------------------------
    def draw(self, surf, t):
        x, y = self.pos.x, self.pos.y
        for b in self.beams:
            b.draw(surf, self, t)
        if self.telegraph is not None:
            gfx.dashed_line(surf, self.pos, self.telegraph, gfx.scale_color(gfx.RED, 0.8), 2, 14, 10, t * 3)
        if self.fading:
            return
        gfx.draw_glow(surf, (x, y), int(self.r * 3.2), self.color, 0.55)
        flash = self.flash > 0 or (self.dying and self.death_t % 6 < 3)
        self.draw_body(surf, t, flash)
        if self.invuln and not self.dying:
            k = 0.5 + 0.5 * math.sin(t * 0.4)
            gfx.neon_circle(surf, (x, y), self.r + 12 + 3 * k, gfx.WHITE, 2, halo=False)


# =============================================================================
class Sentinel(Boss):
    id = "sentinel"
    color = gfx.GREEN
    base_hp = 110
    r = 54
    attacks = {1: ("a_burst", "a_ring"), 2: ("a_burst", "a_ring", "a_spiral", "a_cross"), 3: ("a_spiral", "a_cross", "a_dash", "a_burst")}
    cooldowns = {1: 70, 2: 52, 3: 36}

    def move(self, world, slow):
        c = Vector2(W / 2, 200)
        if self.phase == 1:
            goal = c + Vector2(math.cos(self.t * 0.016) * 180, math.sin(self.t * 0.016) * 60)
        elif self.phase == 2:
            goal = c + Vector2(math.sin(self.t * 0.022) * 340, 0)
        else:
            goal = c + Vector2(math.sin(self.t * 0.03) * 380, math.sin(self.t * 0.05) * 70)
        self.pos += (goal - self.pos) * 0.05 * slow

    def a_burst(self, w):
        for _ in range(3 if self.phase < 3 else 4):
            self.fan(w, self.aim(w), 3, 0.5, 5.2 if self.phase < 3 else 5.8)
            yield 24

    def a_ring(self, w):
        for k in range(2 + (self.phase > 1)):
            self.ring(w, 14, 3.4, self.t * 0.05 + k * 0.22)
            yield 34

    def a_spiral(self, w):
        for i in range(46):
            a = i * 0.24
            self.fire(w, a, 3.6)
            self.fire(w, a + math.pi, 3.6)
            yield 2
        yield 24

    def a_cross(self, w):
        for k in range(4):
            base = (math.pi / 4) * (k % 2)
            for j in range(4):
                for s in range(3):
                    self.fire(w, base + j * math.pi / 2, 2.8 + s * 0.7)
            yield 26

    def a_dash(self, w):
        p = self.random_target(w)
        if p is None:
            return
        target = Vector2(p.pos)
        self.telegraph = target
        self.busy_move = True
        yield 42
        self.telegraph = None
        d = target - self.pos
        vec = d.normalize() * 15 if d.length_squared() > 0 else Vector2(0, 15)
        for _ in range(16):
            self.pos += vec
            self.pos.x = min(max(self.pos.x, 60), W - 60)
            self.pos.y = min(max(self.pos.y, 60), H - 120)
            yield 1
        self.ring(w, 16, 3.6, 0.0)
        yield 30
        self.busy_move = False

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        col = self.color if self.phase == 1 else gfx.ORANGE if self.phase == 2 else gfx.RED
        fill = gfx.WHITE if flash else gfx.scale_color(col, 0.18)
        gfx.neon_poly(surf, gfx.poly_points(x, y, 62, 8, t * 0.008), col, 4, fill=fill)
        for i in range(4):
            a = -t * 0.02 + i * math.pi / 2
            tx, ty = x + math.cos(a) * 74, y + math.sin(a) * 74
            gfx.neon_poly(surf, gfx.poly_points(tx, ty, 11, 4, a), col, 2, fill=gfx.scale_color(col, 0.3))
        gfx.neon_circle(surf, (x, y), 34 + 3 * math.sin(t * 0.1), gfx.mix_white(col, 0.3), 3, fill=(4, 8, 10))
        ex, ey = x + math.cos(self.look) * 9, y + math.sin(self.look) * 9
        pygame.draw.circle(surf, gfx.WHITE, (int(ex), int(ey)), 15)
        pygame.draw.circle(surf, col if not flash else gfx.RED, (int(ex + math.cos(self.look) * 4), int(ey + math.sin(self.look) * 4)), 7)


class Weaver(Boss):
    id = "weaver"
    color = (0, 165, 255)
    base_hp = 170
    r = 50
    attacks = {1: ("a_weave", "a_curtain"), 2: ("a_weave", "a_curtain", "a_summon", "a_wall"), 3: ("a_curtain", "a_wall", "a_weave", "a_web")}
    cooldowns = {1: 64, 2: 50, 3: 34}

    def move(self, world, slow):
        goal = Vector2(W / 2 + math.sin(self.t * 0.014) * 420, 150 + math.sin(self.t * 0.03) * 34)
        self.pos += (goal - self.pos) * 0.05 * slow

    def a_weave(self, w):
        for i in range(30):
            a = math.pi / 2 + math.sin(i * 0.45) * 0.95
            self.fire(w, a, 3.7, turn=0.011 * math.cos(i * 0.45))
            yield 3
        yield 20

    def a_curtain(self, w):
        gap = w.rng.randint(3, 12)
        for _ in range(2 if self.phase < 3 else 3):
            for i in range(18):
                if abs(i - gap) <= 1:
                    continue
                w.enemy_bullet(30 + i * 72, 24, math.pi / 2, 3.0, r=7, color=self.color)
            gap = min(max(gap + w.rng.randint(-4, 4), 2), 14)
            yield 56

    def a_wall(self, w):
        for side in (0, 1):
            gap = w.rng.randint(120, H - 200)
            for i in range(14):
                y = 30 + i * 52
                if gap - 75 < y < gap + 75:
                    continue
                w.enemy_bullet(10 if side == 0 else W - 10, y, 0 if side == 0 else math.pi, 3.3, r=7, color=self.color)
            yield 70

    def a_summon(self, w):
        for kind, pos in (("lancer", (90, 90)), ("drone", (W - 90, 90))):
            if len(w.enemies) < 5:
                w.spawn_enemy(kind, pos, w.level)
        yield 50

    def a_web(self, w):
        for k in range(3):
            self.ring(w, 20, 3.0, k * 0.15, turn=0.006 * (1 if k % 2 else -1), r=5)
            yield 26
        self.fan(w, self.aim(w), 5, 0.7, 5.5)
        yield 30

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        col = self.color
        tips = []
        for i in range(8):
            a = t * 0.012 + i * math.tau / 8
            rad = 80 + 14 * math.sin(t * 0.06 + i)
            tips.append((x + math.cos(a) * rad, y + math.sin(a) * rad * 0.85))
        for i, tip in enumerate(tips):
            pygame.draw.line(surf, gfx.scale_color(col, 0.6), (x, y), tip, 2)
            pygame.draw.line(surf, gfx.scale_color(col, 0.35), tip, tips[(i + 2) % 8], 1)
            pygame.draw.circle(surf, gfx.mix_white(col, 0.5), (int(tip[0]), int(tip[1])), 6)
        gfx.neon_poly(surf, tips, gfx.scale_color(col, 0.7), 1, halo=False)
        core = gfx.poly_points(x, y, 42, 4, t * 0.02)
        gfx.neon_poly(surf, core, gfx.WHITE if flash else col, 3, fill=gfx.WHITE if flash else gfx.scale_color(col, 0.2))
        pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), 12)
        pygame.draw.circle(surf, col, (int(x + math.cos(self.look) * 4), int(y + math.sin(self.look) * 4)), 6)


class Inferno(Boss):
    id = "inferno"
    color = (255, 95, 40)
    base_hp = 240
    r = 56
    attacks = {1: ("a_rows", "a_pillars"), 2: ("a_rows", "a_pillars", "a_sweep", "a_flame_ring"), 3: ("a_rows", "a_sweep", "a_pillars", "a_flame_ring")}
    cooldowns = {1: 62, 2: 48, 3: 32}

    def collide_circle(self, x, y, r):
        return abs(x - self.pos.x) < 118 + r and abs(y - self.pos.y) < 44 + r

    def move(self, world, slow):
        goal = Vector2(W / 2 + math.sin(self.t * 0.011) * 430, 130)
        self.pos += (goal - self.pos) * 0.04 * slow

    def a_rows(self, w):
        gap = w.rng.randint(150, W - 150)
        for _ in range(2 if self.phase == 1 else 3):
            x = 24
            while x < W:
                if abs(x - gap) > 92:
                    w.enemy_bullet(x, 110, math.pi / 2, 3.4, r=7, color=self.color)
                x += 46
            gap = min(max(gap + w.rng.randint(-180, 180), 150), W - 150)
            yield 44

    def a_pillars(self, w):
        for _ in range(3 if self.phase < 3 else 4):
            self.strike_near_players(w, 1, 54, 62, self.color, 0)
            yield 22

    def a_sweep(self, w):
        base = self.aim(w)
        sign = w.rng.choice((-1, 1))
        self.beams.append(Beam(base - sign * 0.62, sign * 0.012, 52, 105, self.color))
        if self.phase == 3:
            self.beams.append(Beam(base - sign * 0.62 + math.pi, sign * 0.012, 52, 105, self.color))
        yield 165

    def a_flame_ring(self, w):
        for k in range(3):
            self.ring(w, 22, 3.2 + k * 0.4, k * 0.14)
            yield 24

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        col = self.color
        pts = gfx.cut_corner_points((x - 120, y - 46, 240, 92), 18)
        gfx.neon_poly(surf, pts, gfx.WHITE if flash else col, 4, fill=gfx.WHITE if flash else (36, 8, 6))
        for i in range(6):                                          # armour plates
            px = x - 100 + i * 40
            pygame.draw.rect(surf, gfx.scale_color(col, 0.35), (px, y - 30, 30, 60), 2)
        for i in range(9):                                          # flames along the top edge
            fx_ = x - 108 + i * 27
            h = 14 + 12 * math.sin(t * 0.3 + i * 1.7) + (t * 7 + i * 13) % 6
            pygame.draw.polygon(surf, (255, 180, 60), [(fx_ - 9, y - 46), (fx_, y - 46 - h), (fx_ + 9, y - 46)])
            pygame.draw.polygon(surf, col, [(fx_ - 5, y - 46), (fx_, y - 46 - h * 0.6), (fx_ + 5, y - 46)])
        for dx in (-46, 46):                                        # eyes
            pygame.draw.polygon(surf, gfx.WHITE if flash else (255, 235, 150), [(x + dx - 22, y - 8), (x + dx + 22, y - 14), (x + dx + 16, y + 4), (x + dx - 16, y + 6)])
        pygame.draw.circle(surf, col, (int(x), int(y + 6)), 18)
        pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y + 6)), 8)


class Cryo(Boss):
    id = "cryo"
    color = (140, 230, 255)
    base_hp = 300
    r = 52
    attacks = {1: ("a_shards", "a_icefall"), 2: ("a_shards", "a_icefall", "a_snow_ring"), 3: ("a_blizzard", "a_icefall", "a_snow_ring", "a_shards")}
    cooldowns = {1: 66, 2: 52, 3: 38}

    def move(self, world, slow):
        goal = Vector2(W / 2 + math.sin(self.t * 0.009) * 300, 190 + math.sin(self.t * 0.021) * 50)
        self.pos += (goal - self.pos) * 0.03 * slow

    def a_shards(self, w):
        for _ in range(3):
            self.fan(w, self.aim(w), 5, 0.9, 4.8, r=4, kind="shard")
            yield 30

    def a_icefall(self, w):
        self.strike_near_players(w, 3, 48, 68, self.color, 5, 3.2)
        yield 90

    def a_snow_ring(self, w):
        for k in range(4):
            self.ring(w, 20, 2.6, k * 0.2, turn=0.007 * (1 if k % 2 else -1), r=5)
            yield 26

    def a_blizzard(self, w):
        for _ in range(48):
            self.fire(w, w.rng.random() * math.tau, w.rng.uniform(1.8, 3.6), r=4, turn=w.rng.uniform(-0.010, 0.010))
            yield 3
        yield 20

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        col = self.color
        pts = []
        for i in range(12):
            r = 74 if i % 2 == 0 else 36
            a = t * 0.006 + i * math.tau / 12
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        gfx.neon_poly(surf, pts, gfx.WHITE if flash else col, 3, fill=gfx.WHITE if flash else (10, 34, 48))
        inner = gfx.poly_points(x, y, 30, 6, -t * 0.012)
        gfx.neon_poly(surf, inner, gfx.mix_white(col, 0.4), 2, fill=(20, 70, 96))
        pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), 11)
        pygame.draw.circle(surf, (40, 120, 200), (int(x + math.cos(self.look) * 4), int(y + math.sin(self.look) * 4)), 6)


class GlitchClone(Enemy):
    """A decoy of the Glitch boss: teleports and shoots, dies in a few hits."""
    kind = "clone"
    base_color = (255, 65, 240)
    score = 0
    coins = (1, 2)

    def setup(self, world):
        self.r = 24
        self.hp = 4
        self.spawn = 24
        self.cd = 70
        self.tp = 130

    def ai(self, world, slow):
        self.tp -= slow
        self.cd -= slow
        if self.tp <= 0:
            self.pos = Vector2(world.rng.randint(120, W - 120), world.rng.randint(90, 330))
            world.fx.burst(self.pos.x, self.pos.y, self.color, 10, 4)
            self.tp = world.rng.randint(110, 170)
        target = world.nearest_player(self.pos)
        if target is not None and self.cd <= 0:
            a = self.aim_at(target)
            for off in (-0.2, 0.0, 0.2):
                self.fire(world, a + off, 4.4, r=5)
            self.cd = world.rng.randint(80, 120)

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        for dx, col in ((-3, (255, 65, 240)), (3, (70, 255, 200))):
            r = pygame.Rect(0, 0, 40, 40)
            r.center = (int(x + dx), int(y))
            pygame.draw.rect(surf, col, r, 2)
        pygame.draw.rect(surf, gfx.WHITE if flash else gfx.scale_color(self.color, 0.3), (x - 16, y - 16, 32, 32))


class Glitch(Boss):
    id = "glitch"
    color = (255, 65, 240)
    base_hp = 340
    r = 46
    attacks = {1: ("a_blink", "a_stripes"), 2: ("a_blink", "a_stripes", "a_clones", "a_spiral"), 3: ("a_blink", "a_spiral", "a_stripes", "a_clones")}
    cooldowns = {1: 56, 2: 44, 3: 30}

    def move(self, world, slow):
        goal = Vector2(W / 2 + math.sin(self.t * 0.02) * 260, 180 + math.sin(self.t * 0.037) * 40)
        self.pos += (goal - self.pos) * 0.04 * slow

    def a_blink(self, w):
        self.fading = True
        self.busy_move = True
        yield 26
        self.pos = Vector2(w.rng.randint(160, W - 160), w.rng.randint(110, 300))
        w.fx.burst(self.pos.x, self.pos.y, self.color, 16, 6)
        yield 14
        self.fading = False
        self.ring(w, 16, 3.6, w.rng.random())
        self.fan(w, self.aim(w), 5, 0.8, 5.2)
        yield 24
        if self.phase == 3:
            self.ring(w, 16, 3.2, 0.2)
            yield 20
        self.busy_move = False

    def a_stripes(self, w):
        for _ in range(3 if self.phase < 3 else 4):
            p = self.random_target(w)
            if p is None:
                return
            w.add_hazard(Stripe(p.pos.x + w.rng.uniform(-90, 90), 64, w.rng.random() < 0.7, 52, 22, self.color))
            yield 30

    def a_clones(self, w):
        alive = len([e for e in w.enemies if e.kind == "clone"])
        for _ in range(2 - alive):
            c = GlitchClone(w, w.rng.randint(150, W - 150), w.rng.randint(100, 320), w.level)
            w.enemies.append(c)
        yield 60

    def a_spiral(self, w):
        for i in range(60):
            a = i * 0.21 * (1 if i < 30 else -1) + self.t * 0.01
            self.fire(w, a, 3.7)
            self.fire(w, a + math.pi * 2 / 3, 3.7)
            self.fire(w, a + math.pi * 4 / 3, 3.7)
            yield 2
        yield 20

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        jit = int(t / 2) % 5
        for dx, col in ((-6 + jit, (255, 65, 240)), (6 - jit, (70, 255, 200)), (0, gfx.WHITE if flash else (12, 4, 20))):
            for k in range(5):
                w_, h_ = 80 - k * 8, 18
                oy = y - 46 + k * 19
                jx = ((t * 7 + k * 31) % 9) - 4 if int(t / 5) % 3 == 0 else 0
                pygame.draw.rect(surf, col, (x - w_ / 2 + dx + jx, oy, w_, h_), 2 if col != (12, 4, 20) and col != gfx.WHITE else 0)
        pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), 12)
        pygame.draw.circle(surf, (255, 65, 240), (int(x + math.cos(self.look) * 4), int(y + math.sin(self.look) * 4)), 6)


class Origin(Boss):
    id = "origin"
    color = (190, 140, 255)
    base_hp = 560
    r = 56
    thresholds = (0.75, 0.5, 0.25)
    attacks = {
        1: ("a_void_rings", "a_stream"),
        2: ("a_void_rings", "a_curtain", "a_spiral"),
        3: ("a_sweep", "a_collapse", "a_curtain", "a_void_rings"),
        4: ("a_spiral4", "a_sweep", "a_collapse", "a_stream", "a_curtain"),
    }
    cooldowns = {1: 64, 2: 50, 3: 40, 4: 28}

    def move(self, world, slow):
        goal = Vector2(W / 2 + math.sin(self.t * 0.012) * 200, 190 + math.sin(self.t * 0.02) * 40)
        self.pos += (goal - self.pos) * 0.03 * slow

    def a_void_rings(self, w):
        for k in range(4):
            self.ring(w, 18, 2.8 + 0.3 * (k % 2), k * 0.17, r=6)
            yield 26

    def a_stream(self, w):
        for _ in range(14):
            self.fire(w, self.aim(w, w.rng.uniform(-0.12, 0.12)), 3.0, r=5, accel=1.014)
            yield 5
        yield 16

    def a_curtain(self, w):
        gap = w.rng.randint(3, 12)
        for _ in range(3):
            for i in range(18):
                if abs(i - gap) <= 1:
                    continue
                w.enemy_bullet(30 + i * 72, 24, math.pi / 2, 3.1, r=7, color=self.color)
            gap = min(max(gap + w.rng.randint(-4, 4), 2), 14)
            yield 52

    def a_spiral(self, w):
        for i in range(50):
            a = i * 0.23
            self.fire(w, a, 3.6)
            self.fire(w, a + math.pi, 3.6)
            yield 2
        yield 20

    def a_spiral4(self, w):
        for i in range(70):
            a = i * 0.19
            for k in range(4):
                self.fire(w, a + k * math.pi / 2, 3.8)
            yield 2
        yield 20

    def a_sweep(self, w):
        base = self.aim(w)
        sign = w.rng.choice((-1, 1))
        for k in range(2):
            self.beams.append(Beam(base - sign * 0.62 + k * math.pi, sign * 0.011, 54, 110, self.color))
        yield 175

    def a_collapse(self, w):
        self.strike_near_players(w, 5 if self.phase < 4 else 7, 66, 78, self.color, 0, spread=230)
        yield 70

    def draw_body(self, surf, t, flash):
        x, y = self.pos.x, self.pos.y
        col = self.color if self.phase < 4 else gfx.mix_white(gfx.RED, 0.2)
        for i in range(28):                                          # jagged corona
            a = t * 0.01 + i * math.tau / 28
            r0, r1 = 62, 84 + 14 * math.sin(t * 0.09 + i * 2.1)
            pygame.draw.line(surf, gfx.scale_color(col, 0.7), (x + math.cos(a) * r0, y + math.sin(a) * r0), (x + math.cos(a) * r1, y + math.sin(a) * r1), 3)
        pygame.draw.circle(surf, gfx.WHITE if flash else (2, 0, 6), (int(x), int(y)), 58)
        pygame.draw.circle(surf, col, (int(x), int(y)), 58, 4)
        pygame.draw.circle(surf, gfx.scale_color(col, 0.5), (int(x), int(y)), 48, 1)
        for i in range(3):
            a = -t * 0.03 + i * math.tau / 3
            gfx.neon_circle(surf, (x + math.cos(a) * 96, y + math.sin(a) * 96 * 0.8), 9, col, 2, fill=(2, 0, 6))
        eye = pygame.Rect(0, 0, 14, 44)
        eye.center = (int(x + math.cos(self.look) * 6), int(y + math.sin(self.look) * 6))
        pygame.draw.ellipse(surf, gfx.WHITE, eye)
        pygame.draw.ellipse(surf, col, eye.inflate(-8, -10))


BOSSES = {b.id: b for b in (Sentinel, Weaver, Inferno, Cryo, Glitch, Origin)}


def make_boss(world, boss_id, hp_scale=1.0):
    return BOSSES[boss_id](world, hp_scale)
