"""A tiny software synthesizer (pure Python, no numpy) used for every sound in the game.

Sound effects are rendered sample by sample (they are short). Music is rendered from
cached periodic wave tables that are repeated at C speed, which keeps the generation
of a 30 second loop well under a second.
"""
import array
import math
import random
import wave as _wave

SR = 22050          # sample rate (set by audio.py to whatever the mixer really opened)
TAU = math.tau

NOTE_INDEX = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
              "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def note_freq(name):
    """'A4' -> 440.0, 'C#3' -> 138.59 ..."""
    if isinstance(name, (int, float)):
        return float(name)
    letter = name[:-1]
    octave = int(name[-1])
    midi = 12 * (octave + 1) + NOTE_INDEX[letter]
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def midi_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


# --- wave tables ---------------------------------------------------------------------
_tables = {}


def _shape(kind, ph, duty):
    if kind == "sine":
        return math.sin(TAU * ph)
    if kind == "square":
        return 1.0 if ph < duty else -1.0
    if kind == "saw":
        return 2.0 * ph - 1.0
    if kind == "tri":
        return 4.0 * abs(ph - 0.5) - 1.0
    if kind == "soft":                       # sine with a bit of 2nd/3rd harmonic - warm pad/bass
        return 0.75 * math.sin(TAU * ph) + 0.18 * math.sin(2 * TAU * ph) + 0.07 * math.sin(3 * TAU * ph)
    if kind == "bell":
        return 0.6 * math.sin(TAU * ph) + 0.3 * math.sin(TAU * ph * 2.756) + 0.1 * math.sin(TAU * ph * 5.404)
    raise ValueError(kind)


def table(freq, kind="sine", duty=0.5):
    """A list of samples spanning a whole number of periods (so it can be repeated seamlessly)."""
    key = (SR, round(freq, 2), kind, duty)
    tbl = _tables.get(key)
    if tbl is None:
        period = SR / freq
        n_periods = 1
        for n in range(1, 41):
            length = period * n
            if abs(length - round(length)) / length < 0.0005:
                n_periods = n
                break
        else:
            n_periods = 40
        length = max(2, int(round(period * n_periods)))
        tbl = [_shape(kind, (i * n_periods / length) % 1.0, duty) for i in range(length)]
        _tables[key] = tbl
    return tbl


_envs = {}


def envelope(n, attack=0.005, decay=6.0, release=0.03):
    """Exponential decay envelope with linear attack/release. ``decay`` in 1/seconds."""
    key = (SR, n, attack, decay, release)
    env = _envs.get(key)
    if env is None:
        a = max(1, int(attack * SR))
        r = max(1, int(release * SR))
        env = [0.0] * n
        for i in range(n):
            v = math.exp(-decay * i / SR) if decay else 1.0
            if i < a:
                v *= i / a
            left = n - i
            if left < r:
                v *= left / r
            env[i] = v
        if len(_envs) > 400:
            _envs.clear()
        _envs[key] = env
    return env


def render_note(freq, dur, kind="sine", vol=1.0, attack=0.005, decay=6.0, release=0.03, duty=0.5):
    """Fast note: repeated wave table x envelope."""
    n = max(2, int(dur * SR))
    tbl = table(freq, kind, duty)
    reps = n // len(tbl) + 1
    wave = (tbl * reps)[:n]
    env = envelope(n, attack, decay, release)
    return [w * e * vol for w, e in zip(wave, env)]


# --- per-sample generators for sound effects ---------------------------------------------
def sweep(f0, f1, dur, kind="square", vol=0.5, attack=0.003, decay=0.0, duty=0.5, release=0.02, vibrato=0.0):
    """A tone whose pitch glides (exponentially) from f0 to f1."""
    n = max(2, int(dur * SR))
    out = [0.0] * n
    ph = 0.0
    ratio = f1 / f0
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    for i in range(n):
        t = i / n
        f = f0 * (ratio ** t)
        if vibrato:
            f *= 1.0 + 0.03 * math.sin(i * vibrato / SR * TAU)
        ph = (ph + f / SR) % 1.0
        if kind == "sine":
            v = math.sin(TAU * ph)
        elif kind == "square":
            v = 1.0 if ph < duty else -1.0
        elif kind == "saw":
            v = 2 * ph - 1
        else:
            v = 4 * abs(ph - 0.5) - 1
        env = math.exp(-decay * i / SR) if decay else 1.0
        if i < a:
            env *= i / a
        if n - i < r:
            env *= (n - i) / r
        out[i] = v * env * vol
    return out


