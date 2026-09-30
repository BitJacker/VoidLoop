"""Persistent progress: story save, achievements, statistics and high scores."""
import copy
import json
import os

from .paths import user_data_dir, legacy_save_path

SAVE_VERSION = 2
STORY_STAGES = 24          # 6 sectors x 4 stages (see campaign.py)

DEFAULT_STATS = {
    "kills": 0, "deaths": 0, "fragments": 0, "bosses": 0, "dashes": 0,
    "grazes": 0, "games": 0, "playtime": 0.0, "loops": 0, "best_combo": 0,
}


def _default():
    return {
        "version": SAVE_VERSION,
        "story": None,
        "achievements": [],
        "stats": dict(DEFAULT_STATS),
        "scores": {},
        "flags": {},
    }


def new_story(difficulty="NORMAL", players=1, loop=1, carry=None):
    """A fresh story run. ``carry`` keeps upgrades/coins for New Game+ loops."""
    story = {
        "stage": 0, "coins": 0, "loop": loop, "difficulty": difficulty, "players": players,
        "hp_bonus": 0, "fire_level": 0, "dash_level": 0, "shield_cell": 0,
        "weapons": [], "weapon": "BLASTER", "seen": [],
    }
    if carry:
        for key in ("coins", "hp_bonus", "fire_level", "dash_level", "shield_cell", "weapons", "weapon"):
            if key in carry:
                story[key] = copy.deepcopy(carry[key])
        story["seen"] = ["prologue"]
    return story


class SaveData:
    def __init__(self, path=None):
        self.path = path if path is not None else user_data_dir() / "savegame.json"
        self.data = _default()

    # ---- load / save ----------------------------------------------------
    @classmethod
    def load(cls, path=None):
        obj = cls(path)
        raw = None
        try:
            raw = json.loads(obj.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = obj._read_legacy()
        except (OSError, ValueError):
            try:                                   # keep the broken file for inspection
                os.replace(obj.path, obj.path.with_suffix(".corrupt"))
            except OSError:
                pass
        if isinstance(raw, dict):
            obj._merge(raw)
        return obj

    def _read_legacy(self):
        """Import a VoidLoop 3.x save (``{"level": n, "coins": n}``) once."""
        try:
            old = json.loads(legacy_save_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(old, dict):
            return None
        level = old.get("level", 1)
        coins = old.get("coins", 0)
        if not isinstance(level, int) or not isinstance(coins, int):
            return None
        story = new_story()
        story["stage"] = max(0, min(level - 1, STORY_STAGES - 1))
        story["coins"] = max(0, coins)
        if level > 1:
            story["weapons"] = ["BLASTER"]
            story["seen"] = ["prologue"]
        ach = [a for a in old.get("achievements", []) if isinstance(a, str)]
        return {"story": story if level > 1 or coins else None, "achievements": ach}

    def _merge(self, raw):
        d = self.data
        story = raw.get("story")
        if isinstance(story, dict):
            base = new_story()
            for key, default in base.items():
                if key in story and isinstance(story[key], type(default)):
                    base[key] = story[key]
            base["stage"] = max(0, min(base["stage"], STORY_STAGES - 1))
            base["coins"] = max(0, base["coins"])
            d["story"] = base
        if isinstance(raw.get("achievements"), list):
            d["achievements"] = [a for a in raw["achievements"] if isinstance(a, str)]
        if isinstance(raw.get("stats"), dict):
            for key, default in DEFAULT_STATS.items():
                v = raw["stats"].get(key, default)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    d["stats"][key] = v
        if isinstance(raw.get("scores"), dict):
            for key, val in raw["scores"].items():
                if isinstance(val, dict) and isinstance(val.get("score"), (int, float)):
                    d["scores"][key] = val
        if isinstance(raw.get("flags"), dict):
            d["flags"] = raw["flags"]

    def save(self):
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
            return True
        except OSError:
            return False

    # ---- story --------------------------------------------------------
    @property
    def story(self):
        return self.data["story"]

    def has_story(self):
        return self.data["story"] is not None

    def start_story(self, difficulty, players, loop=1, carry=None):
        self.data["story"] = new_story(difficulty, players, loop, carry)
        return self.data["story"]

    def clear_story(self):
        self.data["story"] = None

    # ---- achievements ---------------------------------------------------
    def has(self, achievement):
        return achievement in self.data["achievements"]

    def unlock(self, achievement):
        """Returns True the first time an achievement is unlocked."""
        if achievement in self.data["achievements"]:
            return False
        self.data["achievements"].append(achievement)
        return True

    # ---- statistics -----------------------------------------------------
    def add_stat(self, name, amount=1):
        self.data["stats"][name] = self.data["stats"].get(name, 0) + amount

    def max_stat(self, name, value):
        if value > self.data["stats"].get(name, 0):
            self.data["stats"][name] = value

    @property
    def stats(self):
        return self.data["stats"]

    # ---- high scores ------------------------------------------------------
    @staticmethod
    def _score_key(mode, difficulty):
        return "%s|%s" % (mode, difficulty)

    def best(self, mode, difficulty):
        return self.data["scores"].get(self._score_key(mode, difficulty))

    def submit_score(self, mode, difficulty, score, extra=None):
        """Store a score. Returns True when it is a new personal best."""
        key = self._score_key(mode, difficulty)
        old = self.data["scores"].get(key)
        if old is None or score > old["score"]:
            entry = {"score": int(score)}
            if extra:
                entry.update(extra)
            self.data["scores"][key] = entry
            return True
        return False

    # ---- flags ------------------------------------------------------------
    def flag(self, name, default=False):
        return self.data["flags"].get(name, default)

    def set_flag(self, name, value=True):
        self.data["flags"][name] = value
