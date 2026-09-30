"""Play the real game through its real scenes, headlessly, with the bot at the controls.

    python tools/autoplay.py [--start-stage N] [--stages N] [--lang xx] [--mode MODE] [--cheat]

Used by the test-suite (integration) and handy for quickly checking a whole run.
"""
import argparse
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def key(pygame, k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def drive(app, bot, pygame, cheat):
    """One decision of the autopilot for the current scene. Returns the scene class name."""
    sc = app.scene
    name = type(sc).__name__
    if app._fade_dir != 0:
        return name
    if name == "PlayScene":
        if not getattr(sc, "_auto", False):
            sc._auto = True
            sc.read_inputs = lambda: bot.inputs(sc.world)
        if cheat:
            for p in sc.world.players:
                p.hp = p.max_hp
    elif name in ("DialogueScene", "SectorCard", "ResultsScene", "CreditsScene"):
        if sc.t > 40:
            key(pygame, pygame.K_SPACE)
    elif name == "ShopScene":
        if sc.t > 10:
            sc.menu.sel = len(sc.menu.items) - 1
            key(pygame, pygame.K_RETURN)
    elif name == "GameOverScene":
        if sc.talking:
            key(pygame, pygame.K_SPACE)
        elif sc.t > 20:
            sc.menu.sel = 0
            key(pygame, pygame.K_RETURN)
    elif name == "SummaryScene":
        sc.menu.sel = 1
        key(pygame, pygame.K_RETURN)
    elif name == "EndingScene":
        if sc.t > 20:
            key(pygame, pygame.K_RETURN)
    return name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-stage", type=int, default=0)
    ap.add_argument("--stages", type=int, default=24, help="how many story stages to play")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--cheat", action="store_true", help="keep the player alive")
    ap.add_argument("--max-frames", type=int, default=400000)
    ap.add_argument("--difficulty", default="NORMAL")
    args = ap.parse_args(argv)
    os.environ.setdefault("VOIDLOOP_HOME", tempfile.mkdtemp(prefix="voidloop_auto_"))

    import pygame
    from VoidLoop.app import App
    from VoidLoop.bot import Bot
    from VoidLoop.run import Run
    from VoidLoop.weapons import Loadout

    app = App(headless=True, lang=args.lang, no_audio=True)
    story = app.save.start_story(args.difficulty, 1)
    story["stage"] = args.start_stage
    if args.start_stage > 0:
        story["seen"] = ["prologue"]
        story["weapons"] = ["BLASTER", "TWIN", "SPREAD"] if args.start_stage > 8 else ["BLASTER"]
        story["hp_bonus"] = args.start_stage // 8
        story["coins"] = 200
    run = Run(app, "STORY", args.difficulty, 1, story)
    bot = Bot(0.85)
    run.begin()
    visited = {}
    t0 = time.time()
    last_stage = run.index
    stages_done = 0
    for frame in range(args.max_frames):
        name = drive(app, bot, pygame, args.cheat)
        visited[name] = visited.get(name, 0) + 1
        app.step()
        if run.index != last_stage:
            stages_done += run.index - last_stage if run.index > last_stage else 0
            last_stage = run.index
            print("  stage cleared -> now %d  (frame %d, %.0fs)" % (run.index, frame, time.time() - t0))
        if stages_done >= args.stages or name == "MainMenu" or (name == "CreditsScene" and frame > 10):
            if name == "MainMenu" or stages_done >= args.stages:
                break
    print("scenes seen:", ", ".join("%s=%d" % kv for kv in sorted(visited.items())))
    print("reached stage index %d, finished=%s, coins=%d, elapsed %.1fs" % (run.index, run.finished, run.loadout.coins, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
