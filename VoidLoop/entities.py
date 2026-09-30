"""Core entities: input snapshot, bullets, players and pickups."""
import math
from dataclasses import dataclass, field

from pygame import Vector2

from .settings import W, H

BASE_SPEED = 6.0
SPRINT_MULT = 1.8
DASH_DISTANCE = 130.0
DASH_FRAMES = 8
PLAYER_RADIUS = 9
IFRAMES_ON_HIT = 90


@dataclass
class PlayerInput:
    """One frame of intent for one player - produced by the keyboard/mouse (or a bot)."""
    move: Vector2 = field(default_factory=Vector2)
    aim: object = None               # Vector2 world position to aim at, None = auto-aim
    fire: bool = False
    dash: bool = False               # edge-triggered
    sprint: bool = False
    pulse: bool = False              # edge-triggered
    weapon_step: int = 0
    weapon_index: int = -1


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def push_out_of_rect(pos, r, rect):
    """Push a circle out of a pygame.Rect. Returns True when it was overlapping."""
    cx = clamp(pos.x, rect.left, rect.right)
    cy = clamp(pos.y, rect.top, rect.bottom)
    dx, dy = pos.x - cx, pos.y - cy
    d2 = dx * dx + dy * dy
    if d2 >= r * r:
        return False
    if d2 > 1e-6:
        d = math.sqrt(d2)
        k = (r - d) / d
        pos.x += dx * k
        pos.y += dy * k
    else:                                    # centre is inside the rectangle
        left, right = pos.x - rect.left, rect.right - pos.x
        top, bottom = pos.y - rect.top, rect.bottom - pos.y
        m = min(left, right, top, bottom)
        if m == left:
            pos.x = rect.left - r
        elif m == right:
            pos.x = rect.right + r
        elif m == top:
            pos.y = rect.top - r
        else:
            pos.y = rect.bottom + r
    return True


