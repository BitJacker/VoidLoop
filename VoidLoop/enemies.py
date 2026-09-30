"""Enemy types: Drone, Bulwark, Lancer, Comet, Splitter and Orbiter."""
import math

import pygame
from pygame import Vector2

from . import gfx
from .entities import Bullet
from .settings import W, H

ENEMY_TYPES = ("drone", "bulwark", "lancer", "comet", "splitter", "orbiter")
SPAWN_FRAMES = 40


class Enemy:
    kind = "drone"
    base_color = gfx.RED
    score = 100
    coins = (0, 1)               # (chance-based min, max) - see World.drop_loot
    _next_id = 0

    def __init__(self, world, x, y, level=1, elite=False, mini=False):
        self.pos = Vector2(x, y)
        self.knock = Vector2()
        self.level = level
        self.elite = elite
        self.spawn = SPAWN_FRAMES
        self.flash = 0
        self.age = 0
        self.angle = 0.0
        self.id = Enemy._next_id
        Enemy._next_id += 1
        self.color = self.base_color
        self.r = 12
        self.hp = 1
        self.speed = 1.0
        self.cd = 120
        self.mini = mini
        self.setup(world)
        if elite:
            self.hp = self.hp * 2 + 1
            self.r = int(self.r * 1.3)
            self.score *= 2
        self.max_hp = self.hp

    # -- to be overridden --------------------------------------------------------
    def setup(self, world):
        pass

    def ai(self, world, slow):
        pass

    def draw_body(self, surf, t, fill):
        pass

    def on_death(self, world):
        pass

    # -- helpers ---------------------------------------------------------------------
    def scaled_speed(self, world, base, cap=4.8):
        return min(base * world.cfg["speed"], cap)

    def aim_at(self, target):
        d = target.pos - self.pos
        return math.atan2(d.y, d.x)

    def fire(self, world, angle, speed, r=5, color=None, kind="orb"):
        world.enemy_bullet(self.pos.x, self.pos.y, angle, speed, r=r, color=color or self.color, kind=kind)

    # -- frame update -----------------------------------------------------------------
    def update(self, world):
        if self.spawn > 0:
            self.spawn -= 1
            return
        self.age += 1
        if self.flash > 0:
            self.flash -= 1
        slow = world.enemy_slow
        self.ai(world, slow)
        self.pos += self.knock
        self.knock *= 0.85
        self.pos += world.forces_at(self.pos, self.r) * 0.6
        self.pos.x = min(max(self.pos.x, self.r), W - self.r)
        self.pos.y = min(max(self.pos.y, self.r), H - self.r)

    def hit(self, dmg):
        self.hp -= dmg
        self.flash = 5
        return self.hp <= 0

    @property
    def solid(self):
        """False while warping in (can't be hit and can't hurt)."""
        return self.spawn <= 0

    # -- drawing ---------------------------------------------------------------------------
    def draw(self, surf, t):
        x, y = self.pos.x, self.pos.y
        if self.spawn > 0:
            k = self.spawn / SPAWN_FRAMES
            radius = int(self.r * 0.6 + self.r * 2.2 * k)
            pygame.draw.circle(surf, gfx.scale_color(self.color, 0.4 + 0.6 * (1 - k)), (int(x), int(y)), radius, 2)
            gfx.draw_glow(surf, (x, y), self.r * 2, self.color, 0.5 * (1 - k))
            return
        fill = (255, 255, 255) if self.flash > 0 else gfx.scale_color(self.color, 0.2)
        gfx.draw_glow(surf, (x, y), int(self.r * 2.6), self.color, 0.55)
        self.draw_body(surf, t, fill)
        if self.elite:
            gfx.neon_circle(surf, (x, y), self.r + 6, gfx.GOLD, 1, halo=False)
        if self.max_hp > 1 and self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (60, 0, 0), (x - self.r, y - self.r - 10, w, 4))
            pygame.draw.rect(surf, (60, 255, 90), (x - self.r, y - self.r - 10, w * self.hp / self.max_hp, 4))


