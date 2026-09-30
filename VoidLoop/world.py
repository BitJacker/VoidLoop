"""The game simulation: one stage of play.

``World`` owns every entity of a stage and advances it one 60 Hz frame at a
time from abstract ``PlayerInput`` objects, so it can be driven by the keyboard,
by a bot in the test-suite, or by the menu's attract mode.
"""
import math
import random

import pygame
from pygame import Vector2

from . import gfx, biomes, hazards as hz
from .bosses import make_boss
from .enemies import make_enemy
from .entities import Bullet, Player, Pickup, PlayerInput, IFRAMES_ON_HIT
from .fx import FX
from .settings import W, H, P2_COLOR
from .weapons import WEAPONS, TIME_ATTACK_TIERS

EMPTY_INPUT = PlayerInput()

POWERUPS = {
    "SHIELD": {"color": gfx.CYAN, "frames": 360, "icon": "shield"},
    "SPEED": {"color": (255, 240, 60), "frames": 300, "icon": "speed"},
    "DOUBLE_DAMAGE": {"color": gfx.RED, "frames": 360, "icon": "double"},
    "RAPID_FIRE": {"color": gfx.ORANGE, "frames": 360, "icon": "rapid"},
    "FREEZE": {"color": gfx.ICE, "frames": 240, "icon": "freeze"},
    "MAGNET": {"color": gfx.LIME, "frames": 480, "icon": "magnet"},
    "BOMB": {"color": (255, 190, 60), "frames": 0, "icon": "bomb"},
}
TIMED_POWERS = tuple(k for k, v in POWERUPS.items() if v["frames"])
POWER_WEIGHTS = {"SHIELD": 14, "SPEED": 14, "DOUBLE_DAMAGE": 14, "RAPID_FIRE": 14, "FREEZE": 10, "MAGNET": 10, "BOMB": 10}

PULSE_RADIUS = 270
COMBO_FRAMES = 120
PICKUP_MAGNET_RADIUS = 110