class Bullet:
    """A projectile. ``friendly`` bullets hurt enemies, the others hurt players."""
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "color", "friendly", "life", "pierce", "hit", "kind",
                 "grazed", "px", "py", "wall_pass", "accel", "turn", "owner")

    def __init__(self, x, y, vx, vy, r=4, dmg=1, color=(255, 255, 255), friendly=False, life=300, pierce=0,
                 kind="orb", wall_pass=False, accel=1.0, turn=0.0, owner=0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.px, self.py = x, y
        self.r = r
        self.dmg = dmg
        self.color = color
        self.friendly = friendly
        self.life = life
        self.pierce = pierce
        self.hit = None
        self.kind = kind
        self.grazed = False
        self.wall_pass = wall_pass
        self.accel = accel
        self.turn = turn
        self.owner = owner

    def update(self, walls, slow=1.0):
        self.px, self.py = self.x, self.y
        if self.turn:
            c, s = math.cos(self.turn * slow), math.sin(self.turn * slow)
            self.vx, self.vy = self.vx * c - self.vy * s, self.vx * s + self.vy * c
        if self.accel != 1.0:
            self.vx *= self.accel
            self.vy *= self.accel
        self.x += self.vx * slow
        self.y += self.vy * slow
        self.life -= 1
        if self.life <= 0:
            return False
        if not (-60 < self.x < W + 60 and -60 < self.y < H + 60):
            return False
        if not self.wall_pass:
            x, y, r = self.x, self.y, self.r
            for w in walls:
                if w.left - r < x < w.right + r and w.top - r < y < w.bottom + r:
                    return False
        return True


class Player:
    def __init__(self, pid, x, y, color, max_hp):
        self.id = pid
        self.pos = Vector2(x, y)
        self.vel = Vector2()
        self.r = PLAYER_RADIUS
        self.color = color
        self.max_hp = max_hp
        self.hp = max_hp
        self.alive = True
        self.iframes = 0
        self.flash = 0
        self.aim = -math.pi / 2
        self.fire_cd = 0
        self.dash_time = 0
        self.dash_cd = 0
        self.dash_vec = Vector2()
        self.sprinting = False
        self.stamina = 100.0
        self.exhausted = False
        self.energy = 0.0
        self.trail = []                 # afterimages while dashing
        self.thrust = 0.0
        self.swing = None               # Mace state (Horde)
        self.last_move = Vector2(0, -1)
        self.hit_taken = 0

    # ---- state ------------------------------------------------------------
    @property
    def dashing(self):
        return self.dash_time > 0

    def vulnerable(self):
        return self.alive and self.iframes <= 0

    def heal(self, amount=1):
        self.hp = min(self.max_hp, self.hp + amount)

    def revive(self, hp=1, iframes=120):
        self.alive = True
        self.hp = min(self.max_hp, max(1, hp))
        self.iframes = iframes
        self.swing = None

    # ---- per-frame update -----------------------------------------------------
    def update(self, world, inp):
        if not self.alive:
            return
        if self.iframes > 0:
            self.iframes -= 1
        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.fire_cd > 0:
            self.fire_cd -= 1

        move = inp.move
        moving = move.length_squared() > 0.0001
        if moving:
            move = move.normalize() if move.length_squared() > 1 else move
            self.last_move = Vector2(move)

        # aim
        if inp.aim is not None:
            d = inp.aim - self.pos
            if d.length_squared() > 4:
                self.aim = math.atan2(d.y, d.x)
        elif moving:
            self.aim = math.atan2(move.y, move.x)

        # speed / sprint (stamina)
        speed = BASE_SPEED
        if world.has_power("SPEED"):
            speed *= 1.5
        if inp.sprint and moving and self.stamina > 0 and not self.exhausted:
            self.sprinting = True
            speed *= SPRINT_MULT
            self.stamina -= 1.0
            if self.stamina <= 0:
                self.exhausted = True
        else:
            self.sprinting = False
            self.stamina = min(100.0, self.stamina + 0.75)
            if self.exhausted and self.stamina >= 30:
                self.exhausted = False

        # dash: a fast burst with invulnerability
        if inp.dash and self.dash_cd <= 0 and self.dash_time <= 0:
            direction = Vector2(move) if moving else Vector2(math.cos(self.aim), math.sin(self.aim))
            if direction.length_squared() > 0:
                self.dash_vec = direction.normalize() * (DASH_DISTANCE / DASH_FRAMES)
                self.dash_time = DASH_FRAMES
                self.dash_cd = world.loadout.dash_cooldown()
                self.iframes = max(self.iframes, DASH_FRAMES + 8)
                world.on_dash(self)

        if self.dash_time > 0:
            self.dash_time -= 1
            self.vel = Vector2(self.dash_vec)
            self.trail.append((self.pos.x, self.pos.y, self.aim))
            if len(self.trail) > 6:
                self.trail.pop(0)
        else:
            if self.trail:
                self.trail.pop(0)
            target = move * speed if moving else Vector2()
            accel = 0.05 if world.ice else 0.55
            self.vel += (target - self.vel) * accel

        self.thrust = min(1.0, self.vel.length() / (BASE_SPEED * 1.4))
        self.pos += self.vel + world.forces_at(self.pos, self.r)

        for wall in world.walls:
            push_out_of_rect(self.pos, self.r, wall)
        self.pos.x = clamp(self.pos.x, self.r, W - self.r)
        self.pos.y = clamp(self.pos.y, self.r, H - self.r)

        # weapons
        if inp.weapon_step:
            world.loadout.cycle(inp.weapon_step)
        if inp.weapon_index >= 0:
            world.loadout.select_index(inp.weapon_index)
        if inp.fire:
            world.player_fire(self, inp)
        if inp.pulse:
            world.use_pulse(self)


class Pickup:
    """Collectables: fragments, coins, hearts and power-ups."""
    __slots__ = ("kind", "pos", "vel", "r", "life", "power", "t", "value")

    def __init__(self, kind, x, y, power=None, value=1, life=None):
        self.kind = kind
        self.pos = Vector2(x, y)
        self.vel = Vector2()
        self.r = {"fragment": 13, "coin": 8, "heart": 13, "power": 15}[kind]
        self.life = life
        self.power = power
        self.value = value
        self.t = 0