class Drone(Enemy):
    kind = "drone"
    base_color = gfx.RED
    score = 100
    coins = (0, 1)

    def setup(self, world):
        lvl = self.level
        base = 1.0 + 0.1 * min(lvl, 8) + 0.05 * max(0, lvl - 8)
        self.r = 8 if self.mini else 12
        self.speed = self.scaled_speed(world, base * (1.5 if self.mini else 1.0), 4.6)
        self.hp = 1 + (1 if lvl >= 14 and not self.mini else 0)
        self.cd = world.rng.randint(90, 180) if lvl < 7 else world.rng.randint(60, 120)
        self.wobble = world.rng.random() * math.tau
        if self.mini:
            self.color = (255, 120, 140)
            self.score = 50

    def ai(self, world, slow):
        target = world.nearest_player(self.pos)
        if target is None:
            return
        d = target.pos - self.pos
        dist = d.length() or 1.0
        base = math.atan2(d.y, d.x)
        self.angle = base
        sway = math.sin(self.age * 0.05 + self.wobble) * 0.35 if dist > 140 else 0.0
        a = base + sway
        self.pos.x += math.cos(a) * self.speed * slow
        self.pos.y += math.sin(a) * self.speed * slow
        if world.enemies_shoot and not self.mini:
            self.cd -= slow
            if self.cd <= 0 and dist < 720:
                self.fire(world, base, 5.0 * (1.0 if self.level < 8 else 1.15))
                self.cd = world.rng.randint(110, 200) if self.level < 7 else world.rng.randint(70, 130)

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        pts = gfx.poly_points(x, y, self.r * 1.3, 4, self.angle + math.pi / 4 + (math.sin(t * 0.08 + self.wobble) * 0.1))
        gfx.neon_poly(surf, pts, self.color, 2, fill=fill)
        ex, ey = x + math.cos(self.angle) * self.r * 0.35, y + math.sin(self.angle) * self.r * 0.35
        pygame.draw.circle(surf, gfx.WHITE, (int(ex), int(ey)), max(2, int(self.r * 0.28)))


class Bulwark(Enemy):
    kind = "bulwark"
    base_color = (255, 110, 60)
    score = 300
    coins = (1, 3)

    def setup(self, world):
        self.r = 20
        self.speed = self.scaled_speed(world, 0.8 + 0.05 * self.level, 3.0)
        self.hp = 3 + self.level // 2
        self.cd = world.rng.randint(150, 250)
        self.spin = 0.0
        self.shooting = False

    def ai(self, world, slow):
        self.shooting = world.enemies_shoot
        target = world.nearest_player(self.pos)
        if target is None:
            return
        d = target.pos - self.pos
        dist = d.length() or 1.0
        self.angle = math.atan2(d.y, d.x)
        self.spin += 0.03
        if dist > 150:
            self.pos += d / dist * self.speed * slow
        if world.enemies_shoot:
            self.cd -= slow
            if self.cd <= 0 and dist < 760:
                for off in (-0.24, 0.0, 0.24):
                    self.fire(world, self.angle + off, 5.2, r=6)
                self.cd = world.rng.randint(150, 250)

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        gfx.neon_poly(surf, gfx.poly_points(x, y, self.r * 1.15, 6, self.spin * 0.3), self.color, 3, fill=fill)
        gfx.neon_poly(surf, gfx.poly_points(x, y, self.r * 0.6, 3, self.spin), gfx.mix_white(self.color, 0.4), 2, halo=False)
        if self.cd < 22 and self.shooting:
            gfx.draw_glow(surf, (x + math.cos(self.angle) * self.r, y + math.sin(self.angle) * self.r), 24, gfx.WHITE, 0.9)


