"""Sound effects and music compositions (all synthesized - there are no audio files)."""
import random
import zlib

from . import synth as S
from .synth import note_freq, midi_freq, render_note, sweep, noise, sweep_noise, mix, concat, silence


# =============================================================================
#  Sound effects: name -> function returning a list of float samples
# =============================================================================
def _arp(notes, step, kind="tri", vol=0.4, decay=9.0):
    return concat(*[render_note(note_freq(n), step * 1.6, kind, vol, 0.002, decay, 0.01)[:int(step * S.SR)] for n in notes])


def _blip(freq, dur=0.035, vol=0.22):
    return render_note(freq, dur, "square", vol, 0.002, 30.0, 0.008, 0.5)


SFX = {
    "shoot": lambda: sweep(1150, 360, 0.085, "square", 0.24, decay=24, duty=0.25),
    "shoot2": lambda: sweep(820, 250, 0.10, "saw", 0.22, decay=20),
    "hit": lambda: mix(sweep(320, 150, 0.05, "square", 0.22, decay=40), noise(0.045, 0.18, 55, seed=3)),
    "explode": lambda: mix(sweep_noise(0.38, 5200, 180, 0.85, decay=6.5, seed=1), sweep(150, 42, 0.34, "sine", 0.7, decay=7)),
    "hurt": lambda: mix(sweep(340, 70, 0.42, "saw", 0.34, decay=4.5), noise(0.25, 0.3, 9, lowpass=0.55, seed=4)),
    "down": lambda: mix(sweep(520, 38, 1.0, "saw", 0.36, decay=2.6), sweep_noise(0.9, 3000, 90, 0.6, decay=3, seed=5)),
    "dash": lambda: sweep_noise(0.19, 500, 7000, 0.55, decay=7, seed=6),
    "fragment": lambda: _arp(["E5", "G5", "B5", "E6"], 0.055, "tri", 0.45),
    "coin": lambda: concat(_blip(1250, 0.04, 0.2), _blip(1900, 0.06, 0.2)),
    "powerup": lambda: mix(sweep(300, 1400, 0.38, "square", 0.2, decay=3, duty=0.3), sweep(450, 2100, 0.38, "tri", 0.25, decay=3)),
    "heal": lambda: _arp(["C5", "E5", "G5", "C6", "E6"], 0.06, "sine", 0.5, 7),
    "shield": lambda: mix(render_note(1480, 0.22, "sine", 0.3, 0.001, 16), render_note(2210, 0.22, "sine", 0.18, 0.001, 20)),
    "pulse": lambda: concat(sweep(160, 1600, 0.22, "saw", 0.28, decay=0), mix(sweep(120, 30, 0.6, "sine", 0.8, decay=4),
                                                                               sweep_noise(0.6, 4000, 120, 0.7, decay=5, seed=7))),
    "blast": lambda: mix(sweep_noise(0.42, 3600, 110, 0.75, decay=5.5, seed=8), sweep(110, 35, 0.4, "sine", 0.75, decay=6)),
    "boss_phase": lambda: concat(sweep(300, 900, 0.25, "saw", 0.3), sweep(900, 200, 0.5, "saw", 0.34, decay=2.5)),
    "boss_down": lambda: mix(sweep_noise(1.6, 4200, 70, 0.9, decay=1.6, seed=9), sweep(190, 28, 1.5, "sine", 0.9, decay=1.8),
                             sweep(700, 60, 1.4, "saw", 0.2, decay=2.2)),
    "clear": lambda: concat(_arp(["C5", "E5", "G5", "C6"], 0.09, "square", 0.22, 6), render_note(note_freq("E6"), 0.5, "tri", 0.4, 0.005, 3.5, 0.15)),
    "combo": lambda: concat(_blip(880, 0.04, 0.2), _blip(1320, 0.04, 0.2), _blip(1760, 0.07, 0.22)),
    "level": lambda: _arp(["G4", "B4", "D5", "G5", "B5"], 0.075, "square", 0.2, 6),
    "tick": lambda: render_note(1600, 0.05, "square", 0.25, 0.001, 30, 0.01, 0.4),
    "ready": lambda: concat(_blip(700, 0.05, 0.2), _blip(1050, 0.05, 0.2), _blip(1400, 0.09, 0.22)),
    "graze": lambda: render_note(2600, 0.03, "sine", 0.22, 0.001, 50),
    "swing": lambda: sweep_noise(0.16, 700, 3800, 0.5, decay=9, seed=10),
    "smash": lambda: mix(sweep(230, 70, 0.14, "square", 0.35, decay=18), noise(0.08, 0.35, 34, seed=11)),
    "portal": lambda: sweep(380, 1500, 0.28, "sine", 0.32, decay=2, vibrato=38),
    "comet": lambda: sweep(500, 2200, 0.24, "saw", 0.16, decay=5),
    "warning": lambda: concat(*[sweep(560, 560, 0.16, "square", 0.24, duty=0.4) + silence(0.04) + sweep(790, 790, 0.16, "square", 0.24, duty=0.4) + silence(0.04) for _ in range(3)]),
    "ui_move": lambda: _blip(760, 0.025, 0.16),
    "ui_select": lambda: concat(_blip(660, 0.05, 0.22), _blip(990, 0.09, 0.22)),
    "ui_back": lambda: concat(_blip(700, 0.05, 0.2), _blip(440, 0.09, 0.2)),
    "ui_error": lambda: sweep(220, 140, 0.16, "square", 0.24, decay=8),
    "buy": lambda: concat(_blip(1046, 0.05, 0.22), _blip(1568, 0.05, 0.22), _blip(2093, 0.1, 0.22)),
    "blip1": lambda: _blip(420, 0.03, 0.14),
    "blip2": lambda: _blip(560, 0.03, 0.14),
    "blip3": lambda: _blip(300, 0.035, 0.16),
    "achievement": lambda: _arp(["C6", "E6", "G6", "C7", "G6", "C7"], 0.06, "sine", 0.32, 6),
    "gameover": lambda: concat(_arp(["E4", "D4", "C4", "B3"], 0.2, "saw", 0.28, 3.5), sweep(247, 60, 0.9, "saw", 0.28, decay=3)),
    "win": lambda: concat(_arp(["C5", "E5", "G5", "C6", "E6", "G6"], 0.11, "square", 0.22, 5), render_note(note_freq("C7"), 0.9, "tri", 0.4, 0.005, 2.5, 0.3)),
}

