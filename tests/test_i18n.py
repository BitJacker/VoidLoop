"""The four languages must stay in sync: same keys, same placeholders, characters the fonts can draw."""
import json
import re
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from VoidLoop.achievements import ACHIEVEMENT_IDS
from VoidLoop.i18n import I18n, _SPEAKER_RE
from VoidLoop.paths import lang_dir, asset_path
from VoidLoop.settings import LANG_CODES, DIFFICULTY_ORDER, MODES
from VoidLoop.weapons import SHOP_ITEMS
from VoidLoop.bosses import BOSSES
from VoidLoop.biomes import BIOME_IDS
from VoidLoop.world import POWERUPS

PLACEHOLDER = re.compile(r"\{(\w+)\}")


def load(name):
    with open(lang_dir() / name, encoding="utf-8") as f:
        return json.load(f)


UI = {c: load("ui_%s.json" % c) for c in LANG_CODES}
DLG = {c: load("dialogues_%s.json" % c) for c in LANG_CODES}


def required_ui_keys():
    keys = ["_language", "boot.loading", "tips", "help.controls", "help.controls2", "help.text", "credits.lines"]
    keys += ["ach.unlocked", "ach.progress", "ach.stats"]
    keys += ["ach.%s.%s" % (a, f) for a in ACHIEVEMENT_IDS for f in ("name", "desc")]
    keys += ["boss.%s" % b for b in BOSSES]
    keys += ["sector.label"] + ["sector.%s.%s" % (b, f) for b in BIOME_IDS for f in ("name", "sub")]
    keys += ["diff.%s" % d.lower() for d in DIFFICULTY_ORDER]
    keys += ["mode.%s" % m.lower() for m in MODES] + ["mode.%s.desc" % m.lower() for m in MODES] + ["mode.best", "mode.no_score"]
    keys += ["power.%s" % p.lower() for p in POWERUPS]
    keys += ["shop.%s.%s" % (i["id"], f) for i in SHOP_ITEMS for f in ("name", "desc")]
    keys += ["credits.ending_break", "credits.ending_keep", "credits.loop_break", "credits.loop_keep"]
    for group, names in {
        "menu": "tagline continue new_game modes options achievements help quit back save_info loop fullscreen mute",
        "hint": "menu back", "confirm": "new_game yes no",
        "setup": "subtitle difficulty players one_player two_players ship start hp speed cost score",
        "opt": "language music sfx fullscreen crt shake fps",
        "help": "controls_p1 controls_p2 how_title",
        "hud": "sync combo score pulse_ready boss_stage boss_n round level wave phase invulnerable weapon_tier weapon_up timeout warning hint_move hint_weapon",
        "pause": "title continue save exit saved", "dialog": "skip",
        "results": "title time kills combo hits coins score rank continue",
        "over": "title stage retry menu tip",
        "summary": "title timeup again score level bosses rounds record best",
        "shop": "title subtitle continue owned weapon max maxed no_coins bought now loadout dash_label weapons_label stat_rate_label stat_dmg stat_rate stat_shots",
        "ending": "title prompt break keep",
        "credits": "stats kills deaths time thanks",
    }.items():
        keys += ["%s.%s" % (group, n) for n in names.split()]
    return keys


def required_dialogue_keys():
    keys = ["_speakers", "prologue", "weapon_unlock", "ending_break", "ending_keep", "game_over", "bark_first_kill", "bark_combo",
            "bark_low_hp", "bark_boss_phase", "bark_boss_dead", "bark_stage_clear"]
    for n in range(1, 7):
        keys += ["s%d_%s" % (n, k) for k in ("intro", "mid", "boss_intro", "boss_defeat")] + ["chatter_s%d" % n]
    keys += ["bark_boss_%s" % b for b in BOSSES] + ["bark_boss_phase_%s" % b for b in BOSSES]
    keys += ["bark_power_%s" % p.lower() for p in POWERUPS if p != "BOMB"]
    return keys


@pytest.mark.parametrize("lang", LANG_CODES)
def test_ui_has_every_required_key(lang):
    missing = [k for k in required_ui_keys() if k not in UI[lang]]
    assert not missing, "%s is missing UI keys: %s" % (lang, missing)


@pytest.mark.parametrize("lang", LANG_CODES)
def test_dialogues_have_every_required_key(lang):
    missing = [k for k in required_dialogue_keys() if k not in DLG[lang]]
    assert not missing, "%s is missing dialogue keys: %s" % (lang, missing)


@pytest.mark.parametrize("lang", [c for c in LANG_CODES if c != "en"])
def test_no_extra_or_missing_keys_vs_english(lang):
    assert set(UI[lang]) == set(UI["en"]), sorted(set(UI[lang]) ^ set(UI["en"]))
    assert set(DLG[lang]) == set(DLG["en"]), sorted(set(DLG[lang]) ^ set(DLG["en"]))


