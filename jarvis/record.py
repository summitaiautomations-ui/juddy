"""Record a live conversation from the mic into the capture inbox.

Usage:
    python -m jarvis.record         # record until you press Ctrl-C
    python -m jarvis.record 600     # record for up to 600 seconds, then stop

The .wav lands in the capture inbox, where the capture worker transcribes and
summarizes it and logs highlights to Notion. Handy for in-person meetings or
calls on speakerphone.
"""
import sys
import wave
from datetime import datetime

import numpy as np

from . import config
from .audio import Microphone


def main():
    max_seconds = float(sys.argv[1]) if len(sys.argv) > 1 else None
    config.CAPTURE_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = config.CAPTURE_INBOX_DIR / f"note-{stamp}.wav"
    # Write under a .part name so the capture watcher never grabs a partial file.
    tmp = out.parent / (out.name + ".part")

    frames = []
    frame_dur = config.FRAME_SAMPLES / config.SAMPLE_RATE
    elapsed = 0.0
    print(f"Recording to {out.name} — press Ctrl-C to stop.", flush=True)
    try:
        with Microphone() as mic:
            for frame in mic.frames():
                frames.append(frame)
                elapsed += frame_dur
                if max_seconds is not None and elapsed >= max_seconds:
                    break
    except KeyboardInterrupt:
        pass

    if not frames:
        print("Nothing recorded.")
        return

    audio = np.concatenate(frames)
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    tmp.rename(out)
    print(f"Saved {len(audio) / config.SAMPLE_RATE:.0f}s to {out}")


if __name__ == "__main__":
    main()
