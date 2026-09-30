"""Drive the real application (menus, scenes, transitions) with simulated key presses."""
import pygame
import pytest

from VoidLoop import campaign
from VoidLoop.i18n import T, i18n
from VoidLoop.run import Run
from VoidLoop.scenes import title, story, play, results, shop
from VoidLoop.settings import Settings
from VoidLoop.weapons import Loadout


def press(app, key, frames=1):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))
    for _ in range(frames):
        app.step()


def settle(app, frames=40):
    for _ in range(frames):
        app.step()


def new_story_run(app, stage=0, players=1):
    story_save = app.save.start_story("NORMAL", players)
    story_save["stage"] = stage
    if stage:
        story_save["seen"] = ["prologue"]
    return Run(app, "STORY", "NORMAL", players, story_save)


def test_boot_leads_to_main_menu(app):
    app.go(title.BootScene(app), fade=False)
    for _ in range(400):
        app.step()
        if isinstance(app.scene, title.MainMenu):
            break
    assert isinstance(app.scene, title.MainMenu)


def test_main_menu_new_game_flow(app):
    app.save.clear_story()
    app.go(title.MainMenu(app), fade=False)
    settle(app, 5)
    labels = [it.text() for it in app.scene.menu.items]
    assert T("menu.new_game") in labels and T("menu.continue") not in labels
    press(app, pygame.K_RETURN)               # NEW GAME (first entry)
    settle(app, 40)
    assert isinstance(app.scene, title.SetupScene)
    for _ in range(3):
        press(app, pygame.K_DOWN)
    press(app, pygame.K_RETURN)               # START
    settle(app, 40)
    assert isinstance(app.scene, story.DialogueScene), type(app.scene)
    assert app.save.has_story()
    for _ in range(60):                       # skip the whole prologue
        press(app, pygame.K_ESCAPE, 30)
        if isinstance(app.scene, play.PlayScene):
            break
    assert isinstance(app.scene, (story.SectorCard, story.DialogueScene, play.PlayScene))


def test_setup_scene_changes_settings(app):
    s = title.SetupScene(app, "ENDLESS")
    app._switch(s)
    press(app, pygame.K_RIGHT)                # difficulty -> next
    assert app.settings.difficulty == "HARD"
    press(app, pygame.K_DOWN)
    press(app, pygame.K_RIGHT)
    assert app.settings.players == 2
    press(app, pygame.K_DOWN)
    press(app, pygame.K_LEFT)
    assert app.settings.ship_color != "Neon Green"
    app.settings.difficulty, app.settings.players, app.settings.ship_color = "NORMAL", 1, "Neon Green"


def test_options_change_language_live_and_persist(app):
    s = title.OptionsScene(app)
    app._switch(s)
    langs = ["it", "en", "es", "fr"]
    start = app.settings.language
    press(app, pygame.K_RIGHT)
    assert app.settings.language == langs[(langs.index(start) + 1) % 4]
    assert i18n.lang == app.settings.language
    app.step()                                # draws with the new language
    press(app, pygame.K_ESCAPE)
    settle(app, 40)
    assert isinstance(app.scene, title.MainMenu)
    assert Settings.load().language == app.settings.language
    app.settings.language = "en"
    i18n.set_language("en")


def test_options_volume_slider_and_toggles(app):
    s = title.OptionsScene(app)
    app._switch(s)
    press(app, pygame.K_DOWN)
    before = app.settings.music
    press(app, pygame.K_LEFT)
    assert app.settings.music < before
    for _ in range(3):
        press(app, pygame.K_DOWN)
    crt = app.settings.crt
    press(app, pygame.K_RETURN)
    assert app.settings.crt != crt
    app.settings.crt = True


def test_mouse_hover_and_click_on_menu(app):
    app.go(title.MainMenu(app), fade=False)
    settle(app, 3)
    menu = app.scene.menu
    target = menu.items[2]
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=target.rect.center, rel=(0, 0), buttons=(0, 0, 0)))
    app.step()
    assert menu.sel == 2
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=target.rect.center, button=1))
    settle(app, 40)
    assert not isinstance(app.scene, title.MainMenu)


