"""Localisation: UI strings and story dialogues, both stored as JSON per language.

    lang/ui_<code>.json         flat  key -> string / list of strings
    lang/dialogues_<code>.json  story scenes: key -> ["SPEAKER: text", ...]

Missing keys fall back to English, then to the key itself, so a partially
translated language never crashes the game.
"""
import json
import random
import re
from collections import namedtuple

from .paths import lang_dir
from .settings import LANG_CODES

Line = namedtuple("Line", "speaker style text")

# "NAME: text" - the name must be upper case so that ordinary sentences that
# happen to contain a colon are not mistaken for a speaker tag.
_SPEAKER_RE = re.compile(r"^\s*([A-ZÀ-ÖØ-Þ0-9][A-ZÀ-ÖØ-Þ0-9 '’_.\-]{0,28}?)\s*:\s+(\S.*)$")


def _load_json(name):
    try:
        with open(lang_dir() / name, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


class I18n:
    def __init__(self, lang="en"):
        self._ui = {}
        self._dlg = {}
        self.lang = "en"
        self.set_language(lang)

    # ---- language -------------------------------------------------------
    def set_language(self, lang):
        if lang not in LANG_CODES:
            lang = "en"
        for code in {lang, "en"}:
            if code not in self._ui:
                self._ui[code] = _load_json("ui_%s.json" % code)
                self._dlg[code] = _load_json("dialogues_%s.json" % code)
        self.lang = lang

    # ---- UI strings -------------------------------------------------------
    def _lookup(self, table, key):
        for code in (self.lang, "en"):
            value = table.get(code, {}).get(key)
            if value is not None:
                return value
        return None

    def t(self, key, **kwargs):
        value = self._lookup(self._ui, key)
        if not isinstance(value, str):
            return key
        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return value
        return value

    def tl(self, key):
        """A list of strings (tips, help pages ...)."""
        value = self._lookup(self._ui, key)
        return [str(v) for v in value] if isinstance(value, list) else []

    def has(self, key):
        return self._lookup(self._ui, key) is not None

    # ---- dialogues ----------------------------------------------------------
    def speaker_style(self, name):
        table = self._lookup(self._dlg, "_speakers") or {}
        return table.get(name.upper(), "default")

    def parse_line(self, raw):
        m = _SPEAKER_RE.match(raw)
        if not m:
            return Line(None, "narrator", raw.strip())
        name, text = m.group(1).strip(), m.group(2).strip()
        return Line(name, self.speaker_style(name), text)

    def has_scene(self, key):
        return isinstance(self._lookup(self._dlg, key), list)

    def scene(self, key):
        """All the lines of one scene (a pool of scenes yields its first one)."""
        value = self._lookup(self._dlg, key)
        if not isinstance(value, list) or not value:
            return []
        if isinstance(value[0], list):
            value = value[0]
        return [self.parse_line(str(s)) for s in value]

    def pick_scene(self, key, rng=random):
        """A random scene out of a pool (``[[line, ...], [line, ...]]``)."""
        value = self._lookup(self._dlg, key)
        if not isinstance(value, list) or not value:
            return []
        choice = rng.choice(value)
        if not isinstance(choice, list):
            choice = value
        return [self.parse_line(str(s)) for s in choice]

    def pick_line(self, key, rng=random):
        """A random single line out of a flat list of alternatives."""
        value = self._lookup(self._dlg, key)
        if not isinstance(value, list) or not value:
            return None
        choice = rng.choice(value)
        if isinstance(choice, list):
            choice = choice[0] if choice else ""
        return self.parse_line(str(choice))

    # ---- raw access (tests / tools) ----------------------------------------------
    def raw_ui(self, lang):
        if lang not in self._ui:
            self._ui[lang] = _load_json("ui_%s.json" % lang)
        return self._ui[lang]

    def raw_dialogues(self, lang):
        if lang not in self._dlg:
            self._dlg[lang] = _load_json("dialogues_%s.json" % lang)
        return self._dlg[lang]


# Shared instance used all over the game.
i18n = I18n()
T = i18n.t
