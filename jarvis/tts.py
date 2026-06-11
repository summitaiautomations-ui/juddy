"""Text-to-speech via the macOS `say` command.

To drive the HUD from Jarvis's real voice, speech is synthesized to a file,
its amplitude envelope is computed, and the file is played with `afplay` while
the envelope is streamed (via an `on_amp` callback) in sync with playback. If
synthesis/playback isn't available, it falls back to plain blocking `say`.

Claude's replies can contain markdown that sounds wrong read aloud, so we strip
it down to plain prose first.
"""
import os
import re
import subprocess
import tempfile
import time
import wave

import numpy as np

from . import config

_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_URL = re.compile(r"https?://\S+")
_MD_MARKS = re.compile(r"[*_#>`]+")

_ENV_FPS = 50          # envelope frames per second streamed to the HUD
_RMS_FULL_SCALE = 0.18  # RMS that maps to a full-amplitude ring


def speak_friendly(text: str) -> str:
    """Reduce markdown / code / URLs to something natural to hear."""
    text = _CODE_BLOCK.sub(" (code omitted) ", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _URL.sub(" a link ", text)
    text = _MD_MARKS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _envelope(path: str):
    """Per-frame normalized loudness (0..1) of a mono int16 WAV, at _ENV_FPS."""
    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if samples.size == 0:
        return []
    hop = max(1, sample_rate // _ENV_FPS)
    env = []
    for i in range(0, samples.size, hop):
        chunk = samples[i:i + hop]
        rms = float(np.sqrt(np.mean(chunk * chunk))) if chunk.size else 0.0
        env.append(min(1.0, rms / _RMS_FULL_SCALE))
    return env


class Speaker:
    def __init__(self):
        self._proc = None

    def say(self, text: str, friendly: bool = True, on_amp=None):
        spoken = speak_friendly(text) if friendly else text
        if not spoken:
            return
        if not self._say_with_envelope(spoken, on_amp):
            self._say_simple(spoken)

    def _voice_args(self):
        args = []
        if config.TTS_VOICE:
            args += ["-v", config.TTS_VOICE]
        if config.TTS_RATE:
            args += ["-r", str(config.TTS_RATE)]
        return args

    def _say_simple(self, text: str):
        self._proc = subprocess.Popen(["say"] + self._voice_args() + [text])
        self._proc.wait()
        self._proc = None

    def _say_with_envelope(self, text: str, on_amp) -> bool:
        """Synthesize -> analyze -> play, streaming amplitude. False on failure."""
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".wav", prefix="jarvis-tts-")
            os.close(fd)
            synth = subprocess.run(
                ["say"] + self._voice_args()
                + ["-o", path, "--file-format=WAVE", "--data-format=LEI16@22050", text],
                capture_output=True,
            )
            if synth.returncode != 0 or os.path.getsize(path) == 0:
                return False

            envelope = _envelope(path)
            if not envelope:
                return False

            self._proc = subprocess.Popen(["afplay", path])
            frame_dt = 1.0 / _ENV_FPS
            start = time.monotonic()
            for i, amp in enumerate(envelope):
                if on_amp is not None:
                    on_amp(amp)
                if self._proc.poll() is not None:
                    break  # playback ended early (e.g. stopped)
                target = start + (i + 1) * frame_dt
                time.sleep(max(0.0, target - time.monotonic()))
            self._proc.wait()
            return True
        except FileNotFoundError:
            return False  # `say` or `afplay` not on this platform
        except Exception:
            return False
        finally:
            if on_amp is not None:
                on_amp(0.0)
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            self._proc = None

    def stop(self):
        """Interrupt speech in progress (barge-in)."""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
