"""Application shell: window, fixed-step main loop, scene switching and global overlays."""
import argparse
import os
import sys
import time
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from . import __version__, gfx  # noqa: E402
from .audio import Audio  # noqa: E402
from .i18n import i18n, T  # noqa: E402
from .paths import user_data_dir  # noqa: E402
from .save import SaveData  # noqa: E402
from .settings import Settings, W, H, FPS, LANG_CODES  # noqa: E402

STEP = 1.0 / FPS


def _fix_std_streams():
    """Windowed (no console) builds have sys.stdout/sys.stderr set to None."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, open(os.devnull, "w"))


def _make_dpi_aware():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class App:
    def __init__(self, headless=False, lang=None, fullscreen=None, no_audio=False):
        self.headless = headless
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        else:
            _make_dpi_aware()
        pygame.display.init()
        pygame.font.init()
        self.settings = Settings.load()
        if lang in LANG_CODES:
            self.settings.language = lang
        if fullscreen is not None:
            self.settings.fullscreen = fullscreen
        i18n.set_language(self.settings.language)
        self.save = SaveData.load()
        self.screen = self._create_window()
        self.clock = pygame.time.Clock()
        self.audio = Audio(self.settings.sfx, self.settings.music, enabled=not no_audio)
        self.scene = None
        self._pending = None
        self._fade = 0.0
        self._fade_dir = 0
        self.toasts = []
        self.running = True
        self.frame_no = 0
        self._fps = 0.0
        self._acc = 0.0
        self._last = time.perf_counter()
        self._black = pygame.Surface((W, H)).convert()
        self._black.fill((0, 0, 0))

    # ---- window ---------------------------------------------------------------------
    def _create_window(self):
        flags = pygame.SCALED | pygame.RESIZABLE
        if self.settings.fullscreen and not self.headless:
            flags |= pygame.FULLSCREEN
        try:
            screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("VOID LOOP")
        try:
            icon = pygame.Surface((64, 64), pygame.SRCALPHA)
            gfx.draw_logo(icon, 32, 32, 28, 0.0)
            pygame.display.set_icon(icon)
        except pygame.error:
            pass
        return screen

    def toggle_fullscreen(self):
        self.settings.fullscreen = not self.settings.fullscreen
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass
        self.settings.save()

    # ---- scenes ------------------------------------------------------------------------
    def go(self, scene, fade=True):
        """Switch to ``scene`` (with a short fade through black)."""
        if self.scene is None or not fade:
            self._switch(scene)
            return
        self._pending = scene
        self._fade_dir = 1

    def _switch(self, scene):
        if self.scene is not None:
            self.scene.leave()
        self.scene = scene
        scene.enter()

    # ---- achievements / toasts ---------------------------------------------------------------
    def toast(self, title, text="", icon="star", color=gfx.GOLD):
        self.toasts.append({"title": title, "text": text, "icon": icon, "color": color, "t": 0})

    def unlock(self, achievement_id):
        if self.save.unlock(achievement_id):
            self.toast(T("ach.unlocked"), T("ach.%s.name" % achievement_id), "star", gfx.GOLD)
            self.audio.play("achievement")
            self.save.save()
            return True
        return False

    def apply_settings(self):
        self.audio.set_volumes(self.settings.sfx, self.settings.music)
        self.settings.save()

    # ---- main loop -----------------------------------------------------------------------------
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                return
            if e.key == pygame.K_F3:
                self.settings.show_fps = not self.settings.show_fps
                return
            if e.key == pygame.K_F12:
                self.screenshot()
                return
            if e.key == pygame.K_m and not getattr(self.scene, "captures_text", False):
                self.settings.music = 0.0 if self.settings.music > 0 else 0.6
                self.apply_settings()
                return
        if self._fade_dir != 0:
            return                      # ignore input while fading
        if self.scene is not None:
            self.scene.event(e)

    def update(self):
        self.frame_no += 1
        if self._fade_dir == 1:
            self._fade = min(1.0, self._fade + 0.11)
            if self._fade >= 1.0:
                self._switch(self._pending)
                self._pending = None
                self._fade_dir = -1
        elif self._fade_dir == -1:
            self._fade = max(0.0, self._fade - 0.09)
            if self._fade <= 0.0:
                self._fade_dir = 0
        if self.scene is not None:
            self.scene.update()
        for t in self.toasts[:]:
            t["t"] += 1
            if t["t"] > 260:
                self.toasts.remove(t)

    def draw(self):
        surf = self.screen
        if self.scene is not None:
            self.scene.draw(surf)
        if self.settings.crt:
            surf.blit(gfx.crt_overlay(), (0, 0))
        self.draw_toasts(surf)
        if self._fade > 0:
            self._black.set_alpha(int(self._fade * 255))
            surf.blit(self._black, (0, 0))
        if self.settings.show_fps:
            gfx.draw_text(surf, "%d FPS" % round(self._fps), (W - 10, H - 10), "mono", 16, gfx.LIME, "bottomright", shadow=True)

    def draw_toasts(self, surf):
        y = 14
        for t in self.toasts:
            k = t["t"]
            slide = min(1.0, k / 12) if k < 230 else max(0.0, (260 - k) / 30)
            w, h = 340, 64
            x = W - (w + 16) * slide + 0
            gfx.panel(surf, (x, y, w, h), t["color"], fill=(8, 12, 24, 235), border=2, cut=10)
            gfx.draw_icon(surf, t["icon"], x + 34, y + h // 2, 15, t["color"])
            gfx.draw_text(surf, t["title"], (x + 64, y + 12), "display", 15, t["color"])
            gfx.draw_text(surf, t["text"], (x + 64, y + 36), "mono", 18, gfx.WHITE)
            y += h + 8

    def step(self, dt=STEP):
        """Advance exactly one update + one draw (used by tests and tools)."""
        for e in pygame.event.get():
            self.handle_event(e)
        self.update()
        self.draw()

    def run(self):
        _fix_std_streams()
        self._last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            dt = min(0.1, now - self._last)
            self._last = now
            self._acc += dt
            for e in pygame.event.get():
                self.handle_event(e)
            steps = 0
            while self._acc >= STEP and steps < 4:
                self.update()
                self._acc -= STEP
                steps += 1
            if steps == 4:
                self._acc = 0.0
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            if dt > 0:
                self._fps = self._fps * 0.9 + (1.0 / dt) * 0.1
        self.shutdown()

    def shutdown(self):
        self.settings.save()
        self.save.save()
        pygame.quit()

    def screenshot(self):
        folder = user_data_dir() / "screenshots"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / time.strftime("voidloop_%Y%m%d_%H%M%S.png")
            pygame.image.save(self.screen, str(path))
            self.toast("SCREENSHOT", path.name, "check", gfx.CYAN)
        except (OSError, pygame.error):
            pass


# ---------------------------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="voidloop", description="VoidLoop - neon cyber-survival arcade shooter")
    p.add_argument("--version", action="version", version="VoidLoop %s" % __version__)
    p.add_argument("--lang", choices=LANG_CODES, help="interface language")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fullscreen", action="store_true", help="start in fullscreen")
    mode.add_argument("--windowed", action="store_true", help="start in a window")
    p.add_argument("--no-audio", action="store_true", help="disable all sound")
    p.add_argument("--selftest", action="store_true", help="headless self-check used by the build pipeline")
    p.add_argument("--report", metavar="FILE", help="write the self-test report to FILE")
    args, _unknown = p.parse_known_args(argv)                 # tolerate the old positional launcher arguments
    return args


def show_crash(app, details, log_path):
    """A last-resort error screen (instead of a window that silently vanishes)."""
    try:
        surf = app.screen
        lines = ["VOID LOOP crashed", "", "Details were saved to:", str(log_path), "", "Press any key to exit."]
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
            surf.fill((20, 0, 8))
            y = 200
            for i, line in enumerate(lines):
                gfx.draw_text(surf, line, (W // 2, y), "display" if i == 0 else "mono", 34 if i == 0 else 20,
                              gfx.RED if i == 0 else gfx.WHITE, "center")
                y += 50 if i == 0 else 30
            pygame.display.flip()
            time.sleep(0.03)
    except Exception:
        pass


def main(argv=None):
    _fix_std_streams()
    args = parse_args(argv)
    if args.selftest:
        from .selftest import run as run_selftest
        return run_selftest(args.report)
    app = None
    try:
        app = App(lang=args.lang, fullscreen=True if args.fullscreen else False if args.windowed else None, no_audio=args.no_audio)
        from .scenes.title import BootScene
        app.go(BootScene(app), fade=False)
        app.run()
        return 0
    except SystemExit:
        raise
    except BaseException:
        details = traceback.format_exc()
        log = user_data_dir() / "crash.log"
        try:
            log.write_text("VoidLoop %s\n\n%s" % (__version__, details), encoding="utf-8")
        except OSError:
            pass
        if app is not None:
            show_crash(app, details, log)
        try:
            pygame.quit()
        except Exception:
            pass
        return 1
