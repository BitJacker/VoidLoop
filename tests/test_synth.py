import math

import pytest

from VoidLoop import synth, sounds


def peak(samples):
    return max(max(samples), -min(samples))


def test_note_frequencies():
    assert synth.note_freq("A4") == pytest.approx(440.0)
    assert synth.note_freq("C5") == pytest.approx(523.25, abs=0.01)
    assert synth.midi_freq(69) == pytest.approx(440.0)


def test_wave_tables_repeat_seamlessly():
    for freq in (55.0, 220.0, 440.0, 1046.5, 2000.0):
        tbl = synth.table(freq, "sine")
        actual = synth.SR * (len(tbl) and 1) / len(tbl)
        periods = round(freq * len(tbl) / synth.SR)
        assert periods >= 1
        assert abs(tbl[0]) < 0.35 and abs(tbl[-1] - tbl[0]) < 0.6


@pytest.mark.parametrize("name", sorted(sounds.SFX))
def test_every_sound_effect_renders(name):
    s = sounds.SFX[name]()
    assert len(s) > 100
    assert all(math.isfinite(v) for v in s[:: max(1, len(s) // 400)])
    assert peak(s) > 0.02, "sound %s is silent" % name


def test_pcm_conversion_clips_and_interleaves():
    pcm = synth.to_pcm([0.0, 2.0, -2.0, 0.5], channels=2)
    assert len(pcm) == 8
    assert max(pcm) == 32767 and min(pcm) == -32767


@pytest.mark.parametrize("name", ["boss", "menu"])
def test_music_tracks_loop_without_clicks(name):
    s = sounds.compose(name)
    assert 15 < len(s) / synth.SR < 60
    assert peak(s) <= 0.81
    assert abs(s[0] - s[-1]) < 0.15, "loop seam is too abrupt"
    assert (sum(v * v for v in s) / len(s)) ** 0.5 > 0.03, "track is nearly silent"


def test_all_tracks_are_defined_consistently():
    for name, cfg in sounds.TRACKS.items():
        assert len(cfg["prog"]) % 2 == 0
        assert all(q in sounds.CHORDS for _, q in cfg["prog"])
        assert all(d in sounds.DRUMS for d in cfg["drums"])
