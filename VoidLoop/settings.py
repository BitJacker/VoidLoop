"""Game-wide constants and the persisted user settings."""
import json
import os
import sys
import warnings
from dataclasses import dataclass, asdict, fields

from .paths import user_data_dir

# --- display -------------------------------------------------------------
W, H = 1280, 720          # logical resolution (scaled to the real window)
FPS = 60

# --- game modes / languages / difficulty -----------------------------------
MODES = ("STORY", "ENDLESS", "TIME_ATTACK", "BOSS_RUSH", "HORDE")
LANGUAGES = (("it", "Italiano"), ("en", "English"), ("es", "Español"), ("fr", "Français"))
LANG_CODES = tuple(code for code, _ in LANGUAGES)

SHIP_COLORS = {
    "Neon Green": (0, 255, 150),
    "Cyber Blue": (0, 150, 255),
    "Void Purple": (180, 60, 255),
    "Solar Gold": (255, 200, 40),
    "Crimson": (255, 70, 100),
    "Ghost White": (225, 235, 255),
}
P2_COLOR = (255, 130, 30)

DIFFICULTY_ORDER = ("EASY", "NORMAL", "HARD", "NIGHTMARE")
DIFFICULTIES = {
    # speed:  enemy speed multiplier          spawn: spawn chance per frame
    # cost:   base price used by the shop     hp:    player hit points
    # bullet: enemy bullet speed multiplier   score: score multiplier
    # drops:  pickup drop multiplier          boss:  boss hit points multiplier
    "EASY":      {"speed": 0.7, "spawn": 0.005, "cost": 5,  "hp": 5, "bullet": 0.85, "score": 0.5, "drops": 1.5, "boss": 0.75},
    "NORMAL":    {"speed": 1.0, "spawn": 0.009, "cost": 10, "hp": 3, "bullet": 1.00, "score": 1.0, "drops": 1.0, "boss": 1.0},
    "HARD":      {"speed": 1.4, "spawn": 0.015, "cost": 20, "hp": 2, "bullet": 1.10, "score": 1.5, "drops": 0.8, "boss": 1.25},
    "NIGHTMARE": {"speed": 1.9, "spawn": 0.025, "cost": 30, "hp": 1, "bullet": 1.20, "score": 2.5, "drops": 0.6, "boss": 1.5},
}


def detect_language():
    """Best guess of the user's language, restricted to the supported ones."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            found = {0x10: "it", 0x0A: "es", 0x0C: "fr", 0x09: "en"}.get(primary)
            if found:
                return found
        except Exception:
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(var, "").lower()
        if value[:2] in LANG_CODES:
            return value[:2]
    try:
        import locale
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            value = (locale.getdefaultlocale()[0] or "").lower()
        if value[:2] in LANG_CODES:
            return value[:2]
    except Exception:
        pass
    return "en"


@dataclass
class Settings:
    language: str = ""
    ship_color: str = "Neon Green"
    players: int = 1
    difficulty: str = "NORMAL"
    last_mode: str = "STORY"
    fullscreen: bool = False
    music: float = 0.6
    sfx: float = 0.8
    crt: bool = True
    shake: bool = True
    show_fps: bool = False

    # ---- persistence -------------------------------------------------
    @staticmethod
    def path():
        return user_data_dir() / "settings.json"

    @classmethod
    def load(cls):
        s = cls()
        try:
            data = json.loads(cls.path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict):
            for f in fields(cls):
                if f.name not in data:
                    continue
                value, expected = data[f.name], type(getattr(s, f.name))
                if expected is float and isinstance(value, int) and not isinstance(value, bool):
                    value = float(value)
                if isinstance(value, expected) and (expected is bool or not isinstance(value, bool)):
                    setattr(s, f.name, value)
        s.validate()
        return s

    def validate(self):
        if self.language not in LANG_CODES:
            self.language = detect_language()
        if self.ship_color not in SHIP_COLORS:
            self.ship_color = "Neon Green"
        if self.difficulty not in DIFFICULTIES:
            self.difficulty = "NORMAL"
        if self.last_mode not in MODES:
            self.last_mode = "STORY"
        self.players = 2 if self.players == 2 else 1
        self.music = min(1.0, max(0.0, float(self.music)))
        self.sfx = min(1.0, max(0.0, float(self.sfx)))

    def save(self):
        self.validate()
        try:
            tmp = self.path().with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
            os.replace(tmp, self.path())
        except OSError:
            pass

    # ---- helpers -----------------------------------------------------
    @property
    def cfg(self):
        return DIFFICULTIES[self.difficulty]

    @property
    def color(self):
        return SHIP_COLORS[self.ship_color]
