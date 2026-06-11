"""Microphone capture and speech endpointing.

A single 16 kHz mono int16 input stream feeds a frame queue. The wake-word
detector reads from it continuously; once triggered, `record_utterance` reads
from the same queue until the speaker goes quiet.
"""
import queue

import numpy as np
import sounddevice as sd

from . import config


class Microphone:
    """Continuous 16 kHz mono int16 capture exposed as a stream of frames."""

    def __init__(self):
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream = None

    def _callback(self, indata, frames, time_info, status):  # noqa: ARG002
        # indata is int16 with shape (frames, 1); keep a copy of the mono channel.
        self._q.put(indata[:, 0].copy())

    def __enter__(self):
        device = config.INPUT_DEVICE or None
        if device is not None and str(device).isdigit():
            device = int(device)
        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            blocksize=config.FRAME_SAMPLES,
            channels=1,
            dtype="int16",
            device=device,
            callback=self._callback,
        )
        self._stream.start()
        return self

    def __exit__(self, *exc):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def frames(self):
        """Yield captured frames forever (blocks until each is available)."""
        while True:
            yield self._q.get()

    def drain(self):
        """Discard any buffered frames (e.g. echo of our own speech)."""
        try:
            while True:
                self._q.get_nowait()
        except queue.Empty:
            pass


def rms(frame_int16: np.ndarray) -> float:
    """Root-mean-square loudness of a frame, normalised to [0, 1]."""
    if frame_int16.size == 0:
        return 0.0
    x = frame_int16.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(x * x)))


def record_utterance(mic: Microphone):
    """Record one command from the mic.

    Waits for speech to begin (up to VAD_START_TIMEOUT_S), then records until
    the speaker is silent for VAD_SILENCE_S or VAD_MAX_S is reached.

    Returns float32 mono audio in [-1, 1], or None if nothing was said.
    """
    frame_dur = config.FRAME_SAMPLES / config.SAMPLE_RATE
    silence_limit = max(1, int(config.VAD_SILENCE_S / frame_dur))

    collected = []
    speech_started = False
    silence_frames = 0
    elapsed = 0.0

    for frame in mic.frames():
        elapsed += frame_dur
        level = rms(frame)

        if not speech_started:
            if level >= config.VAD_START_RMS:
                speech_started = True
                collected.append(frame)
            elif elapsed >= config.VAD_START_TIMEOUT_S:
                return None  # the user never actually spoke
            continue

        collected.append(frame)
        if level < config.VAD_START_RMS:
            silence_frames += 1
            if silence_frames >= silence_limit:
                break
        else:
            silence_frames = 0

        if elapsed >= config.VAD_MAX_S:
            break

    if not collected:
        return None
    return np.concatenate(collected).astype(np.float32) / 32768.0
