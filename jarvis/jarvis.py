#!/usr/bin/env python3
"""Jarvis — an always-on voice assistant with Claude as its brain.

Pipeline:
    mic -> wake word ("Hey Jarvis") -> record until silence ->
    speech-to-text -> Claude (the brain) -> text-to-speech -> repeat
"""
import logging
import sys
import time

from . import config
from .audio import Microphone, record_utterance
from .brain import Brain
from .stt import Transcriber
from .tts import Speaker
from .wake import WakeWord


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