def make_walls(rng, count, avoid=()):
    """Mirrored blocks so arenas look designed rather than random."""
    walls = []
    tries = 0
    while len(walls) < count and tries < 160:
        tries += 1
        horizontal = rng.random() < 0.6
        w, h = (rng.randint(90, 210), rng.randint(20, 34)) if horizontal else (rng.randint(20, 34), rng.randint(90, 190))
        x = rng.randint(110, W // 2 - 30 - w) if W // 2 - 30 - w > 110 else 110
        y = rng.randint(110, H - 130 - h)
        rects = [pygame.Rect(x, y, w, h)]
        if rng.random() < 0.85:
            rects.append(pygame.Rect(W - x - w, y, w, h))
        if any(r.inflate(70, 70).colliderect(o) for r in rects for o in walls):
            continue
        if any(r.inflate(60, 60).collidepoint(a) for r in rects for a in avoid):
            continue
        walls.extend(rects)
    return walls[:max(count, 0) + 1]


class World:
    def __init__(self, spec, cfg, loadout, colors, seed=None, players=1):
        from .rules import make_rules
        self.spec = spec
        self.cfg = cfg
        self.loadout = loadout
        self.rng = random.Random(seed)
        self.time = 0
        self.level = spec.level
        self.fx = FX()
        self.events = []
        self.state = "playing"            # playing | won | failed
        self.end_timer = 0
        self.hitstop = 0
        self.slowmo = 0
        self.enemy_slow = 1.0
        self.powers = {}

        self.walls = []
        self.hazards = []
        self.enemies = []
        self.pbullets = []
        self.ebullets = []
        self.pickups = []
        self.boss = None
        self.bg = None
        self._canvas = None
        self._wall_cache = {}

        # statistics
        self.score = 0
        self.kills = 0
        self.combo = 0
        self.combo_timer = 0
        self.best_combo = 0
        self.coins_earned = 0
        self.fragments = 0
        self.grazes = 0
        self.hits_taken = 0
        self.dashes = 0
        self.first_kill_done = False
        self.max_pulse_kills = 0
        self.shots_fired = 0
        self.hurt_causes = {}

        self.enemies_shoot = spec.shooting
        self.sector = spec.sector
        self.biome = biomes.BIOMES[spec.sector % len(biomes.BIOMES)]
        self.ice = self.biome.ice

        # players
        start = hz.PLAYER_START
        n = 2 if players == 2 else 1
        max_hp = cfg["hp"] + loadout.hp_bonus
        self.players = []
        for i in range(n):
            x = start[0] + (-46 if n == 2 and i == 0 else 46 if n == 2 else 0)
            p = Player(i + 1, x, start[1], colors[i] if i < len(colors) else P2_COLOR, max_hp)
            p.energy = 30.0
            self.players.append(p)
        if loadout.shield_cell:
            self.powers["SHIELD"] = 240

        self.load_sector(spec.sector, first=True)
        self.rules = make_rules(self)
        self.rules.start()

    # ---------------------------------------------------------------- events
    def emit(self, name, arg=None):
        if len(self.events) < 400:
            self.events.append((name, arg))

    def pop_events(self):
        ev, self.events = self.events, []
        return ev

    # ------------------------------------------------------------- sectors
    def load_sector(self, sector, first=False):
        self.sector = sector % len(biomes.BIOMES)
        self.biome = biomes.BIOMES[self.sector]
        self.ice = self.biome.ice
        self.bg = None
        self._wall_cache.clear()
        self.hazards = []
        self.walls = []
        spec = self.spec
        avoid = [hz.PLAYER_START, (W // 2, H // 2)]
        if spec.walls:
            self.walls = make_walls(random.Random(self.rng.random() if not first else spec.index * 7919 + spec.sector), spec.walls, avoid)
        if spec.hazards and self.biome.hazard:
            self.hazards = hz.make_hazards(self.biome, self.rng, spec.intensity, self.level)
        if not first:
            self.ebullets.clear()
            self.emit("sector", self.sector)
        # keep players out of walls
        for p in self.players:
            for w in self.walls:
                if w.inflate(30, 30).collidepoint(p.pos.x, p.pos.y):
                    p.pos.y = min(H - 40, w.bottom + 40)

    def add_hazard(self, h):
        self.hazards.append(h)

    # ---------------------------------------------------------------- queries
    def alive_players(self):
        return [p for p in self.players if p.alive]

    def nearest_player(self, pos):
        best, best_d = None, 1e18
        for p in self.players:
            if p.alive:
                d = (p.pos.x - pos.x) ** 2 + (p.pos.y - pos.y) ** 2
                if d < best_d:
                    best, best_d = p, d
        return best

    def nearest_target(self, pos):
        """Nearest enemy (or boss) for auto-aim."""
        best, best_d = None, 1e18
        for e in self.enemies:
            if e.solid:
                d = (e.pos.x - pos.x) ** 2 + (e.pos.y - pos.y) ** 2
                if d < best_d:
                    best, best_d = e, d
        if self.boss and not self.boss.dying:
            d = (self.boss.pos.x - pos.x) ** 2 + (self.boss.pos.y - pos.y) ** 2
            if d < best_d:
                best = self.boss
        return best

    def has_power(self, name):
        return name in self.powers

    def give_power(self, name):
        if name == "BOMB":
            p = self.alive_players()[0] if self.alive_players() else None
            if p:
                self.pulse_effect(p.pos, 300, gfx.GOLD, damage=5, cancel=True)
            return
        self.powers[name] = POWERUPS[name]["frames"]

    def forces_at(self, pos, r):
        total = None
        for h in self.hazards:
            f = h.force_at(pos, r)
            if f is not None:
                total = f if total is None else total + f
        return total if total is not None else Vector2()

    def free_point(self, margin=90, tries=40, avoid_players=0):
        for _ in range(tries):
            x = self.rng.randint(margin, W - margin)
            y = self.rng.randint(margin + 20, H - margin)
            pt = Vector2(x, y)
            if any(w.inflate(50, 50).collidepoint(x, y) for w in self.walls):
                continue
            if avoid_players and any(p.pos.distance_to(pt) < avoid_players for p in self.players if p.alive):
                continue
            return pt
        return Vector2(W / 2, H / 2)

    # ------------------------------------------------------------ spawning
    def spawn_position(self, min_dist=280):
        for _ in range(30):
            edge = self.rng.randint(0, 3)
            m = 46
            if edge == 0:
                x, y = self.rng.randint(m, W - m), m
            elif edge == 1:
                x, y = self.rng.randint(m, W - m), H - m
            elif edge == 2:
                x, y = m, self.rng.randint(m, H - m)
            else:
                x, y = W - m, self.rng.randint(m, H - m)
            if any(p.alive and p.pos.distance_to((x, y)) < min_dist for p in self.players):
                continue
            if any(w.inflate(40, 40).collidepoint(x, y) for w in self.walls):
                continue
            return x, y
        return self.rng.randint(60, W - 60), 60

    def spawn_enemy(self, kind, pos=None, level=None, elite=False, mini=False, instant=False):
        if len(self.enemies) >= 40:
            return None
        x, y = pos if pos is not None else self.spawn_position()
        e = make_enemy(self, kind, x, y, level or self.level, elite, mini)
        if instant:
            e.spawn = 0
        self.enemies.append(e)
        return e

    def enemy_bullet(self, x, y, angle, speed, r=5, color=None, kind="orb", **kw):
        if len(self.ebullets) > 700:
            return None
        s = speed * self.cfg["bullet"]
        b = Bullet(x, y, math.cos(angle) * s, math.sin(angle) * s, r=r, color=color or gfx.RED, friendly=False, kind=kind, **kw)
        self.ebullets.append(b)
        return b

    def spawn_pickup(self, kind, x, y, power=None, value=1, life=None):
        pk = Pickup(kind, x, y, power, value, life)
        self.pickups.append(pk)
        return pk

    def spawn_fragment(self):
        pt = self.free_point(110, avoid_players=180)
        return self.spawn_pickup("fragment", pt.x, pt.y)

    def random_power(self):
        names = list(POWER_WEIGHTS)
        return self.rng.choices(names, weights=[POWER_WEIGHTS[n] for n in names])[0]

    # ------------------------------------------------------------- scoring
    def add_score(self, points, pos=None, color=gfx.WHITE, popup=True):
        mult = 1 + min(self.combo, 40) * 0.05
        pts = int(points * mult * self.cfg["score"])
        self.score += pts
        if pos is not None and popup:
            self.fx.text(pos[0], pos[1] - 12, "+%d" % pts, color, 15)
        return pts

    def add_combo(self, n=1):
        self.combo += n
        self.combo_timer = COMBO_FRAMES
        if self.combo > self.best_combo:
            self.best_combo = self.combo
        if self.combo >= 5 and self.combo % 5 == 0:
            self.add_coins(self.combo // 5)
            self.emit("sfx", "combo")
        if self.combo in (10, 25, 50):
            self.emit("bark", "combo")

    def add_coins(self, n):
        self.loadout.coins += n
        self.coins_earned += n

    def add_energy(self, amount):
        for p in self.players:
            if p.alive:
                was = p.energy
                p.energy = min(100.0, p.energy + amount)
                if was < 100 <= p.energy:
                    self.emit("sfx", "ready")

    # ------------------------------------------------------ damage & death
    def damage_enemy(self, e, dmg, source=None, knock=0.0, by_player=True):
        if not e.solid or e.hp <= 0:
            return False
        died = e.hit(dmg)
        if source is not None and knock:
            d = e.pos - Vector2(source)
            if d.length_squared() > 0:
                e.knock += d.normalize() * knock
        if died:
            self.kill_enemy(e, by_player)
            return True
        self.emit("sfx", "hit")
        self.fx.burst(e.pos.x, e.pos.y, gfx.WHITE, 3, 3, 2)
        return False

    def kill_enemy(self, e, by_player=True):
        if e in self.enemies:
            self.enemies.remove(e)
        self.kills += 1
        self.fx.explosion(e.pos.x, e.pos.y, e.color, 1.0 + (0.4 if e.elite else 0.0))
        self.emit("sfx", "explode")
        if e.kind in ("bulwark",) or e.elite:
            self.hitstop = max(self.hitstop, 3)
            self.fx.add_shake(4)
        if by_player:
            self.add_combo()
            self.add_score(e.score, e.pos.xy, gfx.mix_white(e.color, 0.4))
            self.add_energy(12 if e.elite else 6)
            self.drop_loot(e)
            if not self.first_kill_done:
                self.first_kill_done = True
                self.emit("bark", "first_kill")
        e.on_death(self)
        self.rules.on_kill(e)
        self.emit("kill", e.kind)

    def drop_loot(self, e):
        drops = self.cfg["drops"]
        lo, hi = e.coins
        if e.elite:
            lo, hi = lo + 2, hi + 4
        n = self.rng.randint(lo, hi) if self.rng.random() < min(1.0, 0.55 * drops + (0.4 if hi > 1 else 0)) else 0
        for _ in range(n):
            a = self.rng.random() * math.tau
            pk = self.spawn_pickup("coin", e.pos.x + math.cos(a) * 10, e.pos.y + math.sin(a) * 10, life=520)
            pk.vel = Vector2(math.cos(a), math.sin(a)) * self.rng.uniform(1.5, 3.5)
        chance = (0.05 if not e.elite else 0.30) * drops
        if self.rng.random() < chance and len([p for p in self.pickups if p.kind == "power"]) < 2:
            self.spawn_pickup("power", e.pos.x, e.pos.y, self.random_power(), life=900)
        hurt = any(p.alive and p.hp < p.max_hp for p in self.players)
        down = any(not p.alive for p in self.players)
        heart_chance = (0.03 if not e.elite else 0.22) * drops * (2.5 if down else 1.0)
        if (hurt or down) and self.rng.random() < heart_chance:
            self.spawn_pickup("heart", e.pos.x, e.pos.y, life=900)

    def hurt_player(self, p, dmg=1, src=None, cause="hit"):
        """Try to hurt a player. Returns True when damage was actually dealt."""
        if not p.vulnerable():
            return False
        if "SHIELD" in self.powers:
            self.fx.ring(p.pos.x, p.pos.y, gfx.CYAN, 14, 44, 14, 3)
            self.fx.burst(p.pos.x, p.pos.y, gfx.CYAN, 8, 4)
            p.iframes = 12
            self.emit("sfx", "shield")
            return False
        p.hp -= dmg
        self.hurt_causes[cause] = self.hurt_causes.get(cause, 0) + 1
        p.iframes = IFRAMES_ON_HIT if self.cfg["hp"] > 1 else 60
        p.flash = 14
        p.hit_taken += 1
        self.hits_taken += 1
        self.combo = 0
        self.combo_timer = 0
        self.hitstop = max(self.hitstop, 5)
        self.fx.add_shake(9)
        self.fx.add_flash(gfx.RED, 0.5)
        self.fx.explosion(p.pos.x, p.pos.y, gfx.RED, 1.0)
        self.emit("sfx", "hurt")
        if src is not None:
            d = p.pos - Vector2(src)
            if d.length_squared() > 0:
                p.vel = d.normalize() * 7
        if p.hp <= 0:
            p.alive = False
            self.fx.explosion(p.pos.x, p.pos.y, p.color, 2.4)
            self.fx.add_shake(14)
            self.emit("sfx", "down")
            self.emit("player_down", p.id)
        elif p.hp == 1:
            self.emit("bark", "low_hp")
        return True

    def blast(self, x, y, radius, color, dmg_enemies=2, dmg_players=0, boss_dmg=0):
        """An explosion that can chain into other enemies."""
        self.fx.ring(x, y, color, 8, radius, 18, 4)
        self.fx.burst(x, y, color, 16, 6, 3)
        self.emit("sfx", "blast")
        c = Vector2(x, y)
        for e in self.enemies[:]:
            if e.solid and e.pos.distance_to(c) < radius + e.r:
                self.damage_enemy(e, dmg_enemies, c, 6.0)
        if boss_dmg and self.boss and not self.boss.dying and self.boss.pos.distance_to(c) < radius + self.boss.r:
            self.damage_boss(boss_dmg)
        if dmg_players:
            for p in self.alive_players():
                if p.pos.distance_to(c) < radius + p.r:
                    self.hurt_player(p, dmg_players, c, "blast")

    # ----------------------------------------------------------- abilities
    def on_dash(self, p):
        self.dashes += 1
        self.emit("sfx", "dash")
        self.fx.burst(p.pos.x, p.pos.y, p.color, 14, 5, 3)

    def player_fire(self, p, inp):
        if p.fire_cd > 0 or not p.alive:
            return
        if self.spec.mode == "HORDE":
            self.mace_swing(p, inp)
            return
        if not self.loadout.can_shoot:
            return
        if inp.aim is None:                       # auto-aim (keyboard-only play / player 2)
            t = self.nearest_target(p.pos)
            if t is not None:
                d = t.pos - p.pos
                p.aim = math.atan2(d.y, d.x)
        wid = self.loadout.weapon
        if self.spec.mode == "TIME_ATTACK":
            wid = TIME_ATTACK_TIERS[min(self.rules.tier, len(TIME_ATTACK_TIERS) - 1)]
        weapon = WEAPONS[wid]
        cd = self.loadout.fire_cooldown(wid)
        if "RAPID_FIRE" in self.powers:
            cd = max(3, int(cd * 0.4))
        p.fire_cd = cd
        dmg = weapon["dmg"] * (2 if "DOUBLE_DAMAGE" in self.powers else 1)
        color = gfx.mix_white(p.color, 0.25)
        dirx, diry = math.cos(p.aim), math.sin(p.aim)
        for dang, lateral in weapon["shots"]:
            a = p.aim + dang
            ox = p.pos.x + dirx * 14 - diry * lateral
            oy = p.pos.y + diry * 14 + dirx * lateral
            sp = weapon["speed"]
            b = Bullet(ox, oy, math.cos(a) * sp, math.sin(a) * sp, r=weapon["size"], dmg=dmg, color=color, friendly=True, life=70,
                       pierce=weapon["pierce"], kind="player", owner=p.id)
            self.pbullets.append(b)
        self.shots_fired += 1
        self.emit("sfx", "shoot" if len(weapon["shots"]) == 1 else "shoot2")
        self.fx.burst(p.pos.x + dirx * 16, p.pos.y + diry * 16, color, 2, 2.5, 2, life=(6, 12))
        p.vel -= Vector2(dirx, diry) * 0.25

    def mace_swing(self, p, inp):
        """Horde mode: a wide plasma-mace arc that also reflects bullets."""
        if p.swing is not None:
            return
        if inp.aim is None:
            t = self.nearest_target(p.pos)
            if t is not None:
                d = t.pos - p.pos
                p.aim = math.atan2(d.y, d.x)
        p.swing = {"t": 0, "angle": p.aim, "hit": set()}
        p.fire_cd = 26
        self.emit("sfx", "swing")

    def update_mace(self, p):
        s = p.swing
        if s is None:
            return
        s["t"] += 1
        dur = 14
        prog = s["t"] / dur
        blade = s["angle"] - 1.35 + 2.7 * prog
        reach = 84
        tip = Vector2(math.cos(blade), math.sin(blade)) * reach + p.pos
        dmg = 3 * (2 if "DOUBLE_DAMAGE" in self.powers else 1)
        for e in self.enemies[:]:
            if not e.solid or e.id in s["hit"]:
                continue
            d = e.pos - p.pos
            dist = d.length()
            if dist < reach + e.r and dist > 0:
                ang = math.atan2(d.y, d.x)
                diff = abs((ang - blade + math.pi) % math.tau - math.pi)
                if diff < 0.55:
                    s["hit"].add(e.id)
                    self.damage_enemy(e, dmg, p.pos, 12.0)
                    self.fx.burst(e.pos.x, e.pos.y, gfx.WHITE, 8, 5, 3)
                    self.emit("sfx", "smash")
        if self.boss and not self.boss.dying and "boss" not in s["hit"]:
            if self.boss.pos.distance_to(tip) < self.boss.r + 20:
                s["hit"].add("boss")
                self.damage_boss(dmg * 2)
        for b in self.ebullets[:]:
            if math.hypot(b.x - p.pos.x, b.y - p.pos.y) < reach + b.r:
                ang = math.atan2(b.y - p.pos.y, b.x - p.pos.x)
                if abs((ang - blade + math.pi) % math.tau - math.pi) < 0.7:
                    self.ebullets.remove(b)
                    self.fx.burst(b.x, b.y, gfx.WHITE, 4, 3, 2)
                    self.add_energy(1.5)
                    self.add_score(5, None, popup=False)
        if s["t"] >= dur:
            p.swing = None

    def use_pulse(self, p):
        if not p.alive or p.energy < 100:
            return
        p.energy = 0
        p.iframes = max(p.iframes, 45)
        self.emit("sfx", "pulse")
        self.fx.add_shake(10)
        self.fx.add_flash(p.color, 0.6)
        self.pulse_effect(p.pos, PULSE_RADIUS, p.color, damage=4, cancel=True)

    def pulse_effect(self, pos, radius, color, damage=4, cancel=True):
        c = Vector2(pos)
        self.fx.ring(c.x, c.y, color, 10, radius, 24, 6)
        self.fx.ring(c.x, c.y, gfx.WHITE, 6, radius * 0.75, 18, 3)
        self.fx.burst(c.x, c.y, color, 30, 9, 3)
        killed = 0
        for e in self.enemies[:]:
            if e.solid and e.pos.distance_to(c) < radius + e.r:
                if self.damage_enemy(e, damage, c, 14.0):
                    killed += 1
        if killed > self.max_pulse_kills:
            self.max_pulse_kills = killed
        if self.boss and not self.boss.dying and self.boss.pos.distance_to(c) < radius + self.boss.r:
            self.damage_boss(damage * 2)
        if cancel:
            n = 0
            for b in self.ebullets[:]:
                if math.hypot(b.x - c.x, b.y - c.y) < radius:
                    self.ebullets.remove(b)
                    n += 1
                    if n % 3 == 0:
                        self.fx.burst(b.x, b.y, color, 2, 2, 2, life=(8, 14))
                        pk = self.spawn_pickup("coin", b.x, b.y, life=300)
                        pk.vel = Vector2()
            self.add_score(n * 4, None, popup=False)

    # ----------------------------------------------------------------- boss
    def spawn_boss(self, boss_id, hp_scale=1.0):
        self.boss = make_boss(self, boss_id, hp_scale)
        self.emit("boss_spawn", boss_id)
        return self.boss

    def damage_boss(self, dmg):
        b = self.boss
        if b is None or b.dying or b.invuln:
            return False
        b.hp -= dmg
        b.flash = 4
        self.add_energy(0.15 * dmg)
        self.add_score(4 * dmg, None, popup=False)
        if b.hp <= 0:
            b.start_dying(self)
            self.slowmo = 70
            self.fx.add_flash(gfx.WHITE, 0.9)
            self.emit("sfx", "boss_down")
        return True

    # -------------------------------------------------------------- updating
    def update(self, inputs):
        if self.state != "playing":
            self.fx.update()
            return
        if self.hitstop > 0:
            self.hitstop -= 1
            self.fx.update()
            return
        if self.slowmo > 0:
            self.slowmo -= 1
            if self.slowmo % 2:
                self.fx.update()
                return
        self.time += 1
        if self.bg is not None:
            self.bg.update()
        for k in list(self.powers):
            self.powers[k] -= 1
            if self.powers[k] <= 0:
                del self.powers[k]
        self.enemy_slow = 0.35 if "FREEZE" in self.powers else 1.0
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        for p in self.players:
            p.update(self, inputs.get(p.id, EMPTY_INPUT))
            if p.swing is not None:
                self.update_mace(p)

        self.rules.update()

        for h in self.hazards[:]:
            h.update(self)
            if h.done:
                self.hazards.remove(h)
        for e in self.enemies[:]:
            e.update(self)
        self.separate_enemies()
        if self.boss is not None:
            self.boss.update(self)
            if self.boss.gone:
                dead, self.boss = self.boss, None
                self.ebullets.clear()
                self.rules.on_boss_dead(dead)
        self.update_bullets()
        self.update_contacts()
        self.update_pickups()
        self.fx.update()

        if self.state == "playing" and not self.alive_players():
            self.end_timer += 1
            if self.end_timer > 80:
                self.state = "failed"
        elif self.state == "playing":
            self.end_timer = 0

    def separate_enemies(self):
        es = [e for e in self.enemies if e.solid]
        for i in range(len(es)):
            a = es[i]
            for j in range(i + 1, len(es)):
                b = es[j]
                dx, dy = b.pos.x - a.pos.x, b.pos.y - a.pos.y
                min_d = (a.r + b.r) * 0.85
                d2 = dx * dx + dy * dy
                if 0 < d2 < min_d * min_d:
                    d = math.sqrt(d2)
                    push = (min_d - d) * 0.25 / d
                    a.pos.x -= dx * push
                    a.pos.y -= dy * push
                    b.pos.x += dx * push
                    b.pos.y += dy * push

    def update_bullets(self):
        wells = [h for h in self.hazards if isinstance(h, hz.GravityWell)]
        walls = self.walls
        # --- player bullets
        for b in self.pbullets[:]:
            for wl in wells:
                wl.pull_bullet(b)
            if not b.update(walls):
                self.pbullets.remove(b)
                continue
            consumed = False
            for e in self.enemies[:]:
                if not e.solid:
                    continue
                rr = e.r + b.r
                if (e.pos.x - b.x) ** 2 + (e.pos.y - b.y) ** 2 < rr * rr:
                    if b.hit is not None and e.id in b.hit:
                        continue
                    self.damage_enemy(e, b.dmg, (b.px, b.py), 2.5)
                    if b.pierce > 0:
                        b.pierce -= 1
                        if b.hit is None:
                            b.hit = set()
                        b.hit.add(e.id)
                    else:
                        consumed = True
                        break
            if not consumed and self.boss is not None and not self.boss.dying:
                if self.boss.collide_circle(b.x, b.y, b.r) and not (b.hit and "boss" in b.hit):
                    if not self.boss.invuln:
                        self.damage_boss(b.dmg)
                        self.fx.burst(b.x, b.y, gfx.PINK, 4, 4, 2)
                        self.emit("sfx", "hit")
                    else:
                        self.fx.burst(b.x, b.y, gfx.WHITE, 3, 3, 2)
                        self.emit("sfx", "shield")
                    if b.pierce > 0:
                        b.pierce -= 1
                        b.hit = (b.hit or set()) | {"boss"}
                    else:
                        consumed = True
            if consumed and b in self.pbullets:
                self.pbullets.remove(b)
        # --- enemy bullets
        slow = self.enemy_slow
        players = self.alive_players()
        for b in self.ebullets[:]:
            for wl in wells:
                wl.pull_bullet(b)
            if not b.update(walls, slow):
                self.ebullets.remove(b)
                continue
            for p in players:
                dx, dy = p.pos.x - b.x, p.pos.y - b.y
                d2 = dx * dx + dy * dy
                hit_r = p.r + b.r
                if d2 < hit_r * hit_r:
                    if p.vulnerable():
                        self.hurt_player(p, 1, (b.px, b.py), "bullet")
                        self.ebullets.remove(b)
                        break
                elif not b.grazed and d2 < (hit_r + 14) ** 2 and p.vulnerable():
                    b.grazed = True
                    self.grazes += 1
                    self.add_energy(0.8)
                    self.add_score(5, None, popup=False)
                    self.fx.burst(b.x, b.y, gfx.WHITE, 2, 2.5, 2, life=(6, 10))
                    if self.grazes % 12 == 0:
                        self.emit("sfx", "graze")

    def update_contacts(self):
        players = self.alive_players()
        for e in self.enemies[:]:
            if not e.solid:
                continue
            for p in players:
                rr = e.r + p.r - 2
                dx, dy = p.pos.x - e.pos.x, p.pos.y - e.pos.y
                if dx * dx + dy * dy < rr * rr and p.vulnerable():
                    if "SHIELD" in self.powers:
                        self.fx.ring(p.pos.x, p.pos.y, gfx.CYAN, 14, 50, 14, 3)
                        self.kill_enemy(e)
                        break
                    if self.hurt_player(p, 1, e.pos, "contact"):
                        e.knock += (e.pos - p.pos).normalize() * 8 if (e.pos - p.pos).length_squared() > 0 else Vector2()
                        if e.kind == "comet":
                            self.kill_enemy(e, by_player=False)
                            break
        if self.boss is not None and not self.boss.dying:
            for p in players:
                if p.vulnerable() and self.boss.collide_circle(p.pos.x, p.pos.y, p.r - 6):
                    self.hurt_player(p, 1, self.boss.pos, "boss")

    def update_pickups(self):
        magnet_r = 340 if "MAGNET" in self.powers else PICKUP_MAGNET_RADIUS
        players = self.alive_players()
        for pk in self.pickups[:]:
            pk.t += 1
            if pk.life is not None:
                pk.life -= 1
                if pk.life <= 0:
                    self.pickups.remove(pk)
                    continue
            if pk.kind != "fragment" or "MAGNET" in self.powers:
                pk.pos += pk.vel
                pk.vel *= 0.92
            if players and pk.kind in ("coin", "power", "heart", "fragment"):
                near = min(players, key=lambda p: p.pos.distance_squared_to(pk.pos))
                d = near.pos - pk.pos
                dist = d.length()
                if dist < magnet_r and (pk.kind == "coin" or "MAGNET" in self.powers) and dist > 1:
                    pk.pos += d / dist * min(dist, 3.0 + (magnet_r - dist) * 0.06 + (4 if pk.kind == "coin" else 0))
            for p in players:
                if p.pos.distance_to(pk.pos) < p.r + pk.r + 4:
                    self.collect(p, pk)
                    if pk in self.pickups:
                        self.pickups.remove(pk)
                    break

    def collect(self, p, pk):
        c = pk.pos
        if pk.kind == "fragment":
            self.fragments += 1
            self.add_coins(1)
            self.add_combo()
            self.add_score(150, c.xy, gfx.GOLD)
            self.add_energy(8)
            self.fx.burst(c.x, c.y, gfx.GOLD, 18, 5, 3)
            self.fx.ring(c.x, c.y, gfx.GOLD, 8, 46, 16, 3)
            self.emit("sfx", "fragment")
            self.rules.on_fragment()
        elif pk.kind == "coin":
            self.add_coins(pk.value)
            self.add_energy(0.6)
            self.add_score(10, None, popup=False)
            self.fx.burst(c.x, c.y, gfx.GOLD, 4, 3, 2, life=(8, 14))
            self.emit("sfx", "coin")
        elif pk.kind == "heart":
            revived = [q for q in self.players if not q.alive]
            for q in revived:
                q.revive(1, 150)
                q.pos = Vector2(p.pos) + Vector2(30, 0)
                self.fx.explosion(q.pos.x, q.pos.y, gfx.GREEN, 1.6)
            for q in self.alive_players():
                q.heal(1)
            self.fx.ring(c.x, c.y, gfx.RED, 10, 60, 18, 3)
            self.fx.text(c.x, c.y - 14, "+HP", gfx.RED, 16)
            self.emit("sfx", "heal")
        else:
            name = pk.power
            self.give_power(name)
            pu = POWERUPS[name]
            self.fx.burst(c.x, c.y, pu["color"], 20, 5, 3)
            self.fx.ring(c.x, c.y, pu["color"], 8, 60, 18, 3)
            self.fx.text(c.x, c.y - 16, name.replace("_", " "), pu["color"], 14)
            self.emit("sfx", "powerup")
            self.emit("power", name)

    # -------------------------------------------------------------- drawing
    def canvas(self):
        if self._canvas is None:
            self._canvas = pygame.Surface((W, H)).convert()
        return self._canvas

    def draw(self, surf, shake=True):
        if self.bg is None:
            self.bg = biomes.make_background(self.sector)
        ox, oy = self.fx.shake_offset(shake)
        target = self.canvas() if (ox or oy) else surf
        t = self.time
        self.bg.draw(target)
        self.draw_frame(target)
        for h in self.hazards:
            h.draw_floor(target, t)
        for w in self.walls:
            self.draw_wall(target, w)
        for pk in self.pickups:
            self.draw_pickup(target, pk, t)
        for e in self.enemies:
            e.draw(target, t)
        if self.boss is not None:
            self.boss.draw(target, t)
        for h in self.hazards:
            h.draw(target, t)
        for b in self.pbullets:
            self.draw_bullet(target, b)
        for b in self.ebullets:
            self.draw_bullet(target, b)
        for p in self.players:
            self.draw_player(target, p, t)
        self.fx.draw(target)
        self.bg.post(target)
        if target is not surf:
            surf.fill((0, 0, 0))
            surf.blit(target, (ox, oy))
        if self.fx.flash > 0:
            surf.blit(gfx.tint_overlay(self.fx.flash_color, self.fx.flash * 120), (0, 0))
        if "FREEZE" in self.powers:
            k = min(1.0, self.powers["FREEZE"] / 40)
            surf.blit(gfx.tint_overlay((120, 200, 255), 26 * k), (0, 0))

    def draw_frame(self, surf):
        c = gfx.scale_color(self.biome.main, 0.55)
        L = 36
        for (x, y, sx, sy) in ((6, 6, 1, 1), (W - 6, 6, -1, 1), (6, H - 6, 1, -1), (W - 6, H - 6, -1, -1)):
            pygame.draw.lines(surf, c, False, [(x + sx * L, y), (x, y), (x, y + sy * L)], 2)

    def draw_wall(self, surf, w):
        key = (w.w, w.h)
        spr = self._wall_cache.get(key)
        if spr is None:
            spr = pygame.Surface((w.w, w.h)).convert()
            spr.fill(self.biome.wall_fill)
            line = gfx.scale_color(self.biome.main, 0.22)
            for i in range(-w.h, w.w, 12):
                pygame.draw.line(spr, line, (i, w.h), (i + w.h, 0), 1)
            pygame.draw.rect(spr, self.biome.main, spr.get_rect(), 2)
            for cx, cy in ((0, 0), (w.w - 1, 0), (0, w.h - 1), (w.w - 1, w.h - 1)):
                pygame.draw.rect(spr, gfx.WHITE, (min(max(cx - 2, 0), w.w - 5), min(max(cy - 2, 0), w.h - 5), 5, 5))
            self._wall_cache[key] = spr
        gfx.draw_glow(surf, w.center, max(w.w, w.h) // 2 + 26, self.biome.main, 0.14)
        surf.blit(spr, w.topleft)

    def draw_bullet(self, surf, b):
        x, y = b.x, b.y
        if b.friendly:
            pygame.draw.line(surf, gfx.scale_color(b.color, 0.5), (b.px, b.py), (x - b.vx * 0.9, y - b.vy * 0.9), max(1, int(b.r)))
            pygame.draw.line(surf, b.color, (x - b.vx * 0.9, y - b.vy * 0.9), (x, y), max(2, int(b.r * 1.3)))
            pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), max(1, int(b.r * 0.5)))
            gfx.draw_glow(surf, (x, y), int(b.r * 3.5), b.color, 0.6)
        elif b.kind == "shard":
            ang = math.atan2(b.vy, b.vx)
            tip = (x + math.cos(ang) * 9, y + math.sin(ang) * 9)
            tail = (x - math.cos(ang) * 9, y - math.sin(ang) * 9)
            pygame.draw.line(surf, gfx.scale_color(b.color, 0.5), tail, tip, 5)
            pygame.draw.line(surf, gfx.WHITE, tail, tip, 2)
            gfx.draw_glow(surf, (x, y), 14, b.color, 0.7)
        else:
            gfx.draw_glow(surf, (x, y), int(b.r * 3.2), b.color, 0.5)
            pygame.draw.circle(surf, (8, 2, 12), (int(x), int(y)), int(b.r + 3))          # dark outline keeps bullets readable
            pygame.draw.circle(surf, b.color, (int(x), int(y)), int(b.r + 1))
            pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), max(2, int(b.r * 0.55)))

    def draw_pickup(self, surf, pk, t):
        x, y = pk.pos.x, pk.pos.y + math.sin((t + pk.t) * 0.08) * 2
        if pk.life is not None and pk.life < 90 and int(pk.life / 5) % 2 == 0:
            return
        if pk.kind == "fragment":
            spin = (t + pk.t) * 0.05
            w = abs(math.cos(spin))
            pts = [(x, y - 15), (x + 11 * (0.35 + 0.65 * w), y), (x, y + 15), (x - 11 * (0.35 + 0.65 * w), y)]
            gfx.draw_glow(surf, (x, y), 34 + int(6 * math.sin(t * 0.1)), gfx.GOLD, 0.6)
            pygame.draw.polygon(surf, (255, 240, 170), pts)
            pygame.draw.polygon(surf, gfx.GOLD, pts, 2)
        elif pk.kind == "coin":
            w = max(2, int(abs(math.cos((t + pk.t) * 0.12)) * 7))
            gfx.draw_glow(surf, (x, y), 16, gfx.GOLD, 0.4)
            pygame.draw.ellipse(surf, gfx.GOLD, (x - w, y - 7, w * 2, 14))
            pygame.draw.ellipse(surf, (255, 245, 190), (x - w, y - 7, w * 2, 14), 1)
        elif pk.kind == "heart":
            gfx.draw_glow(surf, (x, y), 30, gfx.RED, 0.5)
            gfx.draw_heart(surf, x, y, 13 + math.sin(t * 0.15) * 1.5, gfx.RED)
        else:
            pu = POWERUPS[pk.power]
            gfx.draw_glow(surf, (x, y), 36, pu["color"], 0.55)
            rect = pygame.Rect(0, 0, 30, 30)
            rect.center = (int(x), int(y))
            pygame.draw.rect(surf, gfx.scale_color(pu["color"], 0.25), rect)
            pygame.draw.rect(surf, pu["color"], rect, 2)
            gfx.draw_icon(surf, pu["icon"], x, y, 9, gfx.WHITE)

    def draw_player(self, surf, p, t):
        x, y = p.pos.x, p.pos.y
        if not p.alive:
            gfx.draw_icon(surf, "cross", x, y, 10, gfx.scale_color(p.color, 0.6))
            gfx.draw_text(surf, "P%d" % p.id, (x, y - 24), "mono", 14, p.color, "center")
            return
        for i, (tx, ty, ta) in enumerate(p.trail):
            k = (i + 1) / (len(p.trail) + 1)
            pts = gfx.ship_points(tx, ty, ta, 20)
            pygame.draw.polygon(surf, gfx.scale_color(p.color, 0.5 * k), pts, 2)
        blink = p.iframes > 0 and not p.dashing and int(p.iframes / 4) % 2 == 0
        if not blink:
            gfx.draw_glow(surf, (x, y), 46, p.color, 0.42)
            gfx.draw_ship(surf, x, y, p.aim, 20, p.color, p.thrust + (0.5 if p.sprinting else 0), t, flash=p.flash > 8)
            pygame.draw.circle(surf, gfx.WHITE, (int(x), int(y)), 3)          # the hitbox
        if "SHIELD" in self.powers:
            pulse = 1.0 + 0.06 * math.sin(t * 0.3)
            gfx.neon_circle(surf, (x, y), 30 * pulse, gfx.CYAN, 2)
            gfx.draw_glow(surf, (x, y), 54, gfx.CYAN, 0.25)
        if p.sprinting:
            pygame.draw.circle(surf, (255, 240, 60), (int(x), int(y)), 26, 1)
        # dash cooldown ring
        if p.dash_cd > 0:
            frac = 1 - p.dash_cd / max(1, self.loadout.dash_cooldown())
            rect = pygame.Rect(0, 0, 44, 44)
            rect.center = (int(x), int(y))
            pygame.draw.arc(surf, gfx.scale_color(p.color, 0.5), rect, -math.pi / 2, -math.pi / 2 + math.tau * frac, 2)
        # aim reticle
        if self.loadout.can_shoot or self.spec.mode == "HORDE":
            ax, ay = x + math.cos(p.aim) * 46, y + math.sin(p.aim) * 46
            pygame.draw.circle(surf, gfx.scale_color(p.color, 0.7), (int(ax), int(ay)), 3, 1)
        if p.swing is not None:
            self.draw_mace(surf, p)

    def draw_mace(self, surf, p):
        s = p.swing
        prog = s["t"] / 14
        blade = s["angle"] - 1.35 + 2.7 * prog
        reach = 84
        for i in range(8):                       # trailing arc
            a = blade - i * 0.09
            k = 1 - i / 8
            p0 = (p.pos.x + math.cos(a) * 24, p.pos.y + math.sin(a) * 24)
            p1 = (p.pos.x + math.cos(a) * reach, p.pos.y + math.sin(a) * reach)
            pygame.draw.line(surf, gfx.scale_color(p.color, 0.6 * k), p0, p1, max(1, int(7 * k)))
        tip = (p.pos.x + math.cos(blade) * reach, p.pos.y + math.sin(blade) * reach)
        gfx.neon_line(surf, p.pos, tip, gfx.WHITE, 4)
        gfx.draw_glow(surf, tip, 34, p.color, 0.9)
        pygame.draw.circle(surf, gfx.WHITE, (int(tip[0]), int(tip[1])), 9)
