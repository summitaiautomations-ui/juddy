#!/usr/bin/env python3
"""Jarvis — an always-on voice assistant with Claude as its brain.

Pipeline:
    mic -> wake word ("Hey Jarvis") -> record until silence ->
    speech-to-text -> Claude (the brain) -> text-to-speech -> repeat
"""
import logging
import sys
import time
from datetime import datetime

import numpy as np

from . import config
from .audio import Microphone, record_utterance, save_wav
from .brain import Brain
from .stt import Transcriber
from .tts import Speaker
from .wake import WakeWord

# Spoken intents handled locally (before the brain).
_NOTE_TRIGGERS = (
    "take note", "taking notes", "take a note", "start notes", "note taking",
    "listen to this", "record this", "record the", "capture this",
)
_STOP_TRIGGERS = (
    "done", "stop", "that's all", "thats all", "finished", "finish",
    "wrap up", "all done", "i'm done", "im done",
)


def _wants_notes(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _NOTE_TRIGGERS)


def _wants_stop(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in _STOP_TRIGGERS)


def _take_notes_session(mic, wake, stt, tts, log):
    """Record a conversation until the user says 'Hey Jarvis, done'.

    Buffers audio while still running the wake-word detector, so a second
    wake + a stop word ends the session. The recording is dropped into the
    capture inbox, where the capture worker transcribes and summarizes it.
    """
    tts.say("Okay, I'm taking notes. Say 'Hey Jarvis, done' when you're finished.",
            friendly=False)
    mic.drain()
    wake.reset()

    frames = []
    frame_dur = config.FRAME_SAMPLES / config.SAMPLE_RATE
    elapsed = 0.0
    last_fire = 0.0

    for frame in mic.frames():
        frames.append(frame)
        elapsed += frame_dur
        if elapsed >= config.CAPTURE_MAX_SESSION_S:
            log.info("Note session hit the max duration; wrapping up.")
            break

        if not wake.detected(frame):
            continue
        now = time.monotonic()
        if now - last_fire < config.WAKE_COOLDOWN_S:
            continue
        last_fire = now

        wake.reset()
        mic.drain()
        command = record_utterance(mic)
        spoken = stt.transcribe(command) if command is not None else ""
        log.info("Note-session interjection: %r", spoken)
        if _wants_stop(spoken):
            break
        tts.say("Still listening.", friendly=False)
        mic.drain()
        wake.reset()

    if not frames:
        tts.say("I didn't catch anything.", friendly=False)
        return

    audio = np.concatenate(frames)
    config.CAPTURE_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = config.CAPTURE_INBOX_DIR / f"note-{stamp}.wav"
    tmp = out.parent / (out.name + ".part")  # avoid the watcher grabbing a partial file
    save_wav(tmp, audio)
    tmp.rename(out)
    log.info("Saved note session: %s (%.0fs)", out, len(audio) / config.SAMPLE_RATE)
    tts.say("Got it. I'll summarize that and update Notion.", friendly=False)


def _setup_logging() -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOG_DIR / "jarvis.log"),
        ],
    )
    return logging.getLogger("jarvis")


def main():
    log = _setup_logging()
    log.info("Jarvis starting up — loading models...")

    wake = WakeWord()
    stt = Transcriber()
    tts = Speaker()
    brain = Brain()
    log.info("Models ready. Listening for the wake word %r.", config.WAKE_MODEL)

    with Microphone() as mic:
        last_fire = 0.0
        for frame in mic.frames():
            if not wake.detected(frame):
                continue

            now = time.monotonic()
            if now - last_fire < config.WAKE_COOLDOWN_S:
                continue  # debounce repeated triggers
            last_fire = now

            log.info("Wake word detected.")
            wake.reset()
            mic.drain()

            if config.WAKE_ACK:
                tts.say(config.WAKE_ACK, friendly=False)
                mic.drain()  # clear the echo of our own acknowledgement

            audio = record_utterance(mic)
            if audio is None:
                log.info("No speech captured after wake word.")
                continue

            text = stt.transcribe(audio)
            if not text:
                log.info("Empty transcription; ignoring.")
                continue
            log.info("Heard: %s", text)

            if _wants_notes(text):
                _take_notes_session(mic, wake, stt, tts, log)
                wake.reset()
                mic.drain()
                continue

            reply = brain.ask(text)
            log.info("Jarvis: %s", reply)
            tts.say(reply)

            wake.reset()
            mic.drain()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
