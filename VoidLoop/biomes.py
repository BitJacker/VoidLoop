"""The six sectors ("biomes"): palettes and animated procedural backgrounds."""
import math
import random
from dataclasses import dataclass

import pygame

from . import gfx
from .settings import W, H


@dataclass(frozen=True)
class Biome:
    id: str
    main: tuple          # primary neon colour (walls, frame, HUD tint)
    accent: tuple
    bg_top: tuple
    bg_bottom: tuple
    wall_fill: tuple
    music: str
    hazard: str          # hazard family: "", "current", "laser", "ice", "portal", "gravity"
    ice: bool = False


BIOMES = (
    Biome("boot", (0, 255, 150), (0, 220, 255), (2, 12, 14), (1, 4, 8), (4, 30, 26), "s1", ""),
    Biome("stream", (0, 165, 255), (130, 255, 255), (1, 7, 22), (0, 2, 10), (4, 22, 48), "s2", "current"),
    Biome("firewall", (255, 95, 40), (255, 205, 70), (22, 4, 4), (7, 1, 2), (46, 12, 8), "s3", "laser"),
    Biome("frozen", (140, 230, 255), (255, 255, 255), (5, 18, 28), (2, 7, 14), (16, 46, 62), "s4", "ice", True),
    Biome("corrupt", (255, 65, 240), (70, 255, 200), (16, 2, 22), (5, 0, 10), (40, 8, 48), "s5", "portal"),
    Biome("void", (190, 140, 255), (255, 255, 255), (6, 4, 12), (0, 0, 3), (18, 10, 34), "s6", "gravity"),
)
BIOME_IDS = tuple(b.id for b in BIOMES)


class Background:
    """Base class. ``update()`` advances the animation, ``draw()`` renders it."""
    seed = 1

    def __init__(self, biome):
        self.biome = biome
        self.rng = random.Random(self.seed)
        self.t = 0
        self.base = self.build_base()

    def build_base(self):
        return gfx.gradient_surface((W, H), self.biome.bg_top, self.biome.bg_bottom)

    def update(self):
        self.t += 1

    def draw(self, surf):
        surf.blit(self.base, (0, 0))

    def post(self, surf):
        """Optional screen-space effect applied after everything else is drawn."""