@pytest.mark.parametrize("lang", [c for c in LANG_CODES if c != "en"])
def test_placeholders_match_english(lang):
    for key, en in UI["en"].items():
        if isinstance(en, str):
            assert set(PLACEHOLDER.findall(en)) == set(PLACEHOLDER.findall(UI[lang][key])), (lang, key)


@pytest.mark.parametrize("lang", [c for c in LANG_CODES if c != "en"])
def test_dialogue_structure_matches_english(lang):
    for key, en in DLG["en"].items():
        other = DLG[lang][key]
        assert type(other) is type(en), (lang, key)
        if isinstance(en, list) and key not in ("game_over",) and not key.startswith(("bark_", "chatter_")):
            assert len(other) == len(en), "%s/%s: %d lines vs %d in English" % (lang, key, len(other), len(en))
        if key == "game_over":
            assert len(other) == len(en)
            assert all(len(a) == len(b) for a, b in zip(en, other))
        if key.startswith("bark_boss_") or key.startswith("bark_power_"):
            assert len(other) == len(en), (lang, key)


@pytest.mark.parametrize("lang", LANG_CODES)
def test_every_dialogue_line_has_a_known_speaker(lang):
    speakers = DLG[lang]["_speakers"]
    assert set(speakers.values()) >= {"system", "echo", "void"}
    i18n = I18n(lang)

    def lines_of(value):
        for item in value:
            if isinstance(item, list):
                yield from lines_of(item)
            else:
                yield item

    for key, value in DLG[lang].items():
        if key == "_speakers":
            continue
        for raw in lines_of(value):
            m = _SPEAKER_RE.match(raw)
            assert m, "%s/%s: line without speaker tag: %r" % (lang, key, raw)
            assert m.group(1).strip() in speakers, "%s/%s: unknown speaker %r" % (lang, key, m.group(1))
            assert len(raw) <= 240, "%s/%s: line too long for the box (%d chars)" % (lang, key, len(raw))
    assert i18n.parse_line("ECHO: hi").text == "hi" if lang == "en" else True


MONO_ONLY = {"menu.save_info", "dialog.skip", "ach.stats", "hud.hint_move", "hud.hint_weapon", "hint.menu", "hint.back", "help.text", "help.controls",
             "help.controls2", "tips", "credits.lines", "credits.kills", "credits.deaths", "credits.time", "credits.loop_break",
             "credits.loop_keep", "credits.ending_break", "credits.ending_keep"}


def cmap(name):
    return TTFont(str(asset_path("fonts", name))).getBestCmap()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


@pytest.mark.parametrize("lang", LANG_CODES)
def test_fonts_can_draw_every_character(lang):
    mono = cmap("ShareTechMono-Regular.ttf")
    display = cmap("Orbitron-Bold.ttf")
    problems = []
    for key, value in UI[lang].items():
        table = mono if (key in MONO_ONLY or key.endswith(".desc") or key.startswith(("mode.best", "shop.stat", "shop.now", "power."))) else display
        if key.startswith("_"):
            continue
        for s in strings(value):
            for ch in s:
                if ch not in ("\n",) and ord(ch) not in table:
                    problems.append((key, ch))
    for key, value in DLG[lang].items():
        for s in strings(value):
            for ch in s:
                if ord(ch) not in mono:
                    problems.append((key, ch))
    assert not problems, "%s: characters missing from the fonts: %s" % (lang, sorted(set(problems))[:20])


def test_translations_are_not_copies_of_english():
    for lang in LANG_CODES:
        if lang == "en":
            continue
        same = [k for k, v in UI["en"].items() if isinstance(v, str) and len(v) > 24 and UI[lang][k] == v]
        assert len(same) < 3, (lang, same)


def test_fallback_to_english_and_key():
    i = I18n("it")
    assert i.t("menu.new_game") != "menu.new_game"
    assert i.t("definitely.missing.key") == "definitely.missing.key"
    i.set_language("xx")
    assert i.lang == "en"
    assert i.t("menu.quit") == "QUIT"


def test_speaker_parsing_and_style():
    i = I18n("en")
    line = i.parse_line("ECHO: You made it.")
    assert (line.speaker, line.style, line.text) == ("ECHO", "echo", "You made it.")
    assert i.parse_line("UNKNOWN: hi").style == "echo"
    plain = i.parse_line("Just a narration line: with a colon")
    assert plain.speaker is None and plain.style == "narrator"
    fr = I18n("fr").parse_line("SYSTÈME: Connexion perdue.")
    assert fr.speaker == "SYSTÈME" and fr.style == "system"


def test_pools_and_scenes():
    i = I18n("en")
    assert len(i.scene("prologue")) >= 6
    assert i.pick_scene("game_over")
    assert i.pick_line("chatter_s3").speaker
    assert i.pick_line("no_such_pool") is None
