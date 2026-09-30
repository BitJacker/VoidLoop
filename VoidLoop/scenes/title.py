"""Boot splash, main menu and every screen reachable from it."""
import math
import random

import pygame

from .. import biomes, campaign, gfx, __version__
from ..achievements import ACHIEVEMENTS
from ..bot import Bot
from ..i18n import i18n, T
from ..settings import (W, H, LANGUAGES, MODES, SHIP_COLORS, DIFFICULTY_ORDER, DIFFICULTIES, P2_COLOR)
from ..ui import Menu, Item, draw_header, draw_hint
from ..weapons import Loadout
from ..world import World
from .base import Scene, is_back, is_confirm


def draw_title_logo(surf, t, y=118):
    gfx.draw_logo(surf, W // 2, y - 52, 46, t / 60.0, gfx.GREEN, gfx.CYAN)
    gfx.glow_text(surf, "VOID LOOP", (W // 2, y + 46), "title", 80, gfx.GREEN, "center", 0.75)


class BootScene(Scene):
    """Logo splash while sounds are synthesized."""

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()
        self.ready = False
        self.progress = 0.0
        self.step = 0

    def update(self):
        super().update()
        self.bg.update()
        if self.t == 4:
            self.app.audio.load_sfx(self._progress)
            self.step = 1
        elif self.t == 8:
            self.app.audio.preload_music("menu")
            self.ready = True
        if self.ready and self.t > 84:
            self.app.go(MainMenu(self.app), fade=True)

    def _progress(self, p):
        self.progress = p

    def event(self, e):
        if self.ready and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.t > 20:
            self.app.go(MainMenu(self.app), fade=True)

    def draw(self, surf):
        self.bg.draw(surf)
        k = min(1.0, self.t / 30)
        surf.blit(gfx.tint_overlay((0, 0, 0), 90), (0, 0))
        draw_title_logo(surf, self.t, 300)
        gfx.draw_text(surf, "BITJACKER", (W // 2, 470), "display", 20, gfx.scale_color(gfx.CYAN, k), "center")
        bar = pygame.Rect(W // 2 - 160, 560, 320, 8)
        gfx.bar(surf, bar, 1.0 if self.ready else min(0.95, self.t / 10), gfx.GREEN, border=gfx.scale_color(gfx.GREEN, 0.5), border_w=1)
        gfx.draw_text(surf, T("boot.loading"), (W // 2, 584), "mono", 16, (120, 150, 150), "center")


class MainMenu(Scene):
    music = "menu"

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()
        self.demo = None
        self.bot = Bot(0.85)
        self.demo_rng = random.Random()
        self.menu = None
        self.rebuild()

    def rebuild(self):
        app = self.app
        items = []
        if app.save.has_story():
            items.append(Item("continue", lambda: T("menu.continue"), color=gfx.GREEN, icon="play"))
        items += [
            Item("new", lambda: T("menu.new_game"), color=gfx.CYAN),
            Item("modes", lambda: T("menu.modes"), color=gfx.PURPLE),
            Item("options", lambda: T("menu.options"), color=gfx.WHITE),
            Item("achievements", lambda: T("menu.achievements"), color=gfx.GOLD),
            Item("help", lambda: T("menu.help"), color=gfx.ORANGE),
            Item("quit", lambda: T("menu.quit"), color=gfx.RED),
        ]
        self.menu = Menu(app, items, W // 2, 292, 430, 44, 7, 20)

    def enter(self):
        super().enter()
        self.rebuild()
        self.start_demo()

    def start_demo(self):
        stage = self.demo_rng.choice((2, 5, 6, 9, 10, 13, 14, 17, 18, 21, 22))
        spec = campaign.story_spec(stage)
        lo = Loadout(["BLASTER", "TWIN"])
        self.demo = World(spec, DIFFICULTIES["NORMAL"], lo, [self.app.settings.color], seed=self.demo_rng.randint(0, 10 ** 6))
        for p in self.demo.players:
            p.max_hp = p.hp = 99
        self.bot = Bot(0.9)

    def event(self, e):
        key = self.menu.event(e)
        app = self.app
        if key == "continue":
            from ..run import Run
            s = app.save.story
            Run(app, "STORY", s["difficulty"], s["players"], s).begin()
        elif key == "new":
            if app.save.has_story():
                app.go(ConfirmScene(app, T("confirm.new_game"), lambda: app.go(SetupScene(app, "STORY")), lambda: app.go(MainMenu(app))))
            else:
                app.go(SetupScene(app, "STORY"))
        elif key == "modes":
            app.go(ModeSelectScene(app))
        elif key == "options":
            app.go(OptionsScene(app))
        elif key == "achievements":
            app.go(AchievementsScene(app))
        elif key == "help":
            app.go(HelpScene(app))
        elif key == "quit":
            app.running = False

    def update(self):
        super().update()
        self.menu.update()
        w = self.demo
        if w is not None:
            w.update(self.bot.inputs(w))
            w.pop_events()
            for p in w.players:
                p.hp = max(p.hp, 50)
            if w.state != "playing" or w.time > 60 * 40:
                self.start_demo()

    def draw(self, surf):
        if self.demo is not None:
            self.demo.draw(surf, shake=False)
        else:
            self.bg.update()
            self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 2, 10), 175), (0, 0))
        draw_title_logo(surf, self.t)
        gfx.draw_text(surf, T("menu.tagline"), (W // 2, 240), "mono", 22, gfx.scale_color(gfx.CYAN, 0.9), "center")
        gfx.panel(surf, (W // 2 - 250, 274, 500, len(self.menu.items) * 51 + 26), (30, 60, 70), fill=(2, 4, 10, 165), border=1, cut=16, halo=False)
        self.menu.draw(surf)
        save = self.app.save
        if save.has_story() and self.menu.items[0].key == "continue":
            s = save.story
            sector, k = divmod(min(s["stage"], 23), 4)
            info = T("menu.save_info", sector=sector + 1, stage=k + 1, coins=s["coins"])
            if s.get("loop", 1) > 1:
                info += "  ·  " + T("menu.loop", n=s["loop"])
            gfx.draw_text(surf, info, (W // 2, self.menu.items[0].rect.bottom + 1), "mono", 13, (120, 160, 150), "midtop")
        gfx.draw_text(surf, "v%s" % __version__, (16, H - 12), "mono", 15, (90, 110, 130), "bottomleft")
        gfx.draw_text(surf, "F11 " + T("menu.fullscreen") + "   M " + T("menu.mute"), (W - 16, H - 12), "mono", 15, (90, 110, 130), "bottomright")


class ConfirmScene(Scene):
    def __init__(self, app, message, on_yes, on_no):
        super().__init__(app)
        self.message = message
        self.on_yes, self.on_no = on_yes, on_no
        self.bg = biomes.TitleBG()
        self.menu = Menu(app, [Item("no", lambda: T("confirm.no"), color=gfx.GREEN), Item("yes", lambda: T("confirm.yes"), color=gfx.RED)],
                         W // 2, 420, 380, 56, 12, 22)

    def event(self, e):
        if is_back(e):
            self.on_no()
            return
        key = self.menu.event(e)
        if key == "yes":
            self.on_yes()
        elif key == "no":
            self.on_no()

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 150), (0, 0))
        gfx.panel(surf, (W // 2 - 400, 200, 800, 320), gfx.RED, fill=(10, 4, 8, 235), border=2, cut=16)
        y = 240
        for para in self.message.split("\n"):
            for ln in gfx.wrap_text(para, "mono", 24, 700) if para else [""]:
                gfx.draw_text(surf, ln, (W // 2, y), "mono", 24, gfx.WHITE, "center")
                y += 34
        self.menu.draw(surf)


# =============================================================================================
class ModeSelectScene(Scene):
    music = "menu"
    ORDER = ("ENDLESS", "TIME_ATTACK", "BOSS_RUSH", "HORDE")
    COLORS = {"ENDLESS": gfx.ORANGE, "TIME_ATTACK": gfx.CYAN, "BOSS_RUSH": gfx.PURPLE, "HORDE": gfx.RED}
    ICONS = {"ENDLESS": "pulse", "TIME_ATTACK": "speed", "BOSS_RUSH": "skull", "HORDE": "mace"}

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()
        items = [Item(m, (lambda m=m: T("mode.%s" % m.lower())), color=self.COLORS[m], icon=self.ICONS[m]) for m in self.ORDER]
        items.append(Item("back", lambda: T("menu.back"), color=gfx.SILVER))
        self.menu = Menu(app, items, 400, 190, 480, 62, 14, 20)

    def event(self, e):
        if is_back(e):
            self.app.go(MainMenu(self.app))
            return
        key = self.menu.event(e)
        if key == "back":
            self.app.go(MainMenu(self.app))
        elif key:
            self.app.go(SetupScene(self.app, key))

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 140), (0, 0))
        draw_header(surf, T("menu.modes"), None, gfx.PURPLE)
        self.menu.draw(surf)
        sel = self.menu.items[self.menu.sel].key
        panel = pygame.Rect(700, 190, 500, 420)
        col = self.COLORS.get(sel, gfx.GRAY)
        gfx.panel(surf, panel, col, fill=(4, 8, 18, 222), border=2, cut=16)
        if sel in self.ORDER:
            gfx.draw_icon(surf, self.ICONS[sel], panel.centerx, panel.y + 70, 34, col)
            gfx.draw_text(surf, T("mode.%s" % sel.lower()).upper(), (panel.centerx, panel.y + 132), "display", 26, col, "center")
            y = panel.y + 176
            for ln in gfx.wrap_text(T("mode.%s.desc" % sel.lower()), "mono", 20, panel.w - 56):
                gfx.draw_text(surf, ln, (panel.x + 28, y), "mono", 20, gfx.WHITE)
                y += 27
            best = self.app.save.best(sel, self.app.settings.difficulty)
            txt = T("mode.best", n="{:,}".format(best["score"])) if best else T("mode.no_score")
            gfx.draw_text(surf, txt, (panel.centerx, panel.bottom - 40), "mono", 20, gfx.GOLD if best else (120, 135, 155), "center")
        draw_hint(surf, T("hint.menu"))


class SetupScene(Scene):
    """Difficulty / players / ship colour, then go."""
    music = "menu"

    def __init__(self, app, mode):
        super().__init__(app)
        self.mode = mode
        self.bg = biomes.TitleBG()
        s = app.settings
        self.items = [
            Item("diff", lambda: T("setup.difficulty"), "choice", [(d, (lambda d=d: T("diff.%s" % d.lower()))) for d in DIFFICULTY_ORDER],
                 lambda: s.difficulty, lambda v: setattr(s, "difficulty", v), color=gfx.RED),
            Item("players", lambda: T("setup.players"), "choice", [(1, lambda: T("setup.one_player")), (2, lambda: T("setup.two_players"))],
                 lambda: s.players, lambda v: setattr(s, "players", v), color=gfx.PURPLE),
            Item("color", lambda: T("setup.ship"), "choice", [(c, c) for c in SHIP_COLORS], lambda: s.ship_color,
                 lambda v: setattr(s, "ship_color", v), color=gfx.CYAN),
            Item("start", lambda: T("setup.start"), color=gfx.GREEN, icon="play"),
            Item("back", lambda: T("menu.back"), color=gfx.SILVER),
        ]
        self.menu = Menu(app, self.items, 400, 200, 540, 58, 12, 20)

    def event(self, e):
        if is_back(e):
            self.leave_to_menu()
            return
        key = self.menu.event(e)
        if key == "back":
            self.leave_to_menu()
        elif key == "start":
            self.start()

    def leave_to_menu(self):
        self.app.settings.save()
        self.app.go(MainMenu(self.app) if self.mode == "STORY" else ModeSelectScene(self.app))

    def start(self):
        from ..run import Run
        app = self.app
        s = app.settings
        s.last_mode = self.mode
        s.save()
        if self.mode == "STORY":
            story = app.save.start_story(s.difficulty, s.players)
            app.save.save()
            Run(app, "STORY", s.difficulty, s.players, story).begin()
        else:
            Run(app, self.mode, s.difficulty, s.players).begin()

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 140), (0, 0))
        s = self.app.settings
        title = T("menu.new_game") if self.mode == "STORY" else T("mode.%s" % self.mode.lower())
        draw_header(surf, title, T("setup.subtitle"), gfx.GREEN)
        self.menu.draw(surf)
        panel = pygame.Rect(720, 190, 480, 430)
        gfx.panel(surf, panel, s.color, fill=(4, 8, 18, 222), border=2, cut=16)
        cx, cy = panel.centerx, panel.y + 120
        gfx.draw_glow(surf, (cx, cy), 120, s.color, 0.4)
        gfx.draw_ship(surf, cx - (40 if s.players == 2 else 0), cy, self.t * 0.03, 46, s.color, 0.6, self.t)
        if s.players == 2:
            gfx.draw_ship(surf, cx + 44, cy + 6, self.t * 0.03 + 1.2, 46, P2_COLOR, 0.6, self.t)
        cfg = s.cfg
        rows = [(T("setup.hp"), str(cfg["hp"])), (T("setup.speed"), "x%.1f" % cfg["speed"]), (T("setup.cost"), str(cfg["cost"])),
                (T("setup.score"), "x%.1f" % cfg["score"])]
        y = panel.y + 230
        for label, value in rows:
            gfx.draw_text(surf, label, (panel.x + 40, y), "mono", 21, gfx.WHITE)
            gfx.draw_text(surf, value, (panel.right - 40, y), "display", 19, gfx.GOLD, "topright")
            y += 38
        best = self.app.save.best(self.mode, s.difficulty) if self.mode != "STORY" else None
        if best:
            gfx.draw_text(surf, T("mode.best", n="{:,}".format(best["score"])), (panel.centerx, panel.bottom - 34), "mono", 19, gfx.GOLD, "center")
        draw_hint(surf, T("hint.menu"))


class OptionsScene(Scene):
    music = "menu"

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()
        s = app.settings

        def set_lang(v):
            s.language = v
            i18n.set_language(v)

        def set_fs(v):
            if v != s.fullscreen:
                app.toggle_fullscreen()

        def audio_changed(_it):
            app.audio.set_volumes(s.sfx, s.music)

        items = [
            Item("lang", lambda: T("opt.language"), "choice", [(c, n) for c, n in LANGUAGES], lambda: s.language, set_lang, color=gfx.GREEN,
                 on_change=lambda it: self.on_lang()),
            Item("music", lambda: T("opt.music"), "slider", get=lambda: s.music, set=lambda v: setattr(s, "music", v), color=gfx.CYAN, on_change=audio_changed),
            Item("sfx", lambda: T("opt.sfx"), "slider", get=lambda: s.sfx, set=lambda v: setattr(s, "sfx", v), color=gfx.CYAN,
                 on_change=lambda it: (audio_changed(it), app.audio.play("shoot"))),
            Item("fullscreen", lambda: T("opt.fullscreen"), "toggle", get=lambda: s.fullscreen, set=set_fs, color=gfx.PURPLE),
            Item("crt", lambda: T("opt.crt"), "toggle", get=lambda: s.crt, set=lambda v: setattr(s, "crt", v), color=gfx.PURPLE),
            Item("shake", lambda: T("opt.shake"), "toggle", get=lambda: s.shake, set=lambda v: setattr(s, "shake", v), color=gfx.PURPLE),
            Item("fps", lambda: T("opt.fps"), "toggle", get=lambda: s.show_fps, set=lambda v: setattr(s, "show_fps", v), color=gfx.PURPLE),
            Item("back", lambda: T("menu.back"), color=gfx.SILVER),
        ]
        self.menu = Menu(app, items, W // 2, 150, 720, 52, 9, 20)

    def on_lang(self):
        pass

    def event(self, e):
        if is_back(e):
            self.close()
            return
        key = self.menu.event(e)
        if key == "back":
            self.close()

    def close(self):
        self.app.settings.save()
        self.app.go(MainMenu(self.app))

    def update(self):
        super().update()
        self.bg.update()
        self.menu.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 150), (0, 0))
        draw_header(surf, T("menu.options"), None, gfx.CYAN, 46)
        self.menu.draw(surf)
        draw_hint(surf, T("hint.menu"))


class AchievementsScene(Scene):
    music = "menu"

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()

    def event(self, e):
        if is_back(e) or is_confirm(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self.app.go(MainMenu(self.app))

    def update(self):
        super().update()
        self.bg.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 150), (0, 0))
        save = self.app.save
        done = sum(1 for a, _ in ACHIEVEMENTS if save.has(a))
        draw_header(surf, T("menu.achievements"), T("ach.progress", done=done, total=len(ACHIEVEMENTS)), gfx.GOLD, 40)
        per_col = (len(ACHIEVEMENTS) + 1) // 2
        for i, (aid, icon) in enumerate(ACHIEVEMENTS):
            col, row = divmod(i, per_col)
            x = 56 + col * 600
            y = 148 + row * 46
            got = save.has(aid)
            c = gfx.GOLD if got else (70, 80, 100)
            rect = pygame.Rect(x, y, 570, 40)
            gfx.panel(surf, rect, gfx.scale_color(c, 0.7), fill=(*gfx.scale_color(c, 0.12), 210), border=1, cut=8, halo=False)
            gfx.draw_icon(surf, icon if got else "lock", x + 26, y + 20, 10, c)
            gfx.draw_text(surf, T("ach.%s.name" % aid), (x + 54, y + 4), "display", 15, gfx.WHITE if got else (150, 160, 182))
            gfx.draw_text(surf, T("ach.%s.desc" % aid), (x + 54, y + 22), "mono", 14, (190, 200, 215) if got else (128, 140, 162))
        st = save.stats
        hours, mins = int(st["playtime"] // 3600), int(st["playtime"] % 3600 // 60)
        txt = T("ach.stats", kills=int(st["kills"]), deaths=int(st["deaths"]), time="%dh %02dm" % (hours, mins), bosses=int(st["bosses"]),
                fragments=int(st["fragments"]))
        gfx.draw_text(surf, txt, (W // 2, H - 44), "mono", 18, (170, 190, 210), "center")
        draw_hint(surf, T("hint.back"), H - 18)


class HelpScene(Scene):
    music = "menu"

    def __init__(self, app):
        super().__init__(app)
        self.bg = biomes.TitleBG()

    def event(self, e):
        if is_back(e) or is_confirm(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self.app.go(MainMenu(self.app))

    def update(self):
        super().update()
        self.bg.update()

    def draw(self, surf):
        self.bg.draw(surf)
        surf.blit(gfx.tint_overlay((0, 0, 8), 150), (0, 0))
        draw_header(surf, T("menu.help"), None, gfx.ORANGE, 40)
        for x, title, key, color in ((50, T("help.controls_p1"), "help.controls", gfx.GREEN), (660, T("help.controls_p2"), "help.controls2", gfx.ORANGE)):
            panel = pygame.Rect(x, 124, 570, 296)
            gfx.panel(surf, panel, color, fill=(4, 8, 18, 222), border=2, cut=14)
            gfx.draw_text(surf, title, (panel.x + 24, panel.y + 14), "display", 18, color)
            y = panel.y + 52
            for row in i18n.tl(key):
                keys, _, action = row.partition("|")
                gfx.draw_text(surf, keys, (panel.x + 24, y), "mono", 19, gfx.WHITE)
                gfx.draw_text(surf, action, (panel.x + 250, y), "mono", 19, (170, 190, 210))
                y += 26
        panel = pygame.Rect(50, 434, 1180, 240)
        gfx.panel(surf, panel, gfx.CYAN, fill=(4, 8, 18, 222), border=2, cut=14)
        gfx.draw_text(surf, T("help.how_title"), (panel.x + 24, panel.y + 14), "display", 18, gfx.CYAN)
        y = panel.y + 50
        for line in i18n.tl("help.text"):
            for ln in gfx.wrap_text(line, "mono", 19, panel.w - 70):
                gfx.draw_text(surf, ln, (panel.x + 28, y), "mono", 19, gfx.WHITE)
                y += 25
            y += 4
        draw_hint(surf, T("hint.back"), H - 18)