# minimum time (seconds) between two plays of the same sound
SFX_GAP = {"shoot": 0.03, "shoot2": 0.04, "hit": 0.03, "explode": 0.04, "graze": 0.08, "coin": 0.03, "blip1": 0.02, "blip2": 0.02,
           "blip3": 0.02, "tick": 0.1, "smash": 0.05}
SFX_GAIN = {"shoot": 0.5, "shoot2": 0.55, "hit": 0.6, "graze": 0.6, "coin": 0.8, "blip1": 0.9, "blip2": 0.9, "blip3": 0.9,
            "explode": 0.55, "down": 0.6, "pulse": 0.55, "blast": 0.5, "boss_down": 0.65, "hurt": 0.85}


# =============================================================================
#  Music
# =============================================================================
CHORDS = {"m": (0, 3, 7), "M": (0, 4, 7), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11), "sus2": (0, 2, 7), "dim": (0, 3, 6), "5": (0, 7, 12)}
MINOR = (0, 2, 3, 5, 7, 8, 10)
PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)
DORIAN = (0, 2, 3, 5, 7, 9, 10)
DIM = (0, 2, 3, 5, 6, 8, 9, 11)

DRUMS = {                       # 16 steps per bar
    "none": dict(k=(), s=(), h=()),
    "soft": dict(k=(0, 8), s=(), h=(4, 12)),
    "half": dict(k=(0,), s=(8,), h=(4, 12)),
    "four": dict(k=(0, 4, 8, 12), s=(4, 12), h=(2, 6, 10, 14)),
    "break": dict(k=(0, 6, 10), s=(4, 12), h=(0, 2, 4, 6, 8, 10, 12, 14)),
    "drive": dict(k=(0, 4, 8, 12), s=(4, 12), h=tuple(range(0, 16, 2)) + (15,)),
    "glitch": dict(k=(0, 3, 10), s=(6, 13), h=(1, 2, 5, 9, 11, 14)),
}


def _prog(*chords):
    return list(chords)


