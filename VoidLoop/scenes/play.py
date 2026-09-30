"""The gameplay scene: input, HUD, pause menu and in-game radio chatter."""
import math

import pygame
from pygame import Vector2

from .. import biomes, gfx
from ..achievements import live_check
from ..bosses import BOSSES
from ..entities import PlayerInput
from ..i18n import i18n, T
from ..settings import W, H, P2_COLOR
from ..ui import Menu, Item
from ..weapons import WEAPONS, TIME_ATTACK_TIERS
from ..world import World, POWERUPS
from .base import Scene, is_click

BOSS_MUSIC = {"origin": "final"}
MODE_KEYS = {"STORY": "mode.story", "ENDLESS": "mode.endless", "TIME_ATTACK": "mode.time_attack", "BOSS_RUSH": "mode.boss_rush", "HORDE": "mode.horde"}


class Bark:
    """A line of radio chatter shown at the bottom of the screen."""

    def __init__(self, line, frames=210):
        self.line = line
        self.t = 0
        self.frames = frames


class PlayScene(Scene):
    def __init__(self, app, run, spec, world=None):
        super().__init__(app)
        self.run = run
        self.spec = spec
        colors = [app.settings.color] + [P2_COLOR]
        self.world = world or World(spec, run.cfg, run.loadout, colors, players=run.players)
        self.paused = False
        self.menu = None
        self.bark = None
        self.bark_cooldown = 240
        self.bark_history = {}
        self.chatter_timer = 60 * 18
        self.banner_t = self.banner_total = 0
        self.banner_lines = []
        self.edge = set()
        self.wheel = 0
        self.end_wait = 0
        self._ended = False
        self.boss_warning = 0
        self.hint_t = 60 * 14 if (spec.mode == "STORY" and spec.index <= 1) else 0
        self._build_banner()
        self._last_music = None
        self.mouse_visible = True

    # ---- lifecycle -------------------------------------------------------------------------
    def enter(self):
        self.play_music()
        pygame.mouse.set_visible(True)

    def leave(self):
        pygame.mouse.set_visible(True)

    def play_music(self):
        w = self.world
        name = w.biome.music
        if w.boss is not None:
            name = BOSS_MUSIC.get(w.boss.id, "boss")
        if name != self._last_music:
            self._last_music = name
            self.app.audio.play_music(name)

    def _build_banner(self):
        spec = self.spec
        biome = biomes.BIOMES[spec.sector]
        if spec.mode == "STORY":
            sector, k = divmod(spec.index, 4)
            title = "%d-%d" % (sector + 1, k + 1)
            sub = T("sector.%s.name" % biome.id)
            self.banner_lines = [(title, "title", 54, gfx.WHITE), (sub, "display", 24, biome.main)]
            if spec.kind == "boss":
                self.banner_lines.append((T("hud.boss_stage"), "display", 22, gfx.RED))
        elif spec.mode == "BOSS_RUSH":
            self.banner_lines = [(T("hud.boss_n", n=spec.index + 1), "title", 44, gfx.WHITE), (T("sector.%s.name" % biome.id), "display", 24, biome.main)]
        elif spec.mode == "HORDE":
            self.banner_lines = [(T("hud.round", n=spec.index), "title", 44, gfx.WHITE), (T("sector.%s.name" % biome.id), "display", 24, biome.main)]
        elif spec.mode == "TIME_ATTACK":
            self.banner_lines = [(T("hud.level", n=spec.index), "title", 44, gfx.WHITE), (T("sector.%s.name" % biome.id), "display", 24, biome.main)]
        else:
            self.banner_lines = [(T(MODE_KEYS[spec.mode]).upper(), "title", 44, gfx.WHITE), (T("sector.%s.name" % biome.id), "display", 24, biome.main)]
        self.set_banner(self.banner_lines, 170)

    def set_banner(self, lines, frames):
        self.banner_lines = lines
        self.banner_t = self.banner_total = frames

    # ---- input --------------------------------------------------------------------------------
    def event(self, e):
        if self.paused:
            key = self.menu.event(e)
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.set_pause(False)
            elif key == "resume":
                self.set_pause(False)
            elif key == "save":
                self.run.save_story()
                self.app.toast(T("pause.saved"), "", "check", gfx.GREEN)
                self.set_pause(False)
            elif key == "menu":
                self.run.save_story()
                self.run.quit_to_menu()
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.set_pause(True)
            elif e.key == pygame.K_LSHIFT:
                self.edge.add("p1_dash")
            elif e.key == pygame.K_RSHIFT:
                self.edge.add("p2_dash")
            elif e.key == pygame.K_SPACE:
                self.edge.add("p1_pulse")
            elif e.key in (pygame.K_RALT, pygame.K_KP_PERIOD):
                self.edge.add("p2_pulse")
            elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.edge.add("weapon%d" % (e.key - pygame.K_1))
            elif e.key == pygame.K_q:
                self.wheel -= 1
            elif e.key == pygame.K_e:
                self.wheel += 1
        elif e.type == pygame.MOUSEWHEEL:
            self.wheel += -1 if e.y > 0 else 1 if e.y < 0 else 0
        elif e.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            if not self.paused and self.world.state == "playing":
                self.set_pause(True)

    def set_pause(self, on):
        self.paused = on
        self.app.audio.play("ui_select" if on else "ui_back")
        if on:
            items = [Item("resume", lambda: T("pause.continue"), color=gfx.GREEN)]
            if self.run.story is not None:
                items.append(Item("save", lambda: T("pause.save"), color=gfx.CYAN))
            items.append(Item("menu", lambda: T("pause.exit"), color=gfx.RED))
            self.menu = Menu(self.app, items, W // 2, 300, 440, 56, 12, 22)

    def read_inputs(self):
        keys = pygame.key.get_pressed()
        world = self.world
        inputs = {}
        one = len(world.players) == 1
        mouse = Vector2(pygame.mouse.get_pos())
        buttons = pygame.mouse.get_pressed()
        # ---- player 1
        mv = Vector2(keys[pygame.K_d] - keys[pygame.K_a], keys[pygame.K_s] - keys[pygame.K_w])
        if one:
            mv += Vector2(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], keys[pygame.K_DOWN] - keys[pygame.K_UP])
        kb_fire = one and (keys[pygame.K_RETURN] or keys[pygame.K_KP0])
        fire = bool(buttons[0]) or bool(kb_fire)
        aim = mouse if (buttons[0] or not kb_fire) else None
        p1 = PlayerInput(move=mv, aim=aim, fire=fire, sprint=bool(keys[pygame.K_LCTRL] or (one and keys[pygame.K_RCTRL])),
                         dash="p1_dash" in self.edge or (one and "p2_dash" in self.edge),
                         pulse="p1_pulse" in self.edge or (one and "p2_pulse" in self.edge), weapon_step=self.wheel)
        for i in range(4):
            if "weapon%d" % i in self.edge:
                p1.weapon_index = i
        inputs[1] = p1
        # ---- player 2
        if not one:
            mv2 = Vector2(keys[pygame.K_RIGHT] - keys[pygame.K_LEFT], keys[pygame.K_DOWN] - keys[pygame.K_UP])
            inputs[2] = PlayerInput(move=mv2, aim=None, fire=bool(keys[pygame.K_RETURN] or keys[pygame.K_KP0]),
                                    sprint=bool(keys[pygame.K_RCTRL]), dash="p2_dash" in self.edge, pulse="p2_pulse" in self.edge)
        self.edge.clear()
        self.wheel = 0
        return inputs

    # ---- barks --------------------------------------------------------------------------------------
    def say(self, key, priority=1, cooldown=420, force=False):
        """Show one line of radio chatter (rate limited)."""
        if self.bark is not None and not force:
            return
        if self.bark_cooldown > 0 and not force:
            return
        last = self.bark_history.get(key, -99999)
        if self.t - last < cooldown and not force:
            return
        line = i18n.pick_line(key)
        if line is None:
            return
        self.bark_history[key] = self.t
        self.bark = Bark(line)
        self.bark_cooldown = 200
        self.app.audio.play("blip1")

    # ---- update ---------------------------------------------------------------------------------------
    def update(self):
        super().update()
        if self.paused:
            self.menu.update()
            return
        world = self.world
        if self.bark is not None:
            self.bark.t += 1
            if self.bark.t > self.bark.frames:
                self.bark = None
        if self.bark_cooldown > 0:
            self.bark_cooldown -= 1
        if self.banner_t > 0:
            self.banner_t -= 1
        if self.hint_t > 0:
            self.hint_t -= 1
        if self.boss_warning > 0:
            self.boss_warning -= 1

        inputs = self.read_inputs() if world.state == "playing" else {}
        world.update(inputs)
        self.handle_events(world.pop_events())
        if world.boss is not None:
            self.play_music()
        if self.t % 20 == 0:
            live_check(self.app, self.run, world)

        self.chatter_timer -= 1
        if self.chatter_timer <= 0 and world.state == "playing" and world.boss is None:
            self.chatter_timer = 60 * 26
            self.say("chatter_s%d" % (world.sector + 1), cooldown=0)

        if world.state in ("won", "failed") and not self._ended:
            self._ended = True
            self.end_wait = 45 if world.state == "won" else 40
        if self._ended:
            self.end_wait -= 1
            if self.end_wait <= 0:
                self._ended = False
                self.end_wait = 999999
                if world.state == "won":
                    self.app.audio.play("win")
                    self.run.stage_won(world)
                else:
                    self.app.audio.play("gameover")
                    self.run.stage_failed(world)

    def handle_events(self, events):
        audio = self.app.audio
        world = self.world
        for name, arg in events:
            if name == "sfx":
                audio.play(arg)
            elif name == "bark":
                if arg == "boss_phase" and world.boss is not None:
                    key = "bark_boss_phase_%s" % world.boss.id
                    if not i18n.has_scene(key):
                        key = "bark_boss_phase"
                    self.say(key, cooldown=0, force=True)
                else:
                    key = {"first_kill": "bark_first_kill", "combo": "bark_combo", "low_hp": "bark_low_hp"}.get(arg)
                    if key:
                        self.say(key, cooldown=1500 if arg == "low_hp" else 900)
            elif name == "power":
                key = "bark_power_%s" % arg.lower()
                if i18n.has_scene(key):
                    self.say(key, cooldown=900)
            elif name == "boss_spawn":
                audio.play("warning")
                self.boss_warning = 150
                self.play_music()
                key = "bark_boss_%s" % arg
                if i18n.has_scene(key):
                    self.say(key, cooldown=0, force=True)
            elif name == "boss_dead":
                self.say("bark_boss_dead", cooldown=0, force=True)
                self._last_music = None
            elif name == "sector":
                self.set_banner([(T("sector.%s.name" % biomes.BIOMES[arg].id), "title", 44, biomes.BIOMES[arg].main),
                                 (T("sector.%s.sub" % biomes.BIOMES[arg].id), "mono", 22, gfx.WHITE)], 150)
                self._last_music = None
                self.play_music()
            elif name == "level":
                self.set_banner([(T("hud.level", n=arg), "title", 44, gfx.WHITE)], 90)
            elif name == "wave":
                self.set_banner([(T("hud.wave", n=arg), "title", 48, gfx.WHITE)], 90)
            elif name == "tier":
                self.set_banner([(T("hud.weapon_up"), "title", 40, gfx.GOLD)], 80)
            elif name == "stage_clear":
                self.say("bark_stage_clear", cooldown=0, force=True)
            elif name == "timeout":
                self.set_banner([(T("hud.timeout"), "title", 54, gfx.RED)], 80)

    # ---- drawing -------------------------------------------------------------------------------------------
    def draw(self, surf):
        world = self.world
        world.draw(surf, shake=self.app.settings.shake)
        self.draw_hud(surf)
        if self.paused:
            surf.blit(gfx.tint_overlay((0, 0, 8), 190), (0, 0))
            gfx.glow_text(surf, T("pause.title"), (W // 2, 200), "title", 52, gfx.GREEN, "center", 0.7)
            self.menu.draw(surf)

    def draw_hud(self, surf):
        world = self.world
        rules = world.rules
        t = self.t
        color = world.biome.main
        # ---- players: hearts, pulse energy, stamina
        y = 14
        for p in world.players:
            x = 16
            gfx.draw_text(surf, "P%d" % p.id, (x, y + 2), "display", 14, p.color)
            hx = x + 34
            for i in range(p.max_hp):
                filled = i < p.hp
                gfx.draw_heart(surf, hx + i * 26, y + 12, 11, gfx.RED if p.alive else gfx.GRAY, filled)
            bar_y = y + 30
            ready = p.energy >= 100
            gfx.bar(surf, (x + 34, bar_y, 130, 7), p.energy / 100.0, gfx.WHITE if ready and (t // 8) % 2 == 0 else p.color, border=(70, 80, 100), border_w=1)
            gfx.draw_text(surf, T("hud.pulse_ready") if ready else "", (x + 172, bar_y - 3), "mono", 15, gfx.WHITE)
            gfx.bar(surf, (x + 34, bar_y + 10, 130, 4), p.stamina / 100.0, gfx.scale_color(gfx.YELLOW, 0.9 if not p.exhausted else 0.4))
            y += 58
        # ---- top centre: mode label + progress, or the boss bar
        info = rules.hud()
        boss = world.boss
        if boss is not None:
            self.draw_boss_bar(surf, boss)
        else:
            gfx.draw_text(surf, info["label"] if not info.get("label") == "SYNC" else T("hud.sync"), (W // 2, 14), "display", 24,
                          gfx.RED if info.get("danger") and (t // 10) % 2 == 0 else gfx.WHITE, "midtop", shadow=True)
            if info.get("progress") is not None:
                gfx.bar(surf, (W // 2 - 190, 50, 380, 12), info["progress"], color, border=gfx.scale_color(color, 0.6), border_w=2)
            if info.get("sub"):
                gfx.draw_text(surf, info["sub"], (W // 2, 68), "mono", 18, gfx.scale_color(color, 0.9), "midtop")
        # ---- top right: coins + score
        gfx.draw_icon(surf, "coin", W - 30, 24, 8, gfx.GOLD)
        gfx.draw_text(surf, str(self.run.loadout.coins), (W - 46, 24), "display", 20, gfx.GOLD, "midright", shadow=True)
        gfx.draw_text(surf, T("hud.score", n="{:,}".format(self.run.score + world.score)), (W - 20, 46), "mono", 18, gfx.WHITE, "topright", shadow=True)
        secs = world.time // 60
        gfx.draw_text(surf, "%02d:%02d" % (secs // 60, secs % 60), (W - 20, 68), "mono", 16, (150, 165, 190), "topright")
        # ---- power-ups (right)
        py = 100
        for name, left in world.powers.items():
            pu = POWERUPS[name]
            gfx.draw_icon(surf, pu["icon"], W - 34, py + 10, 9, pu["color"])
            gfx.bar(surf, (W - 176, py + 6, 120, 8), left / pu["frames"], pu["color"], border=gfx.scale_color(pu["color"], 0.5), border_w=1)
            gfx.draw_text(surf, T("power." + name.lower()), (W - 182, py + 10), "mono", 14, pu["color"], "midright")
            py += 26
        # ---- combo (bottom left)
        if world.combo >= 2:
            k = min(1.0, world.combo_timer / 120)
            col = gfx.GOLD if world.combo >= 10 else gfx.ORANGE if world.combo >= 5 else gfx.WHITE
            pulse_size = 30 + (6 if world.combo_timer > 112 else 0)
            gfx.draw_text(surf, "x%d" % world.combo, (24, H - 96), "title", pulse_size, col, "bottomleft", shadow=True)
            gfx.draw_text(surf, T("hud.combo"), (24, H - 68), "mono", 16, col, "topleft")
            gfx.bar(surf, (24, H - 46, 120, 5), k, col)
        # ---- weapon (bottom left)
        lo = self.run.loadout
        wx = 24
        if world.spec.mode == "HORDE":
            gfx.draw_icon(surf, "mace", wx + 12, H - 24, 12, gfx.WHITE)
        elif world.spec.mode == "TIME_ATTACK":
            gfx.draw_text(surf, T("hud.weapon_tier", n=rules.tier + 1), (wx, H - 32), "mono", 16, gfx.GOLD, "midleft")
        else:
            for i, wid in enumerate(lo.weapons):
                sel = wid == lo.weapon
                r = pygame.Rect(wx + i * 44, H - 40, 38, 30)
                pygame.draw.rect(surf, gfx.scale_color(world.players[0].color, 0.3 if sel else 0.08), r)
                pygame.draw.rect(surf, world.players[0].color if sel else (70, 80, 100), r, 2 if sel else 1)
                gfx.draw_icon(surf, WEAPONS[wid]["icon"], r.centerx, r.centery, 9, gfx.WHITE if sel else (140, 150, 170))
                gfx.draw_text(surf, str(i + 1), (r.x + 3, r.y + 1), "mono", 11, (150, 160, 180))
        # ---- bottom centre: radio chatter
        if self.bark is not None:
            self.draw_bark(surf)
        # ---- control hint (first stages of the story)
        if self.hint_t > 0:
            a = min(1.0, self.hint_t / 30)
            hint = T("hud.hint_weapon") if self.run.loadout.can_shoot else T("hud.hint_move")
            gfx.draw_text(surf, hint, (W // 2, H - 118), "mono", 20, gfx.scale_color(gfx.WHITE, a), "center", shadow=True)
        # ---- banner
        if self.banner_t > 0:
            a = min(1.0, self.banner_t / 30, (self.banner_total - self.banner_t) / 20 + 0.02)
            y = 250
            for text, kind, size, col in self.banner_lines:
                gfx.draw_text(surf, text, (W // 2, y), kind, size, gfx.scale_color(col, max(0.0, min(1.0, a))), "center", shadow=True)
                y += size + 14
        # ---- boss warning
        if self.boss_warning > 0:
            k = (self.boss_warning // 10) % 2
            bar_h = 84
            pygame.draw.rect(surf, (60, 0, 0) if k else (30, 0, 0), (0, H // 2 - bar_h // 2, W, bar_h))
            gfx.draw_text(surf, T("hud.warning"), (W // 2, H // 2), "title", 56, gfx.RED if k else gfx.scale_color(gfx.RED, 0.6), "center")

    def draw_boss_bar(self, surf, boss):
        w = 700
        x = W // 2 - w // 2
        col = gfx.GREEN if boss.phase == 1 else gfx.ORANGE if boss.phase == 2 else gfx.RED
        col = boss.color if boss.phase == 1 else col
        name = T("boss." + boss.id)
        gfx.draw_text(surf, name, (W // 2, 12), "display", 22, gfx.WHITE, "midtop", shadow=True)
        pygame.draw.rect(surf, (10, 12, 22), (x, 44, w, 18))
        frac = max(0.0, boss.hp / boss.max_hp)
        pygame.draw.rect(surf, gfx.scale_color(col, 0.9), (x, 44, int(w * frac), 18))
        pygame.draw.rect(surf, gfx.mix_white(col, 0.5), (x, 44, int(w * frac), 5))
        pygame.draw.rect(surf, gfx.WHITE, (x, 44, w, 18), 2)
        for th in boss.thresholds:                                     # phase markers
            pygame.draw.line(surf, gfx.WHITE, (x + int(w * th), 44), (x + int(w * th), 62), 2)
        gfx.draw_text(surf, T("hud.phase", n=boss.phase), (x + w, 68), "mono", 16, col, "topright")
        if boss.invuln and not boss.dying:
            gfx.draw_text(surf, T("hud.invulnerable"), (x, 68), "mono", 16, gfx.WHITE, "topleft")

    def draw_bark(self, surf):
        b = self.bark
        line = b.line
        from .story import style_color
        col = style_color(self.app, line.style)
        k = min(1.0, b.t / 10, (b.frames - b.t) / 14)
        text = line.text
        wtxt = gfx.text_width(text, "mono", 22)
        w = max(360, wtxt + 130)
        x = W // 2 - w // 2
        y = H - 92 + int((1 - k) * 30)
        gfx.panel(surf, (x, y, w, 60), col, fill=(4, 8, 18, 225), border=2, cut=10)
        if line.speaker:
            gfx.draw_text(surf, line.speaker, (x + 18, y + 8), "display", 13, col)
        gfx.draw_text(surf, text, (x + 18, y + 30), "mono", 22, gfx.WHITE)
