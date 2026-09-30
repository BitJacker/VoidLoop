"""Audio manager: sound effects + looping music, all synthesized at run time.

Everything degrades gracefully: without an audio device the game simply runs silent.
"""
import time

import pygame

from . import synth, sounds
from .paths import cache_dir


class Audio:
    def __init__(self, sfx_volume=0.8, music_volume=0.6, enabled=True):
        self.ok = False
        self.sfx = {}
        self.music = {}
        self.sfx_volume = sfx_volume
        self.music_volume = music_volume
        self.current = None
        self._last = {}
        self._mus_idx = 0
        self.channels = 2
        self.music_channels = []
        if not enabled:
            return
        try:
            if pygame.mixer.get_init():          # pygame.init() may already have opened it at 44.1 kHz
                pygame.mixer.quit()
            pygame.mixer.init(22050, -16, 2, 512)
            freq, fmt, chans = pygame.mixer.get_init()
            if fmt != -16:                       # only signed 16-bit is supported by the synth output
                pygame.mixer.quit()
                pygame.mixer.init(freq, -16, chans, 512)
                freq, fmt, chans = pygame.mixer.get_init()
            synth.SR = int(freq)
            self.channels = max(1, min(2, chans))
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(2)
            self.music_channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.ok = True
        except (pygame.error, OSError, ValueError):
            self.ok = False

    # ---- loading ------------------------------------------------------------------
    def _sound_from_samples(self, samples):
        peak = max(max(samples), -min(samples), 1e-9)
        if peak > 0.95:                          # loud effects (explosions...) are scaled instead of clipped
            k = 0.95 / peak
            samples = [v * k for v in samples]
        pcm = synth.to_pcm(samples, self.channels)
        return pygame.mixer.Sound(buffer=pcm.tobytes())

    def load_sfx(self, progress=None):
        """Render all sound effects (about half a second in total)."""
        if not self.ok:
            return
        names = list(sounds.SFX)
        for i, name in enumerate(names):
            if name not in self.sfx:
                try:
                    snd = self._sound_from_samples(sounds.SFX[name]())
                    snd.set_volume(min(1.0, sounds.SFX_GAIN.get(name, 1.0) * self.sfx_volume))
                    self.sfx[name] = snd
                except Exception:
                    pass
            if progress:
                progress((i + 1) / len(names))

    def _music_sound(self, name):
        snd = self.music.get(name)
        if snd is not None:
            return snd
        path = cache_dir() / ("music_%s_v%d_%d_%d.wav" % (name, sounds.TRACK_VERSION, synth.SR, self.channels))
        try:
            if path.exists():
                snd = pygame.mixer.Sound(str(path))
        except (pygame.error, OSError):
            snd = None
        if snd is None:
            samples = sounds.compose(name)
            pcm = synth.to_pcm(samples, self.channels)
            try:
                synth.save_wav(path, pcm, self.channels)
            except OSError:
                pass
            snd = pygame.mixer.Sound(buffer=pcm.tobytes())
        self.music[name] = snd
        return snd

    def preload_music(self, name):
        if self.ok and self.music_volume > 0:
            try:
                self._music_sound(name)
            except Exception:
                pass

    # ---- playback -----------------------------------------------------------------------
    def play(self, name, volume=1.0):
        if not self.ok or self.sfx_volume <= 0:
            return
        snd = self.sfx.get(name)
        if snd is None:
            return
        gap = sounds.SFX_GAP.get(name, 0.0)
        now = time.monotonic()
        if gap and now - self._last.get(name, 0.0) < gap:
            return
        self._last[name] = now
        if volume != 1.0:
            snd.set_volume(min(1.0, sounds.SFX_GAIN.get(name, 1.0) * self.sfx_volume * volume))
            snd.play()
            snd.set_volume(min(1.0, sounds.SFX_GAIN.get(name, 1.0) * self.sfx_volume))
        else:
            snd.play()

    def play_music(self, name, fade_ms=900):
        if not self.ok or name == self.current:
            return
        self.current = name
        if self.music_volume <= 0:
            return
        try:
            snd = self._music_sound(name)
        except Exception:
            return
        old = self.music_channels[self._mus_idx]
        old.fadeout(fade_ms)
        self._mus_idx = 1 - self._mus_idx
        ch = self.music_channels[self._mus_idx]
        ch.set_volume(self.music_volume * 0.6)
        ch.play(snd, loops=-1, fade_ms=fade_ms)

    def stop_music(self, fade_ms=600):
        self.current = None
        if self.ok:
            for ch in self.music_channels:
                ch.fadeout(fade_ms)

    # ---- volumes ----------------------------------------------------------------------------
    def set_volumes(self, sfx=None, music=None):
        if sfx is not None:
            self.sfx_volume = max(0.0, min(1.0, sfx))
            for name, snd in self.sfx.items():
                snd.set_volume(min(1.0, sounds.SFX_GAIN.get(name, 1.0) * self.sfx_volume))
        if music is not None:
            was_off = self.music_volume <= 0
            self.music_volume = max(0.0, min(1.0, music))
            if self.ok:
                for ch in self.music_channels:
                    ch.set_volume(self.music_volume * 0.6)
                if was_off and self.music_volume > 0 and self.current:
                    track, self.current = self.current, None
                    self.play_music(track)
                elif self.music_volume <= 0:
                    for ch in self.music_channels:
                        ch.stop()
