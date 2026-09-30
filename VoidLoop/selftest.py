"""Headless self-check. ``voidloop --selftest`` runs it, also from a frozen (PyInstaller) build.

It exercises the resources that packaging can silently lose (fonts, language files, ...) and
plays a few seconds of every mode, so a broken installer is caught before anyone downloads it.
"""
import os
import sys
import tempfile
import time
import traceback


def run(report_path=None):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["VOIDLOOP_HOME"] = tempfile.mkdtemp(prefix="voidloop_selftest_")
    from . import paths
    paths.reset_for_tests()

    lines = []
    failed = []

    def check(name, fn):
        t0 = time.time()
        try:
            detail = fn()
            lines.append("OK    %-34s %s (%.2fs)" % (name, detail or "", time.time() - t0))
        except Exception:
            failed.append(name)
            lines.append("FAIL  %s\n%s" % (name, traceback.format_exc()))

    import pygame
    from . import __version__

    lines.append("VoidLoop %s selftest - python %s, pygame %s, frozen=%s" % (
        __version__, sys.version.split()[0], pygame.version.ver, paths.is_frozen()))

    # ---- resources ---------------------------------------------------------------------
    def resources():
        missing = []
        for rel in ("fonts/Orbitron-Black.ttf", "fonts/Orbitron-Bold.ttf", "fonts/ShareTechMono-Regular.ttf"):
            if not paths.asset_path(*rel.split("/")).exists():
                missing.append(rel)
        for code in ("it", "en", "es", "fr"):
            for prefix in ("ui", "dialogues"):
                if not (paths.lang_dir() / ("%s_%s.json" % (prefix, code))).exists():
                    missing.append("lang/%s_%s.json" % (prefix, code))
        if missing:
            raise RuntimeError("missing resources: %s" % ", ".join(missing))
        return "fonts + 4 languages present"

    check("resources", resources)

    from .app import App
    holder = {}

    def start_app():
        holder["app"] = App(headless=True, lang="en")
        pygame.font.init()
        return "window %dx%d" % holder["app"].screen.get_size()

    check("window", start_app)
    app = holder.get("app")
    if app is None:
        return _finish(lines, failed, report_path)

    from . import gfx

    def fonts():
        for kind, size in (("title", 40), ("display", 22), ("mono", 18)):
            f = gfx.font(kind, size)
            img = f.render("Àèìòù ñ ç œ", True, (255, 255, 255))
            if img.get_width() < 10:
                raise RuntimeError("font %s renders nothing" % kind)
        return "3 fonts"

    check("fonts", fonts)

    def languages():
        from .i18n import I18n
        from .settings import LANG_CODES
        for code in LANG_CODES:
            i = I18n(code)
            if not i.tl("tips") or not i.scene("prologue") or i.t("menu.new_game") == "menu.new_game":
                raise RuntimeError("language %s is incomplete" % code)
        return ", ".join(LANG_CODES)

    check("languages", languages)

    def audio():
        from .audio import Audio
        a = Audio(0.5, 0.5)
        if not a.ok:
            return "no audio device (running silent)"
        a.load_sfx()
        from . import sounds
        a.preload_music("boss")
        return "%d effects, boss track" % len(a.sfx)

    check("audio synthesis", audio)

    def worlds():
        from . import campaign, settings
        from .bot import Bot
        from .weapons import Loadout
        from .world import World
        specs = [campaign.story_spec(i) for i in (0, 3, 9, 13, 18, 23)] + [campaign.endless_spec(1), campaign.time_attack_spec(1),
                                                                            campaign.boss_rush_spec(2), campaign.horde_spec(1)]
        for spec in specs:
            w = World(spec, settings.DIFFICULTIES["NORMAL"], Loadout(["BLASTER"]), [settings.SHIP_COLORS["Neon Green"]], seed=5)
            bot = Bot(0.8)
            for _ in range(90):
                w.update(bot.inputs(w))
                w.pop_events()
            w.draw(app.screen)
        return "%d stages simulated and drawn" % len(specs)

    check("game simulation", worlds)

    def scenes():
        from .scenes import title, story, results, shop
        from .i18n import i18n
        from .run import Run
        from . import campaign
        from .weapons import Loadout
        n = 0
        seq = [title.BootScene(app), title.MainMenu(app), title.ModeSelectScene(app), title.SetupScene(app, "STORY"), title.OptionsScene(app),
               title.AchievementsScene(app), title.HelpScene(app), story.SectorCard(app, 3, lambda: None),
               story.DialogueScene(app, i18n.scene("prologue"), lambda: None)]
        story_save = app.save.start_story("NORMAL", 1)
        run = Run(app, "STORY", "NORMAL", 1, story_save)
        seq.append(shop.ShopScene(app, run, lambda: None))
        from .scenes.play import PlayScene
        seq.append(PlayScene(app, run, campaign.story_spec(0)))
        for sc in seq:
            app._switch(sc)
            for _ in range(3):
                app.step()
            n += 1
        return "%d scenes drawn" % n

    check("menus and scenes", scenes)

    def saves():
        from .save import SaveData
        s = SaveData.load()
        s.start_story("HARD", 2)
        s.unlock("first_blood")
        s.submit_score("ENDLESS", "NORMAL", 1234)
        if not s.save():
            raise RuntimeError("cannot write the save file")
        again = SaveData.load()
        if not again.has_story() or not again.has("first_blood"):
            raise RuntimeError("save round-trip failed")
        return str(paths.user_data_dir())

    check("save/load", saves)
    return _finish(lines, failed, report_path)


def _finish(lines, failed, report_path):
    lines.append("RESULT: %s" % ("PASS" if not failed else "FAIL (%s)" % ", ".join(failed)))
    text = "\n".join(lines) + "\n"
    if report_path:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:
        pass
    return 0 if not failed else 1
