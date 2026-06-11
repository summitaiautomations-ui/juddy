"""Conversation capture worker.

Watches an inbox folder for recordings — from a Plaud recorder, a mic note
(see record.py), or any dropped audio/transcript — transcribes audio with
faster-whisper, then asks the brain to summarize it, pull next steps, and log
highlights to the matching Notion pipeline record.

Run it with:  python -m jarvis.capture
"""
import logging
import re
import shutil
import sys
import time
from pathlib import Path

from . import config
from .brain import Brain
from .stt import Transcriber
from .tts import Speaker

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".flac", ".m4b", ".aac", ".ogg", ".mp4"}
TEXT_EXTS = {".txt", ".md", ".vtt", ".srt"}


def _setup_logging() -> logging.Logger:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOG_DIR / "jarvis-capture.log"),
        ],
    )
    return logging.getLogger("jarvis.capture")


def _ready_files(inbox: Path):
    """New, fully-written files in the inbox (skips dotfiles and subfolders)."""
    for path in sorted(inbox.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in AUDIO_EXTS or path.suffix.lower() in TEXT_EXTS:
            yield path


def _extract_tldr(summary: str) -> str:
    """Pull the TL;DR out of the brain's summary for a spoken read-back.

    Falls back to the first couple of sentences if there's no TL;DR heading.
    """
    lines = summary.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"tl;?dr", line, re.IGNORECASE):
            after = re.split(r"tl;?dr", line, flags=re.IGNORECASE)[-1]
            collected = []
            head = after.lstrip(" :*-—–)").strip()
            if head:
                collected.append(head)
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if not s:
                    if collected:
                        break
                    continue
                if re.match(r"^(#{1,6}\s|\d+[.)]\s|[-*]\s|\*\*)", s):
                    break
                collected.append(s)
            text = " ".join(collected).strip()
            if text:
                return text
    plain = re.sub(r"[#*`>_]", "", summary).strip()
    sentences = re.split(r"(?<=[.!?])\s+", plain)
    return " ".join(sentences[:2]).strip()


def _is_stable(path: Path, wait: float = 2.0) -> bool:
    """Guard against picking up a file that's still syncing/being written."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return False
    time.sleep(wait)
    return path.exists() and path.stat().st_size == size and size > 0


def _process(path: Path, stt: Transcriber, brain: Brain, speaker, log: logging.Logger,
             processed: Path, failed: Path):
    try:
        if path.suffix.lower() in AUDIO_EXTS:
            log.info("Transcribing %s ...", path.name)
            transcript = stt.transcribe_file(path)
        else:
            transcript = path.read_text(errors="ignore")

        if not transcript.strip():
            raise ValueError("empty transcript")

        log.info("Summarizing %s (%d chars) ...", path.name, len(transcript))
        result = brain.process_transcript(transcript, source=path.name)
        log.info("Summary for %s:\n%s", path.name, result)

        (processed / f"{path.stem}.summary.md").write_text(
            f"# Capture summary — {path.name}\n\n{result}\n"
        )
        shutil.move(str(path), str(processed / path.name))

        if speaker is not None:
            tldr = _extract_tldr(result)
            if tldr:
                speaker.say(f"Here's the recap. {tldr}")
    except Exception as exc:  # noqa: BLE001 — keep the worker alive on any one file
        log.exception("Failed to process %s: %s", path.name, exc)
        shutil.move(str(path), str(failed / path.name))


def main():
    log = _setup_logging()
    inbox = config.CAPTURE_INBOX_DIR
    processed = inbox / "processed"
    failed = inbox / "failed"
    for d in (inbox, processed, failed):
        d.mkdir(parents=True, exist_ok=True)

    log.info("Loading models ...")
    stt = Transcriber()
    brain = Brain()
    speaker = Speaker() if config.CAPTURE_READBACK else None
    log.info("Watching %s for recordings (Plaud, mic notes, dropped audio).", inbox)

    while True:
        for path in _ready_files(inbox):
            if _is_stable(path):
                _process(path, stt, brain, speaker, log, processed, failed)
        time.sleep(config.CAPTURE_POLL_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