class Lancer(Enemy):
    kind = "lancer"
    base_color = gfx.ORANGE
    score = 200
    coins = (0, 2)

    def setup(self, world):
        self.r = 10
        self.speed = self.scaled_speed(world, 0.9 + 0.03 * self.level, 3.0)
        self.hp = 1 + (1 if self.level >= 12 else 0)
        self.cd = world.rng.randint(80, 140)
        self.state = "move"
        self.aim_t = 0
        self.side = world.rng.choice((-1, 1))

    def ai(self, world, slow):
        target = world.nearest_player(self.pos)
        if target is None:
            return
        d = target.pos - self.pos
        dist = d.length() or 1.0
        unit = d / dist
        if self.state == "move":
            self.angle = math.atan2(d.y, d.x)
            if dist < 250:
                self.pos -= unit * self.speed * 1.4 * slow
            elif dist > 380:
                self.pos += unit * self.speed * 0.9 * slow
            else:
                self.pos += Vector2(-unit.y, unit.x) * self.side * self.speed * 0.7 * slow
            if world.enemies_shoot:
                self.cd -= slow
                if self.cd <= 0:
                    self.state, self.aim_t = "aim", 40
        else:
            self.aim_t -= 1
            if self.aim_t > 12:                       # still tracking
                self.angle = math.atan2(d.y, d.x)
            if self.aim_t <= 0:
                self.fire(world, self.angle, 10.0, r=4, kind="shard")
                self.state = "move"
                self.cd = world.rng.randint(110, 170)
                self.side = world.rng.choice((-1, 1))

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        a = self.angle
        pts = [(x + math.cos(a) * self.r * 1.8, y + math.sin(a) * self.r * 1.8),
               (x + math.cos(a + 2.5) * self.r * 1.2, y + math.sin(a + 2.5) * self.r * 1.2),
               (x + math.cos(a + math.pi) * self.r * 0.5, y + math.sin(a + math.pi) * self.r * 0.5),
               (x + math.cos(a - 2.5) * self.r * 1.2, y + math.sin(a - 2.5) * self.r * 1.2)]
        gfx.neon_poly(surf, pts, self.color, 2, fill=fill)
        if self.state == "aim":
            locked = self.aim_t <= 12
            end = (x + math.cos(a) * 1500, y + math.sin(a) * 1500)
            color = gfx.WHITE if locked else gfx.scale_color(gfx.RED, 0.6 + 0.4 * math.sin(t * 0.6))
            if locked:
                pygame.draw.line(surf, color, (x, y), end, 2)
            else:
                gfx.dashed_line(surf, (x, y), end, color, 1, 14, 10, t * 3)
            gfx.draw_glow(surf, (x + math.cos(a) * self.r * 1.8, y + math.sin(a) * self.r * 1.8), 18, gfx.RED, 0.9)


class Comet(Enemy):
    kind = "comet"
    base_color = (255, 40, 255)
    score = 150
    coins = (0, 1)

    def setup(self, world):
        self.r = 9
        self.rush_speed = self.scaled_speed(world, 3.4 + 0.14 * self.level, 8.6)
        self.speed = self.rush_speed * 0.5
        self.hp = 1
        self.state = "stalk"
        self.timer = world.rng.randint(50, 100)
        self.dir = Vector2(1, 0)
        self.trail = []

    def ai(self, world, slow):
        target = world.nearest_player(self.pos)
        if target is None:
            return
        d = target.pos - self.pos
        dist = d.length() or 1.0
        if self.state == "stalk":
            self.angle = math.atan2(d.y, d.x)
            self.pos += d / dist * self.speed * slow
            self.timer -= slow
            if self.timer <= 0 or dist < 260:
                self.state, self.timer = "charge", 30
        elif self.state == "charge":
            self.angle = math.atan2(d.y, d.x)
            self.timer -= 1
            if self.timer <= 0:
                self.dir = Vector2(math.cos(self.angle), math.sin(self.angle))
                self.state, self.timer = "rush", 60
                world.emit("sfx", "comet")
        else:
            self.pos += self.dir * self.rush_speed * slow
            self.timer -= slow
            self.trail.append((self.pos.x, self.pos.y))
            if len(self.trail) > 8:
                self.trail.pop(0)
            if self.timer <= 0:
                self.state, self.timer = "stalk", world.rng.randint(60, 110)
                self.trail.clear()
        if self.state != "rush" and self.trail:
            self.trail.pop(0)

    def on_death(self, world):
        world.blast(self.pos.x, self.pos.y, 62, self.color, dmg_enemies=2, dmg_players=0)

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        for i, (tx, ty) in enumerate(self.trail):
            k = (i + 1) / (len(self.trail) + 1)
            pygame.draw.circle(surf, gfx.scale_color(self.color, 0.7 * k), (int(tx), int(ty)), max(1, int(self.r * k * 0.8)))
        a = self.angle
        pts = [(x + math.cos(a) * self.r * 1.7, y + math.sin(a) * self.r * 1.7),
               (x + math.cos(a + 2.6) * self.r * 1.2, y + math.sin(a + 2.6) * self.r * 1.2),
               (x + math.cos(a - 2.6) * self.r * 1.2, y + math.sin(a - 2.6) * self.r * 1.2)]
        flicker = self.state == "charge" and int(t / 3) % 2 == 0
        gfx.neon_poly(surf, pts, gfx.WHITE if flicker else self.color, 2, fill=fill)
        if self.state == "charge":
            end = (x + math.cos(a) * 240, y + math.sin(a) * 240)
            gfx.dashed_line(surf, (x, y), end, gfx.scale_color(self.color, 0.7), 1, 8, 8, t * 2)


