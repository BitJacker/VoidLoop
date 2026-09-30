"""A small autopilot. It drives the menu's attract mode and the test-suite's balance simulations."""
import math

from pygame import Vector2

from .entities import PlayerInput
from .settings import W, H


class Bot:
    """Dodges bullets, chases fragments/pickups and shoots the nearest enemy.

    ``skill`` (0..1) scales reaction quality so tests can model weaker players.
    """

    def __init__(self, skill=0.8):
        self.skill = skill
        self.t = 0
        self.dash_cd = 0
        self.wander = Vector2(1, 0)

    def inputs(self, world):
        self.t += 1
        return {p.id: self.decide(world, p) for p in world.players if p.alive}

    # -------------------------------------------------------------------------
    def decide(self, world, p):
        pos = p.pos
        danger = Vector2()
        urgent = 0.0
        for b in world.ebullets:
            dx, dy = pos.x - b.x, pos.y - b.y
            d2 = dx * dx + dy * dy
            if d2 > 200 * 200:
                continue
            # will it pass close to me? project the bullet forward
            vx, vy = b.vx, b.vy
            sp2 = vx * vx + vy * vy or 1.0
            tt = max(0.0, (-dx * vx - dy * vy) / sp2)              # time of closest approach (frames)
            if tt > 40:
                continue
            cx, cy = b.x + vx * tt - pos.x, b.y + vy * tt - pos.y
            miss = math.hypot(cx, cy)
            if miss < 36 + b.r:
                w = (1.0 - miss / (36 + b.r)) * (1.0 - min(1.0, tt / 40)) * 2.0
                dist = math.sqrt(d2) or 1.0
                danger += Vector2(dx / dist + (-vy / math.sqrt(sp2)) * 0.6, dy / dist + (vx / math.sqrt(sp2)) * 0.6) * w
                urgent = max(urgent, w)
        for e in world.enemies:
            if not e.solid:
                continue
            d = pos - e.pos
            dist = d.length() or 1.0
            reach = 110 + (60 if e.kind == "comet" else 0)
            if dist < reach:
                danger += d / dist * (1.0 - dist / reach) * 2.2
                urgent = max(urgent, (1.0 - dist / reach) * 1.2)
        if world.boss is not None and not world.boss.dying:
            d = pos - world.boss.pos
            dist = d.length() or 1.0
            if dist < 190:
                danger += d / dist * (1.0 - dist / 190) * 2.0
        for h in world.hazards:
            name = h.__class__.__name__
            if name == "LaserGate" and h.state(world.time) != "off":
                from .hazards import dist_point_segment
                dd = dist_point_segment(pos, h.a, h.b)
                if dd < 90:
                    away = pos - Vector2(h.a + (h.b - h.a) * max(0, min(1, (pos - h.a).dot(h.b - h.a) / max(1, (h.b - h.a).length_squared()))))
                    if away.length_squared() > 0:
                        danger += away.normalize() * (1 - dd / 90) * 3.0
                        urgent = max(urgent, 0.8)
            elif name == "Blast" and h.boom == 0:
                d = pos - h.pos
                dist = d.length() or 1.0
                if dist < h.r + 60:
                    danger += d / dist * 2.5
                    urgent = max(urgent, 1.0)
            elif name == "Stripe":
                rect = h.rect.inflate(60, 60)
                if rect.collidepoint(pos.x, pos.y):
                    c = Vector2(h.rect.center)
                    away = Vector2(pos.x - c.x, 0) if h.vertical else Vector2(0, pos.y - c.y)
                    danger += (away.normalize() if away.length_squared() else Vector2(1, 0)) * 3.0
                    urgent = max(urgent, 1.0)
            elif name == "GravityWell":
                d = pos - h.pos
                dist = d.length() or 1.0
                if dist < 150:
                    danger += d / dist * (1 - dist / 150) * 2.5

        # goal: fragment > power > heart > coin > kite towards the middle
        goal = None
        best = 1e9
        for pk in world.pickups:
            weight = {"fragment": 0.0, "power": 120.0, "heart": 60.0, "coin": 260.0}.get(pk.kind, 300.0)
            d = pos.distance_to(pk.pos)
            if pk.kind == "coin" and d > 250:
                continue
            score = d + weight
            if score < best:
                best, goal = score, pk.pos
        move = Vector2()
        if goal is not None:
            d = goal - pos
            if d.length() > 4:
                move += d.normalize() * 0.9
        else:
            c = Vector2(W / 2, H * 0.55) - pos
            if c.length() > 200:
                move += c.normalize() * 0.5
            else:
                a = self.t * 0.02
                move += Vector2(math.cos(a), math.sin(a)) * 0.4
        move += danger * (1.6 * (0.4 + 0.6 * self.skill))
        # keep off the screen borders
        margin = 70
        if pos.x < margin:
            move.x += 0.7
        if pos.x > W - margin:
            move.x -= 0.7
        if pos.y < margin + 30:
            move.y += 0.7
        if pos.y > H - margin:
            move.y -= 0.7
        if move.length_squared() > 1:
            move = move.normalize()

        aim_target = world.nearest_target(pos)
        aim = Vector2(aim_target.pos) if aim_target is not None else None
        fire = aim_target is not None
        dash = False
        if self.dash_cd > 0:
            self.dash_cd -= 1
        if urgent > 1.15 and self.dash_cd <= 0 and p.dash_cd <= 0 and move.length_squared() > 0.1 and world.rng.random() < self.skill:
            dash = True
            self.dash_cd = 20
        pulse = p.energy >= 100 and (len(world.enemies) >= 5 or len(world.ebullets) > 25 or (world.boss is not None and not world.boss.dying))
        return PlayerInput(move=move, aim=aim if aim is not None else None, fire=fire, dash=dash, sprint=urgent > 0.6, pulse=pulse)
