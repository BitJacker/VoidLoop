"""End-to-end: let the autopilot play the real game through the real scenes."""
import pytest

from tools import autoplay


@pytest.mark.slow
def test_final_stage_ending_and_credits(screen):
    """Final boss -> results -> ending choice -> epilogue -> credits -> back at the title with a New Game+ save."""
    import pygame
    import os
    from VoidLoop.app import App
    from VoidLoop.bot import Bot
    from VoidLoop.run import Run
    from VoidLoop.scenes import title

    app = App(headless=True, lang="en", no_audio=True)
    story = app.save.start_story("NORMAL", 1)
    story["stage"] = 23
    story["seen"] = ["prologue"]
    story["weapons"] = ["BLASTER", "TWIN", "SPREAD"]
    run = Run(app, "STORY", "NORMAL", 1, story)
    bot = Bot(0.85)
    run.begin()
    seen = []
    for frame in range(60 * 60 * 6):
        name = autoplay.drive(app, bot, pygame, cheat=True)
        if not seen or seen[-1] != name:
            seen.append(name)
        app.step()
        if name == "MainMenu" and "CreditsScene" in seen:
            break
    assert "CreditsScene" in seen and "EndingScene" in seen, seen
    assert isinstance(app.scene, title.MainMenu)
    assert run.finished
    s = app.save.story
    assert s["loop"] == 2 and s["stage"] == 0, "the story rolls over into a New Game+ loop"
    assert app.save.has("loop_breaker") or app.save.has("loop_keeper")
    assert app.save.has("boss_slayer")


@pytest.mark.slow
def test_autoplay_first_stages_then_menu(screen):
    rc = autoplay.main(["--stages", "3", "--cheat", "--max-frames", "40000"])
    assert rc == 0