class Splitter(Enemy):
    kind = "splitter"
    base_color = (150, 255, 90)
    score = 200
    coins = (0, 2)

    def setup(self, world):
        self.r = 16
        self.speed = self.scaled_speed(world, (1.0 + 0.09 * min(self.level, 12)) * 0.85, 3.6)
        self.hp = 2 + self.level // 8
        self.phase = world.rng.random() * math.tau

    def ai(self, world, slow):
        target = world.nearest_player(self.pos)
        if target is None:
            return
        d = target.pos - self.pos
        dist = d.length() or 1.0
        self.angle = math.atan2(d.y, d.x)
        self.pos += d / dist * self.speed * slow

    def on_death(self, world):
        for k in (-1, 1):
            mini = world.spawn_enemy("drone", (self.pos.x + k * 12, self.pos.y), self.level, mini=True, instant=True)
            if mini is not None:
                mini.knock = Vector2(k * 6, 0)

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        pulse = 1.0 + 0.08 * math.sin(t * 0.15 + self.phase)
        gfx.neon_circle(surf, (x, y), self.r * pulse, self.color, 2, fill=fill)
        for k in (-1, 1):
            cx = x + math.cos(t * 0.05 + self.phase) * 6 * k
            cy = y + math.sin(t * 0.05 + self.phase) * 6 * k
            pygame.draw.circle(surf, gfx.mix_white(self.color, 0.5), (int(cx), int(cy)), 5)


class Orbiter(Enemy):
    kind = "orbiter"
    base_color = (90, 200, 255)
    score = 250
    coins = (1, 2)

    def setup(self, world):
        self.r = 13
        self.speed = self.scaled_speed(world, 2.2 + 0.05 * self.level, 4.2)
        self.hp = 2
        self.cd = world.rng.randint(90, 150)
        self.dir = world.rng.choice((-1, 1))
        self.orbit = world.rng.uniform(210, 290)
        self.phase = world.rng.random() * math.tau

    def ai(self, world, slow):
        target = world.nearest_player(self.pos)
        if target is None:
            return
        rel = self.pos - target.pos
        ang = math.atan2(rel.y, rel.x) + self.dir * 0.017 * slow
        radius = self.orbit + math.sin(self.age * 0.02 + self.phase) * 40
        goal = target.pos + Vector2(math.cos(ang), math.sin(ang)) * radius
        move = goal - self.pos
        dist = move.length()
        if dist > 1:
            self.pos += move / dist * min(self.speed * slow, dist)
        self.angle = math.atan2(-rel.y, -rel.x)
        if world.enemies_shoot:
            self.cd -= slow
            if self.cd <= 0:
                for off in (-0.13, 0.0, 0.13):
                    self.fire(world, self.angle + off, 5.0, r=5)
                self.cd = world.rng.randint(110, 170)

    def draw_body(self, surf, t, fill):
        x, y = self.pos.x, self.pos.y
        gfx.neon_circle(surf, (x, y), self.r, self.color, 2, fill=fill)
        for i in range(3):
            a = t * 0.08 * self.dir + i * math.tau / 3
            pygame.draw.circle(surf, gfx.mix_white(self.color, 0.6), (int(x + math.cos(a) * (self.r + 7)), int(y + math.sin(a) * (self.r + 7))), 3)


ENEMY_CLASSES = {"drone": Drone, "bulwark": Bulwark, "lancer": Lancer, "comet": Comet, "splitter": Splitter, "orbiter": Orbiter}


def make_enemy(world, kind, x, y, level, elite=False, mini=False):
    return ENEMY_CLASSES[kind](world, x, y, level, elite, mini)