def test_continue_appears_with_a_save_and_resumes(app):
    run = new_story_run(app, stage=5)
    run.save_story()
    app.go(title.MainMenu(app), fade=False)
    settle(app, 3)
    assert app.scene.menu.items[0].key == "continue"
    press(app, pygame.K_RETURN)
    settle(app, 50)
    assert isinstance(app.scene, play.PlayScene)
    assert app.scene.spec.index == 5


def test_confirm_dialog_before_erasing_a_save(app):
    run = new_story_run(app, stage=3)
    run.save_story()
    app.go(title.MainMenu(app), fade=False)
    settle(app, 3)
    keys = [it.key for it in app.scene.menu.items]
    app.scene.menu.sel = keys.index("new")
    press(app, pygame.K_RETURN)
    settle(app, 40)
    assert isinstance(app.scene, title.ConfirmScene)
    press(app, pygame.K_ESCAPE)               # "no"
    settle(app, 40)
    assert isinstance(app.scene, title.MainMenu) and app.save.story["stage"] == 3


def test_pause_menu_and_exit(app):
    run = new_story_run(app, stage=1)
    scene = play.PlayScene(app, run, run.spec())
    app._switch(scene)
    settle(app, 10)
    press(app, pygame.K_ESCAPE)
    assert scene.paused
    t = scene.world.time
    settle(app, 20)
    assert scene.world.time == t, "the world must freeze while paused"
    press(app, pygame.K_ESCAPE)
    assert not scene.paused
    press(app, pygame.K_ESCAPE)
    keys = [it.key for it in scene.menu.items]
    assert keys == ["resume", "save", "menu"]
    scene.menu.sel = 2
    press(app, pygame.K_RETURN)
    settle(app, 40)
    assert isinstance(app.scene, title.MainMenu)


def test_every_mode_starts_and_plays(app):
    for mode in ("ENDLESS", "TIME_ATTACK", "BOSS_RUSH", "HORDE"):
        app.settings.players = 1
        s = title.SetupScene(app, mode)
        app._switch(s)
        s.start()
        settle(app, 40)
        assert isinstance(app.scene, play.PlayScene), mode
        settle(app, 120)
        assert app.scene.world.spec.mode == mode


def test_story_death_shows_game_over_and_retry_replays_the_stage(app):
    run = new_story_run(app, stage=2)
    scene = play.PlayScene(app, run, run.spec())
    app._switch(scene)
    p = scene.world.players[0]
    p.hp = 0
    p.alive = False
    for _ in range(200):
        app.step()
        if isinstance(app.scene, results.GameOverScene):
            break
    assert isinstance(app.scene, results.GameOverScene)
    over = app.scene
    for _ in range(20):
        press(app, pygame.K_SPACE)
    assert not over.talking
    press(app, pygame.K_RETURN)               # RETRY
    settle(app, 50)
    assert isinstance(app.scene, play.PlayScene) and app.scene.spec.index == 2
    assert app.scene.world is not scene.world


def test_endless_death_records_the_high_score(app):
    run = Run(app, "ENDLESS", "NORMAL", 1)
    scene = play.PlayScene(app, run, run.spec())
    app._switch(scene)
    w = scene.world
    w.score = 4321
    w.players[0].hp = 0
    w.players[0].alive = False
    for _ in range(200):
        app.step()
        if isinstance(app.scene, results.SummaryScene):
            break
    assert isinstance(app.scene, results.SummaryScene)
    assert app.save.best("ENDLESS", "NORMAL")["score"] >= 4321
    assert run.record