def noise(dur, vol=0.5, decay=8.0, lowpass=0.0, highpass=False, seed=None, attack=0.001):
    """White noise burst. ``lowpass`` 0..0.99 smooths it (higher = darker)."""
    rng = random.Random(seed)
    n = max(2, int(dur * SR))
    out = [0.0] * n
    prev = 0.0
    prev_raw = 0.0
    a = max(1, int(attack * SR))
    for i in range(n):
        raw = rng.uniform(-1.0, 1.0)
        if lowpass:
            prev = prev * lowpass + raw * (1 - lowpass)
            v = prev
        elif highpass:
            v = raw - prev_raw
            prev_raw = raw
        else:
            v = raw
        env = math.exp(-decay * i / SR) if decay else 1.0
        if i < a:
            env *= i / a
        out[i] = v * env * vol
    return out


def sweep_noise(dur, f_lp0, f_lp1, vol=0.5, decay=0.0, seed=None):
    """Noise through a low-pass filter whose cutoff glides (explosions, whooshes)."""
    rng = random.Random(seed)
    n = max(2, int(dur * SR))
    out = [0.0] * n
    y = 0.0
    for i in range(n):
        t = i / n
        fc = f_lp0 * ((f_lp1 / f_lp0) ** t)
        alpha = min(0.99, 1 - math.exp(-TAU * fc / SR))
        y += alpha * (rng.uniform(-1.0, 1.0) - y)
        env = math.exp(-decay * i / SR) if decay else 1.0
        if n - i < 200:
            env *= (n - i) / 200
        out[i] = y * env * vol * 2.2
    return out


def mix(*tracks):
    """Sum lists of different lengths into one."""
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def silence(dur):
    return [0.0] * int(dur * SR)


def add_at(dest, start, samples, wrap=True):
    """Add ``samples`` into ``dest`` at index ``start`` (wrapping around the end for seamless loops)."""
    total = len(dest)
    n = len(samples)
    start %= total
    end = start + n
    if end <= total:
        dest[start:end] = [a + b for a, b in zip(dest[start:end], samples)]
    elif wrap:
        first = total - start
        dest[start:] = [a + b for a, b in zip(dest[start:], samples[:first])]
        rest = samples[first:first + total]
        dest[:len(rest)] = [a + b for a, b in zip(dest[:len(rest)], rest)]
    else:
        first = total - start
        dest[start:] = [a + b for a, b in zip(dest[start:], samples[:first])]


def echo(track, delay, feedback=0.4, taps=4, wet=1.0):
    """Circular (loop-safe) echo."""
    total = len(track)
    out = list(track)
    gain = feedback
    for k in range(1, taps + 1):
        shift = int(delay * SR * k) % total
        if shift:
            rotated = track[-shift:] + track[:-shift]
            out = [a + b * gain * wet for a, b in zip(out, rotated)]
        gain *= feedback
    return out


def lowpass(track, alpha):
    out = [0.0] * len(track)
    y = 0.0
    for i, v in enumerate(track):
        y += alpha * (v - y)
        out[i] = y
    return out


def bitcrush(track, levels=12):
    return [round(v * levels) / levels for v in track]


def normalize(track, peak=0.85):
    top = max(max(track), -min(track), 1e-9)
    k = peak / top
    return [v * k for v in track]


def to_pcm(track, channels=1, gain=1.0):
    """float samples (-1..1) -> interleaved signed 16-bit ``array('h')``."""
    ints = array.array("h", [max(-32767, min(32767, int(v * gain * 32767))) for v in track])
    if channels == 1:
        return ints
    out = array.array("h", bytes(len(ints) * 2 * channels))
    for c in range(channels):
        out[c::channels] = ints
    return out


def save_wav(path, pcm, channels=1):
    with _wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