TRACKS = {
    "menu": dict(bpm=90, key=45, scale=MINOR, pad=0.09, bass="long", arp="bells", drums=("none", "soft"), lead="bell", echo=0.4,
                 prog=_prog((0, "m7"), (8, "maj7"), (3, "M"), (10, "M"), (0, "m7"), (8, "maj7"), (3, "M"), (10, "M"),
                            (0, "m7"), (10, "M"), (8, "maj7"), (7, "M"), (0, "m7"), (10, "M"), (8, "maj7"), (7, "M"))),
    "s1": dict(bpm=104, key=40, scale=MINOR, pad=0.07, bass="pulse8", arp="up16", drums=("soft", "four"), lead="tri", echo=0.25,
               prog=_prog((0, "m"), (8, "M"), (3, "M"), (10, "M")) * 3 + _prog((0, "m"), (8, "M"), (10, "M"), (7, "M"))),
    "s2": dict(bpm=118, key=38, scale=DORIAN, pad=0.06, bass="walk", arp="up16", drums=("break", "drive"), lead="square", echo=0.3,
               prog=_prog((0, "m7"), (5, "m7"), (8, "M"), (7, "M")) * 3 + _prog((0, "m7"), (5, "m7"), (8, "M"), (10, "M"))),
    "s3": dict(bpm=132, key=40, scale=PHRYGIAN, pad=0.05, bass="pulse8", arp="pluck8", drums=("four", "drive"), lead="saw", echo=0.2,
               prog=_prog((0, "5"), (1, "M"), (0, "5"), (10, "M")) * 3 + _prog((0, "5"), (1, "M"), (8, "M"), (7, "M"))),
    "s4": dict(bpm=78, key=41, scale=MINOR, pad=0.10, bass="long", arp="bells", drums=("half", "half"), lead="bell", echo=0.55,
               prog=_prog((0, "m7"), (8, "maj7"), (3, "maj7"), (10, "M")) * 2 + _prog((0, "m7"), (5, "m7"), (8, "maj7"), (7, "M")) * 2),
    "s5": dict(bpm=124, key=43, scale=DIM, pad=0.05, bass="off", arp="up16", drums=("glitch", "break"), lead="square", echo=0.25, crush=9,
               prog=_prog((0, "m"), (1, "M"), (0, "dim"), (6, "M")) * 3 + _prog((0, "m"), (1, "M"), (6, "M"), (7, "M"))),
    "s6": dict(bpm=88, key=38, scale=MINOR, pad=0.10, bass="long", arp="bells", drums=("half", "soft"), lead="bell", echo=0.6, deep=True,
               prog=_prog((0, "m"), (8, "M"), (5, "m"), (7, "M")) * 3 + _prog((0, "m"), (8, "M"), (10, "M"), (7, "M"))),
    "boss": dict(bpm=148, key=38, scale=MINOR, pad=0.05, bass="pulse8", arp="up16", drums=("four", "drive"), lead="saw", echo=0.15,
                 prog=_prog((0, "5"), (8, "M"), (10, "M"), (7, "M")) * 3 + _prog((0, "5"), (8, "M"), (10, "M"), (7, "M"))),
    "final": dict(bpm=160, key=40, scale=PHRYGIAN, pad=0.06, bass="pulse8", arp="up16", drums=("drive", "drive"), lead="saw", echo=0.2, deep=True,
                  prog=_prog((0, "5"), (1, "M"), (8, "M"), (7, "M")) * 3 + _prog((0, "5"), (1, "M"), (10, "M"), (7, "M"))),
}
TRACK_VERSION = 3

_drum_cache = {}


def _drum(kind):
    key = (S.SR, kind)
    d = _drum_cache.get(key)
    if d is None:
        if kind == "k":
            d = mix(sweep(170, 42, 0.17, "sine", 0.95, decay=14), sweep(1800, 300, 0.012, "square", 0.25, decay=200))
        elif kind == "s":
            d = mix(noise(0.13, 0.5, 26, seed=21), sweep(220, 160, 0.09, "tri", 0.4, decay=25))
        else:
            d = noise(0.045, 0.22, 70, highpass=True, seed=22)
        _drum_cache[key] = d
    return d