class BootBG(Background):
    """Slowly scrolling neon grid with drifting data motes."""
    seed = 11
    CELL = 64

    def __init__(self, biome):
        super().__init__(biome)
        c, cell = biome.main, self.CELL
        grid = pygame.Surface((W + cell * 2, H + cell * 2)).convert()
        grid.fill((0, 0, 0))
        for i in range(0, W + cell * 2 + 1, cell):
            pygame.draw.line(grid, gfx.scale_color(c, 0.38 if (i // cell) % 4 == 0 else 0.16), (i, 0), (i, H + cell * 2))
        for j in range(0, H + cell * 2 + 1, cell):
            pygame.draw.line(grid, gfx.scale_color(c, 0.38 if (j // cell) % 4 == 0 else 0.16), (0, j), (W + cell * 2, j))
        for radius in (150, 290, 430):                       # radar rings, baked into the static layer
            pygame.draw.circle(self.base, gfx.scale_color(c, 0.22), (W // 2, H // 2), radius, 1)
        for a in range(0, 360, 15):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            pygame.draw.line(self.base, gfx.scale_color(c, 0.22), (W / 2 + ca * 290, H / 2 + sa * 290), (W / 2 + ca * 302, H / 2 + sa * 302), 1)
        self.grid = grid
        self.motes = [[self.rng.uniform(0, W), self.rng.uniform(0, H), self.rng.uniform(0.15, 0.9),
                       self.rng.choice((1, 1, 2, 3)), self.rng.random() * 6.28] for _ in range(80)]
        scan = pygame.Surface((W, 70)).convert()
        for y in range(70):
            k = 1 - abs(y - 35) / 35
            pygame.draw.line(scan, gfx.scale_color(c, 0.22 * k * k), (0, y), (W, y))
        self.scan = scan

    def update(self):
        super().update()
        for m in self.motes:
            m[1] -= m[2]
            if m[1] < -4:
                m[1], m[0] = H + 4, self.rng.uniform(0, W)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        cell = self.CELL
        surf.blit(self.grid, (-(int(self.t * 0.35) % cell), -(int(self.t * 0.2) % cell)), special_flags=pygame.BLEND_RGB_ADD)
        c = self.biome.main
        for x, y, sp, size, ph in self.motes:
            a = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self.t * 0.04 + ph))
            pygame.draw.circle(surf, gfx.scale_color(c, a * 0.9), (int(x), int(y)), size)
        sy = int((self.t * 2.2) % (H + 260)) - 130
        surf.blit(self.scan, (0, sy), special_flags=pygame.BLEND_RGB_ADD)
        sweep = self.t * 0.018
        for i in range(24):                                   # radar sweep with a fading wedge
            a0, a1 = sweep - i * 0.03, sweep - (i + 1) * 0.03
            pygame.draw.polygon(surf, gfx.scale_color(c, 0.30 * (1 - i / 24) ** 2),
                                [(W / 2, H / 2), (W / 2 + math.cos(a0) * 430, H / 2 + math.sin(a0) * 430),
                                 (W / 2 + math.cos(a1) * 430, H / 2 + math.sin(a1) * 430)])


class StreamBG(Background):
    """Falling columns of hex/binary glyphs."""
    seed = 22
    CH = 16
    CHARS = "01234567890ABCDEF<>/|+=:"

    def __init__(self, biome):
        super().__init__(biome)
        f = gfx.font("mono", 15)
        main, acc = biome.main, biome.accent
        levels = [gfx.WHITE, acc, gfx.scale_color(main, 0.85), gfx.scale_color(main, 0.5), gfx.scale_color(main, 0.26)]
        self.glyphs = [[f.render(ch, True, col).convert_alpha() for ch in self.CHARS] for col in levels]
        self.cols = []
        step = 20
        for i in range(W // step + 1):
            sp = self.rng.choice((1.4, 2.0, 2.8, 3.6, 4.6))
            self.cols.append([i * step + self.rng.randint(-3, 3), self.rng.uniform(-H, H), sp, self.rng.randint(6, 17), self.rng.randint(0, 999)])
        streaks = pygame.Surface((W, H)).convert()
        streaks.fill((0, 0, 0))
        for i in range(14):
            x = self.rng.randint(0, W)
            pygame.draw.line(streaks, gfx.scale_color(main, 0.028), (x, 0), (x, H), self.rng.randint(20, 90))
        self.base.blit(streaks, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def update(self):
        super().update()
        for c in self.cols:
            c[1] += c[2]
            if c[1] - c[3] * self.CH > H:
                c[1] = -self.rng.uniform(0, 200)
                c[2] = self.rng.choice((1.4, 2.0, 2.8, 3.6, 4.6))
                c[3] = self.rng.randint(6, 17)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        n = len(self.CHARS)
        ch = self.CH
        t6 = self.t // 6
        for x, head, sp, length, seed in self.cols:
            dim = 0.0 if sp > 2.5 else 1.0
            for k in range(length):
                y = head - k * ch
                if y < -ch or y > H:
                    continue
                level = 0 if k == 0 else 1 if k == 1 else 2 if k < 4 else 3 if k < 9 else 4
                if dim and level < 4:
                    level += 1
                idx = (seed + int(y // ch) * 13 + (t6 * (1 + k % 3) if k < 3 else 0)) % n
                surf.blit(self.glyphs[level][idx], (x, y))


class FirewallBG(Background):
    """Honeycomb firewall with flaring cells and rising embers."""
    seed = 33
    R = 38

    def __init__(self, biome):
        super().__init__(biome)
        self.hex_r = self.R
        w = self.hex_r * 1.5
        h = self.hex_r * math.sqrt(3)
        self.cells = []
        col = 0
        x = -self.hex_r
        while x < W + self.hex_r * 2:
            y = -h + (h / 2 if col % 2 else 0)
            while y < H + h:
                self.cells.append((x, y))
                y += h
            x += w
            col += 1
        line_col = gfx.scale_color(biome.main, 0.24)
        for cx, cy in self.cells:
            pygame.draw.polygon(self.base, line_col, gfx.poly_points(cx, cy, self.hex_r - 1, 6), 1)
        self.lit = []
        self.hex_sprites = []
        for level in range(1, 9):
            spr = pygame.Surface((int(self.hex_r * 2 + 2), int(h + 2))).convert()
            spr.fill((0, 0, 0))
            pygame.draw.polygon(spr, gfx.scale_color((255, 90, 30), 0.42 * level / 8), gfx.poly_points(self.hex_r + 1, h / 2 + 1, self.hex_r - 3, 6))
            self.hex_sprites.append(spr)
        self.embers = [[self.rng.uniform(0, W), self.rng.uniform(0, H), self.rng.uniform(0.5, 2.0), self.rng.random() * 6.28,
                        self.rng.choice((1, 2, 2, 3))] for _ in range(70)]
        self.heat = []
        for level in (0.5, 0.75, 1.0):
            s = pygame.Surface((W, 220)).convert()
            for y in range(220):
                k = (y / 219) ** 2
                pygame.draw.line(s, gfx.scale_color((255, 70, 20), 0.55 * k * level), (0, y), (W, y))
            self.heat.append(s)

    def update(self):
        super().update()
        if self.rng.random() < 0.22 and len(self.lit) < 22:
            self.lit.append([self.rng.choice(self.cells), 46])
        for c in self.lit[:]:
            c[1] -= 1
            if c[1] <= 0:
                self.lit.remove(c)
        for e in self.embers:
            e[1] -= e[2]
            e[0] += math.sin(self.t * 0.03 + e[3]) * 0.5
            if e[1] < -5:
                e[1], e[0] = H + 5, self.rng.uniform(0, W)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        for (cx, cy), life in self.lit:
            spr = self.hex_sprites[min(7, int(life / 46 * 8))]
            surf.blit(spr, (int(cx - self.hex_r - 1), int(cy - spr.get_height() / 2)), special_flags=pygame.BLEND_RGB_ADD)
        idx = int(1 + math.sin(self.t * 0.04) * 1.0)
        surf.blit(self.heat[max(0, min(2, idx))], (0, H - 220), special_flags=pygame.BLEND_RGB_ADD)
        for x, y, sp, ph, size in self.embers:
            a = 0.5 + 0.5 * math.sin(self.t * 0.09 + ph)
            col = gfx.lerp_color((255, 60, 20), (255, 210, 90), a)
            pygame.draw.circle(surf, col, (int(x), int(y)), size)
            if size >= 3:
                gfx.draw_glow(surf, (x, y), 10, (255, 100, 30), 0.6 * a)


class FrozenBG(Background):
    """Crystal cave with a slow aurora and falling snow."""
    seed = 44

    def __init__(self, biome):
        super().__init__(biome)
        rng = self.rng
        for _ in range(16):                              # big translucent crystals
            cx, cy = rng.randint(0, W), rng.randint(0, H)
            r = rng.randint(60, 200)
            pts = [(cx + math.cos(a) * r * rng.uniform(0.5, 1.0), cy + math.sin(a) * r * rng.uniform(0.5, 1.0))
                   for a in sorted(rng.uniform(0, math.tau) for _ in range(rng.randint(3, 5)))]
            pygame.draw.polygon(self.base, (8, 30, 44), pts)
            pygame.draw.polygon(self.base, (20, 70, 96), pts, 1)
        self.aurora = [self._aurora(1.0, 0.0), self._aurora(0.55, 2.0)]
        self.snow = [[rng.uniform(0, W), rng.uniform(0, H), rng.choice((0.6, 1.1, 1.8)), rng.random() * 6.28] for _ in range(110)]

    def _aurora(self, intensity, phase):
        surf = pygame.Surface((W * 2, 260)).convert()
        surf.fill((0, 0, 0))
        for layer in range(14):
            k = layer / 13
            pts_top, pts_bottom = [], []
            for x in range(0, W * 2 + 40, 40):
                top = 30 + 34 * math.sin(x * 0.006 + phase) + 18 * math.sin(x * 0.017 + phase * 2)
                pts_top.append((x, top))
                pts_bottom.append((x, top + 200 - layer * 12))
            hue = gfx.lerp_color((30, 255, 170), (110, 120, 255), 0.5 + 0.5 * math.sin(layer * 0.3 + phase))
            pygame.draw.polygon(surf, gfx.scale_color(hue, (0.06 + 0.16 * k) * intensity), pts_top + pts_bottom[::-1])
        return surf

    def update(self):
        super().update()
        for s in self.snow:
            s[1] += s[2]
            s[0] += math.sin(self.t * 0.02 + s[3]) * 0.4
            if s[1] > H + 4:
                s[1], s[0] = -4, self.rng.uniform(0, W)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        a = int(self.t * 0.25) % (W * 2 // 2)
        surf.blit(self.aurora[0], (-a, 0), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(self.aurora[0], (-a + W * 2, 0), special_flags=pygame.BLEND_RGB_ADD)
        b = int(self.t * 0.12) % W
        surf.blit(self.aurora[1], (b - W, 30), special_flags=pygame.BLEND_RGB_ADD)
        for x, y, sp, ph in self.snow:
            size = 1 if sp < 1 else 2
            col = (150, 190, 210) if sp < 1 else (220, 240, 255)
            pygame.draw.circle(surf, col, (int(x), int(y)), size)


class CorruptBG(Background):
    """Unstable purple data with random glitches applied to the whole frame."""
    seed = 55

    def __init__(self, biome):
        super().__init__(biome)
        rng = self.rng
        main, acc = biome.main, biome.accent
        for _ in range(170):                             # dead pixels / circuit fragments
            x, y = rng.randint(0, W // 8) * 8, rng.randint(0, H // 8) * 8
            col = main if rng.random() < 0.75 else acc
            pygame.draw.rect(self.base, gfx.scale_color(col, rng.uniform(0.06, 0.20)), (x, y, rng.choice((8, 16, 40, 90, 160)), rng.choice((8, 8, 16))))
        for _ in range(16):                              # vertical data buses
            x = rng.randint(0, W // 8) * 8
            pygame.draw.line(self.base, gfx.scale_color(main, 0.13), (x, 0), (x, H), 2)
        glow = pygame.Surface((W, H)).convert()
        glow.fill((0, 0, 0))
        gfx.draw_glow(glow, (W // 2, H // 2), 520, main, 0.32)
        self.base.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.glitch = 0
        self.slices = []
        self.blocks = []
        self.noise_y = 0.0
        self.flicker = []

    def update(self):
        super().update()
        rng = self.rng
        self.noise_y = (self.noise_y + 1.6) % (H + 80)
        if rng.random() < 0.12 and len(self.flicker) < 14:
            self.flicker.append([rng.randint(0, W // 8) * 8, rng.randint(0, H // 8) * 8, rng.choice((16, 32, 64)), rng.choice((8, 16)),
                                 rng.choice((self.biome.main, self.biome.accent)), rng.randint(6, 26)])
        for f in self.flicker[:]:
            f[5] -= 1
            if f[5] <= 0:
                self.flicker.remove(f)
        if self.glitch > 0:
            self.glitch -= 1
        elif rng.random() < 0.02:
            self.glitch = rng.randint(4, 12)
            self.slices = [(rng.randint(0, H - 60), rng.randint(6, 60), rng.randint(-40, 40)) for _ in range(rng.randint(2, 5))]
            self.blocks = [(rng.randint(0, W - 100), rng.randint(0, H - 40), rng.randint(20, 160), rng.randint(4, 30),
                            rng.choice((self.biome.main, self.biome.accent, (255, 255, 255)))) for _ in range(rng.randint(2, 6))]

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        rng = random.Random(self.t // 2)
        y0 = int(self.noise_y) - 40
        for _ in range(46):                              # a band of static drifting down the screen
            pygame.draw.rect(surf, gfx.scale_color(self.biome.main, rng.uniform(0.08, 0.28)),
                             (rng.randint(0, W), y0 + rng.randint(0, 40), rng.choice((4, 8, 24, 60)), rng.choice((1, 2, 2, 4))))
        for x, y, w, h, col, life in self.flicker:
            pygame.draw.rect(surf, gfx.scale_color(col, 0.42 * min(1.0, life / 8)), (x, y, w, h))

    def post(self, surf):
        if self.glitch <= 0:
            return
        for y, h, dx in self.slices:
            tmp = surf.subsurface((0, y, W, h)).copy()
            surf.blit(tmp, (dx, y))
        for x, y, w, h, col in self.blocks:
            pygame.draw.rect(surf, gfx.scale_color(col, 0.55), (x, y, w, h))


class VoidBG(Background):
    """Deep space: parallax stars, nebula and a slow rotating vortex."""
    seed = 66

    def __init__(self, biome):
        super().__init__(biome)
        rng = self.rng
        neb = pygame.Surface((W, H)).convert()
        neb.fill((0, 0, 0))
        for cx, cy, r, col in ((300, 220, 420, (60, 20, 110)), (1000, 520, 480, (20, 30, 110)), (700, 100, 300, (90, 20, 90))):
            gfx.draw_glow(neb, (cx, cy), r, col, 0.55)
        self.base.blit(neb, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.stars = [[rng.uniform(0, W), rng.uniform(0, H), rng.choice((0.08, 0.2, 0.45)), rng.random() * 6.28] for _ in range(130)]
        self.streaks = []

    def update(self):
        super().update()
        for s in self.stars:
            s[0] -= s[2]
            if s[0] < -2:
                s[0], s[1] = W + 2, self.rng.uniform(0, H)
        if self.rng.random() < 0.006 and len(self.streaks) < 2:
            self.streaks.append([self.rng.uniform(W * 0.4, W), self.rng.uniform(0, H * 0.6), 24])
        for s in self.streaks[:]:
            s[0] -= 16
            s[1] += 6
            s[2] -= 1
            if s[2] <= 0:
                self.streaks.remove(s)

    def draw(self, surf):
        surf.blit(self.base, (0, 0))
        cx, cy = W / 2, H / 2
        main = self.biome.main
        for ring in range(6):
            radius = 120 + ring * 80
            rot = self.t * (0.004 + ring * 0.0015) * (1 if ring % 2 else -1)
            segs = 20 + ring * 4
            col = gfx.scale_color(main, 0.26 + 0.035 * ring)
            for i in range(segs):
                if i % 3 == 2:
                    continue
                a0 = rot + i * math.tau / segs
                a1 = a0 + math.tau / segs * 0.6
                pygame.draw.line(surf, col, (cx + math.cos(a0) * radius, cy + math.sin(a0) * radius * 0.62),
                                 (cx + math.cos(a1) * radius, cy + math.sin(a1) * radius * 0.62), 1 + (ring == 0))
        gfx.draw_glow(surf, (cx, cy), 170 + int(8 * math.sin(self.t * 0.03)), main, 0.32)
        for x, y, sp, ph in self.stars:
            b = 0.5 + 0.5 * math.sin(self.t * 0.05 + ph)
            v = int(70 + 150 * b * (0.4 + sp))
            pygame.draw.rect(surf, (v, v, min(255, v + 25)), (int(x), int(y), 2 if sp > 0.3 else 1, 2 if sp > 0.3 else 1))
        for x, y, life in self.streaks:
            pygame.draw.line(surf, gfx.scale_color((220, 200, 255), life / 24), (x, y), (x + 60, y - 22), 2)


class TitleBG(VoidBG):
    """Menu background: the void with a green grid floor."""
    seed = 77

    def __init__(self, biome=None):
        super().__init__(biome or BIOMES[5])


BG_CLASSES = {"boot": BootBG, "stream": StreamBG, "firewall": FirewallBG, "frozen": FrozenBG, "corrupt": CorruptBG, "void": VoidBG}


def make_background(sector):
    biome = BIOMES[sector % len(BIOMES)]
    return BG_CLASSES[biome.id](biome)
