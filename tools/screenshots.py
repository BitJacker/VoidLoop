"""Render every screen of the game headlessly to PNG files (used for docs and visual checks).

    python tools/screenshots.py [output_dir] [language]
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("VOIDLOOP_HOME", tempfile.mkdtemp(prefix="voidloop_shots_"))

import pygame  # noqa: E402

from VoidLoop.app import App  # noqa: E402
from VoidLoop import campaign  # noqa: E402
from VoidLoop.bot import Bot  # noqa: E402
from VoidLoop.i18n import i18n  # noqa: E402
from VoidLoop.run import Run  # noqa: E402
from VoidLoop.scenes import title, story, play, results, shop  # noqa: E402
from VoidLoop.weapons import Loadout  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "screenshots")
LANG = sys.argv[2] if len(sys.argv) > 2 else "en"
os.makedirs(OUT, exist_ok=True)

app = App(headless=True, lang=LANG, no_audio=True)
app.settings.crt = True


def shot(name, scene, frames=30, before=None):
    app._switch(scene)
    for i in range(frames):
        if before:
            before(scene, i)
        app.step()
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))
    print("saved", name)


def play_shot(name, stage_index, frames, players=1, difficulty="NORMAL", weapons=("BLASTER", "TWIN")):
    story_save = app.save.start_story(difficulty, players)
    story_save["stage"] = stage_index
    run = Run(app, "STORY", difficulty, players, story_save)
    run.loadout = Loadout(list(weapons))
    scene = play.PlayScene(app, run, run.spec())
    scene.banner_t = 0
    scene.hint_t = 0
    bot = Bot(0.9)
    w = scene.world
    for _ in range(frames):
        w.update(bot.inputs(w))
        w.pop_events()
        for p in w.players:
            p.hp = max(p.hp, p.max_hp - 1)
            p.alive = True
    app._switch(scene)
    scene.hint_t = 0
    scene.banner_t = 0
    scene.bark = play.Bark(i18n.pick_line("chatter_s%d" % (w.sector + 1)))
    scene.bark.t = 30
    for _ in range(3):
        scene.update = lambda: None            # freeze the frame; only draw
        app.step()
    scene.bark.t = 30
    app.step()
    pygame.image.save(app.screen, os.path.join(OUT, name + ".png"))
    print("saved", name)
    return run, scene


shot("01_title", title.MainMenu(app), 120)
shot("02_setup", title.SetupScene(app, "STORY"), 20)
shot("03_modes", title.ModeSelectScene(app), 20)
shot("04_options", title.OptionsScene(app), 20)
app.save.unlock("first_blood"); app.save.unlock("boss_slayer"); app.save.unlock("combo_master")
shot("05_achievements", title.AchievementsScene(app), 20)
shot("06_help", title.HelpScene(app), 20)
lines = i18n.scene("s5_mid")
shot("07_dialogue", story.DialogueScene(app, lines, lambda: None, sector=4, glitch=0.16), 70)
shot("08_sector_card", story.SectorCard(app, 2, lambda: None), 130)
for name, idx, fr in (("10_play_s1", 2, 500), ("11_play_s2", 6, 700), ("12_play_s3", 10, 700), ("13_play_s4", 14, 700),
                      ("14_play_s5", 18, 700), ("15_play_s6", 22, 700), ("16_boss_sentinel", 3, 500), ("17_boss_weaver", 7, 900),
                      ("18_boss_inferno", 11, 700), ("19_boss_cryo", 15, 800), ("20_boss_glitch", 19, 800), ("21_boss_origin", 23, 900)):
    play_shot(name, idx, fr)
run, sc = play_shot("22_coop", 10, 500, players=2)
# results / shop / game over / summary / ending / credits
story_save = app.save.start_story("NORMAL", 1)
run = Run(app, "STORY", "NORMAL", 1, story_save)
run.loadout = Loadout(["BLASTER"]); run.loadout.coins = 87
w = play.PlayScene(app, run, campaign.story_spec(0)).world
bot = Bot(0.9)
for _ in range(3000):
    w.update(bot.inputs(w)); w.pop_events()
    if w.state != "playing":
        break
shot("30_results", results.ResultsScene(app, run, w, lambda: None), 110)
shot("31_shop", shop.ShopScene(app, run, lambda: None), 30)
shot("32_gameover", results.GameOverScene(app, run, w), 100)
run2 = Run(app, "ENDLESS", "NORMAL", 1)
run2.score, run2.kills, run2.frames, run2.best_combo, run2.record = 48250, 132, 60 * 251, 27, True
w2 = play.PlayScene(app, run2, campaign.endless_spec(1)).world
shot("33_summary", results.SummaryScene(app, run2, w2), 60)
shot("34_ending", story.EndingScene(app, run), 30)
shot("35_credits", story.CreditsScene(app, run, "break"), 200)
print("done ->", OUT)
