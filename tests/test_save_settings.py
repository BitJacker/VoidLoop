import json

from VoidLoop.save import SaveData, STORY_STAGES
from VoidLoop.settings import Settings, DIFFICULTIES


def test_save_roundtrip(tmp_path):
    p = tmp_path / "save.json"
    s = SaveData(p)
    story = s.start_story("HARD", 2)
    story["stage"] = 7
    story["coins"] = 42
    story["weapons"] = ["BLASTER", "TWIN"]
    s.unlock("first_blood")
    s.add_stat("kills", 5)
    s.max_stat("best_combo", 12)
    assert s.submit_score("ENDLESS", "NORMAL", 1000)
    assert not s.submit_score("ENDLESS", "NORMAL", 900)
    assert s.save()
    t = SaveData.load(p)
    assert t.story["stage"] == 7 and t.story["coins"] == 42 and t.story["weapons"] == ["BLASTER", "TWIN"]
    assert t.has("first_blood") and t.stats["kills"] == 5 and t.stats["best_combo"] == 12
    assert t.best("ENDLESS", "NORMAL")["score"] == 1000


def test_unlock_only_once(tmp_path):
    s = SaveData(tmp_path / "s.json")
    assert s.unlock("a") is True
    assert s.unlock("a") is False


def test_corrupt_save_is_backed_up_and_ignored(tmp_path):
    p = tmp_path / "save.json"
    p.write_text("{ this is not json", encoding="utf-8")
    s = SaveData.load(p)
    assert not s.has_story()
    assert (tmp_path / "save.corrupt").exists()


def test_garbage_values_are_sanitised(tmp_path):
    p = tmp_path / "save.json"
    p.write_text(json.dumps({"story": {"stage": 9999, "coins": -5, "weapons": "nope"}, "achievements": [1, "ok"], "stats": {"kills": "x"}}))
    s = SaveData.load(p)
    assert s.story["stage"] == STORY_STAGES - 1
    assert s.story["coins"] == 0
    assert s.story["weapons"] == []
    assert s.data["achievements"] == ["ok"]
    assert s.stats["kills"] == 0


def test_legacy_v3_save_is_imported(tmp_path, monkeypatch):
    legacy = tmp_path / "old.json"
    legacy.write_text(json.dumps({"level": 6, "coins": 55, "achievements": ["boss_slayer"]}))
    monkeypatch.setattr("VoidLoop.save.legacy_save_path", lambda: legacy)
    s = SaveData.load(tmp_path / "does_not_exist.json")
    assert s.story["stage"] == 5 and s.story["coins"] == 55 and "BLASTER" in s.story["weapons"]
    assert s.has("boss_slayer")


def test_new_game_plus_carries_upgrades(tmp_path):
    s = SaveData(tmp_path / "s.json")
    first = s.start_story("NORMAL", 1)
    first.update(coins=99, hp_bonus=2, weapons=["BLASTER", "SPREAD"], weapon="SPREAD", stage=20)
    nxt = s.start_story("NORMAL", 1, loop=2, carry=first)
    assert nxt["loop"] == 2 and nxt["stage"] == 0 and nxt["coins"] == 99 and nxt["hp_bonus"] == 2
    assert nxt["weapons"] == ["BLASTER", "SPREAD"] and "prologue" in nxt["seen"]


def test_settings_validate_and_persist():
    s = Settings.load()
    s.language = "xx"
    s.difficulty = "IMPOSSIBLE"
    s.music = 5
    s.players = 7
    s.validate()
    assert s.language in ("it", "en", "es", "fr")
    assert s.difficulty == "NORMAL" and s.music == 1.0 and s.players == 1
    s.language, s.difficulty, s.crt = "fr", "HARD", False
    s.save()
    t = Settings.load()
    assert (t.language, t.difficulty, t.crt) == ("fr", "HARD", False)
    assert t.cfg == DIFFICULTIES["HARD"]


def test_settings_ignore_wrong_types():
    Settings.path().write_text(json.dumps({"music": "loud", "crt": "yes", "sfx": 1}))
    s = Settings.load()
    assert s.crt is True and s.sfx == 1.0 and s.music == 0.6