def compose(name):
    """Render one music loop as float samples (seamless when looped)."""
    c = TRACKS[name]
    rng = random.Random(zlib.crc32(name.encode()))
    beat = 60.0 / c["bpm"]
    bar = beat * 4
    prog = c["prog"]
    sr = S.SR
    total = int(round(len(prog) * bar * sr))
    track = [0.0] * total
    half = len(prog) // 2
    scale = c["scale"]
    key = c["key"]
    prev_idx = 7

    def at(t):
        return int(t * sr)

    for bi, (deg, quality) in enumerate(prog):
        t0 = bi * bar
        root = key + deg
        chord = [root + i for i in CHORDS[quality]]
        section = 0 if bi < half else 1

        # ---- pad -------------------------------------------------------------
        if c.get("pad"):
            for note in chord:
                S.add_at(track, at(t0), render_note(midi_freq(note + 12), bar * 1.02, "soft", c["pad"], 0.35, 0.0, 0.5))
            if c.get("deep"):
                S.add_at(track, at(t0), render_note(midi_freq(root), bar * 1.02, "soft", c["pad"] * 1.2, 0.5, 0.0, 0.5))

        # ---- bass ---------------------------------------------------------------
        style = c["bass"]
        if style == "long":
            S.add_at(track, at(t0), render_note(midi_freq(root), bar * 0.98, "soft", 0.30, 0.02, 0.7, 0.15))
        elif style == "pulse8":
            pattern = (0, 0, 12, 0, 0, 0, 12, 7)
            for i, off in enumerate(pattern):
                S.add_at(track, at(t0 + i * beat / 2), render_note(midi_freq(root + off), beat * 0.45, "saw", 0.16 if off == 0 else 0.12, 0.004, 9.0, 0.03))
        elif style == "walk":
            for i, off in enumerate((0, 7, 12, 7)):
                S.add_at(track, at(t0 + i * beat), render_note(midi_freq(root + off), beat * 0.9, "soft", 0.28, 0.005, 4.0, 0.05))
        elif style == "off":
            for pos in (0, 0.75, 1.5, 2.5, 3.25):
                S.add_at(track, at(t0 + pos * beat), render_note(midi_freq(root + (12 if pos == 2.5 else 0)), beat * 0.4, "saw", 0.16, 0.003, 10.0, 0.03))

        # ---- arpeggio ---------------------------------------------------------------
        arp = c["arp"]
        if arp in ("up16", "pluck8"):
            steps = 16 if arp == "up16" else 8
            dur = beat * 4 / steps
            tones = chord + [chord[0] + 12]
            order = (0, 1, 2, 3, 2, 1) if len(tones) >= 4 else (0, 1, 2, 1)
            wave = "square" if c["lead"] != "saw" else "saw"
            for i in range(steps):
                if c.get("crush") and rng.random() < 0.18:
                    continue
                n = tones[order[i % len(order)] % len(tones)] + 24
                S.add_at(track, at(t0 + i * dur), render_note(midi_freq(n), dur * 1.4, wave, 0.055 if arp == "up16" else 0.07, 0.002, 12.0, 0.02, 0.25))
        elif arp == "bells":
            for pos in (0.0, 1.5, 2.5) if section == 0 else (0.0, 1.0, 2.0, 3.0):
                if rng.random() < 0.85:
                    n = rng.choice(chord) + 36
                    S.add_at(track, at(t0 + pos * beat), render_note(midi_freq(n), beat * 1.6, "bell", 0.12, 0.002, 3.2, 0.1))

        # ---- lead melody ----------------------------------------------------------------
        lead = c.get("lead")
        if lead and (section == 1 or c["bpm"] > 120):
            density = (0.9, 0.25, 0.6, 0.3, 0.85, 0.25, 0.6, 0.4)
            wave = {"tri": "tri", "square": "square", "saw": "saw", "bell": "bell"}[lead]
            vol = 0.10 if wave != "bell" else 0.16
            i = 0
            while i < 8:
                if rng.random() < density[i]:
                    if i in (0, 4):
                        note = rng.choice(chord) + 24
                    else:
                        prev_idx = max(0, min(len(scale) * 2 - 1, prev_idx + rng.choice((-2, -1, 1, 2))))
                        note = key + 24 + scale[prev_idx % len(scale)] + 12 * (prev_idx // len(scale))
                    length = 2 if rng.random() < 0.3 and i < 7 else 1
                    S.add_at(track, at(t0 + i * beat / 2), render_note(midi_freq(note), beat / 2 * length * 1.1, wave, vol, 0.005, 4.0, 0.05, 0.4))
                    i += length
                else:
                    i += 1

        # ---- drums ------------------------------------------------------------------------
        drums = DRUMS[c["drums"][section]]
        for step in range(16):
            ts = t0 + step * beat / 4
            if step in drums["k"]:
                S.add_at(track, at(ts), _drum("k"))
            if step in drums["s"]:
                S.add_at(track, at(ts), _drum("s"))
            if step in drums["h"]:
                S.add_at(track, at(ts), _drum("h"))

    if c.get("echo"):
        track = S.echo(track, beat * 0.75, 0.42, 3, c["echo"])
    if c.get("crush"):
        track = S.bitcrush(track, c["crush"])
    return S.normalize(track, 0.8)