def test_stage_clear_leads_to_results_then_shop_then_next_stage(app):
    run = new_story_run(app, stage=0)
    scene = play.PlayScene(app, run, run.spec())
    app._switch(scene)
    w = scene.world
    w.rules.begin_win(1)
    seen = []
    for _ in range(600):
        name = type(app.scene).__name__
        if not seen or seen[-1] != name:
            seen.append(name)
        if name in ("ResultsScene", "DialogueScene", "SectorCard", "ShopScene"):
            press(app, pygame.K_SPACE)
            if name == "ShopScene":
                app.scene.menu.sel = len(app.scene.menu.items) - 1
                press(app, pygame.K_RETURN)
        else:
            app.step()
        if isinstance(app.scene, play.PlayScene) and app.scene is not scene:
            seen.append("PlayScene")
            break
    assert seen[:3] == ["PlayScene", "ResultsScene", "DialogueScene"], seen     # weapon unlock talk after stage 1
    assert "ShopScene" in seen and seen[-1] == "PlayScene"
    assert "BLASTER" in run.loadout.weapons and run.index == 1
    assert app.save.story["stage"] == 1


def test_shop_purchase_updates_coins_and_save(app):
    run = new_story_run(app, stage=3)
    run.loadout.coins = 100
    sh = shop.ShopScene(app, run, lambda: None)
    app._switch(sh)
    press(app, pygame.K_RETURN)               # first item: Twin Shot
    assert "TWIN" in run.loadout.weapons and run.loadout.coins < 100
    coins = run.loadout.coins
    press(app, pygame.K_RETURN)               # buying it again fails
    assert run.loadout.coins == coins
    assert app.save.story["weapons"].count("TWIN") == 1


def test_achievement_toast_and_persistence(app):
    app.save.data["achievements"] = []
    assert app.unlock("first_blood")
    assert not app.unlock("first_blood")
    assert app.toasts
    for _ in range(300):
        app.step()
    assert not app.toasts


def test_dialogue_typewriter_advances_and_finishes(app):
    lines = i18n.scene("weapon_unlock")
    done = []
    sc = story.DialogueScene(app, lines, lambda: done.append(1), sector=0)
    app._switch(sc)
    settle(app, 5)
    assert sc.box.chars > 0 and not sc.box.finished_typing()
    press(app, pygame.K_SPACE)                # completes the line
    assert sc.box.finished_typing() and sc.box.i == 0
    for _ in range(2 * len(lines) + 2):        # two presses per line: finish typing, then next
        press(app, pygame.K_SPACE)
    assert done == [1]


def test_screenshot_and_fullscreen_toggle_do_not_crash(app):
    app.go(title.MainMenu(app), fade=False)
    settle(app, 3)
    app.screenshot()
    app.toggle_fullscreen()
    app.toggle_fullscreen()
    app.settings.show_fps = True
    settle(app, 3)
    app.settings.show_fps = False


@pytest.mark.parametrize("lang", ["it", "en", "es", "fr"])
def test_every_scene_draws_in_every_language(app, lang):
    app.settings.language = lang
    i18n.set_language(lang)
    run = new_story_run(app, stage=1)
    world = play.PlayScene(app, run, campaign.story_spec(3)).world
    world.rules.begin_win(1)
    for _ in range(80):
        world.update({})
    scenes = [title.MainMenu(app), title.ModeSelectScene(app), title.SetupScene(app, "STORY"), title.OptionsScene(app),
              title.AchievementsScene(app), title.HelpScene(app), story.SectorCard(app, 4, lambda: None),
              story.DialogueScene(app, i18n.scene("s5_boss_intro"), lambda: None, sector=4, glitch=0.2),
              shop.ShopScene(app, run, lambda: None), results.ResultsScene(app, run, world, lambda: None),
              results.GameOverScene(app, run, world), story.EndingScene(app, run), story.CreditsScene(app, run, "keep"),
              play.PlayScene(app, run, campaign.story_spec(3))]
    for sc in scenes:
        app._switch(sc)
        for _ in range(4):
            app.step()
    app.settings.language = "en"
    i18n.set_language("en")
