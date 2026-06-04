"""
Jarvis — always-listening voice assistant for the recruiting pipeline.

Pipeline per turn:
  1. Porcupine listens locally for the "Jarvis" wake word
  2. Record audio until ~1.5s of silence
  3. Transcribe with faster-whisper (runs locally, no API)
  4. Send to Claude with the Notion tool set
  5. Speak the reply with macOS `say` (formal British butler voice)

Env required:
  PICOVOICE_ACCESS_KEY   (free from picovoice.ai/console)
  ANTHROPIC_API_KEY      (Claude)
  NOTION_TOKEN           (same integration as the dashboard)
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
import wave
from datetime import datetime
from io import BytesIO
from queue import Queue

import numpy as np
import pvporcupine
import sounddevice as sd
from anthropic import Anthropic
from faster_whisper import WhisperModel

import notion_tools

# ---------- config ----------
WAKE_KEYWORD = "jarvis"
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
TTS_VOICE = os.environ.get("TTS_VOICE", "Daniel")  # British butler
TTS_RATE = os.environ.get("TTS_RATE", "190")
SILENCE_RMS = 380          # below this is silence
SILENCE_HANG_MS = 1500     # stop after this much continuous silence
MAX_UTTERANCE_MS = 12000   # hard cap so a stuck mic doesn't run forever
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You are Jarvis, a formal butler-style assistant to Justin Neal,
Vice President of Talent Acquisition at Summit Mortgage. Address him as "sir."

Be crisp, brief, and professional. No filler, no preamble. Reference candidates by
first name. When stating numbers, round naturally (e.g. "fifty-six million,"
"one-hundred-sixty-seven units"). Prefer short sentences a person can take in by ear.

You have direct read/write access to the recruiting pipeline in Notion via tools.
Use them confidently:
  - search_candidate: find someone by name
  - get_pipeline_summary: total counts and volume by stage
  - get_followups: who is due for a follow-up (overdue or soon)
  - create_candidate: add a new candidate (Initial Outreach by default)
  - update_candidate: change fields on an existing page (requires page_id)
  - move_stage: move someone to a new stage (auto-applies priority rule)

Stage-priority convention (always applied):
  Offer  -> Priority Hot
  Interview -> Priority Warm
  Passed -> Priority cleared

When the user asks you to add or change someone, confirm what you did in one
sentence. When the user asks a question, answer in one or two sentences.
Do not narrate your tool usage. Do not say "I'm searching..." -- just answer.
"""

TOOLS = [
    {
        "name": "search_candidate",
        "description": "Find candidates whose name contains the given query.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_pipeline_summary",
        "description": "Return totals by stage (count, volume, units) and hot count.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_followups",
        "description": "Active candidates due for follow-up within N days (default 7). Each has an `overdue` flag.",
        "input_schema": {
            "type": "object",
            "properties": {"within_days": {"type": "integer", "default": 7}},
        },
    },
    {
        "name": "create_candidate",
        "description": "Create a new candidate. `name` required. Optional: units, volume, company, nmls, phone, email, city, state, recruiter, notes, source.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "units": {"type": "number"},
                "volume": {"type": "number"},
                "company": {"type": "string"},
                "nmls": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "recruiter": {"type": "string", "enum": ["Justin Neal", "Matt Redding", "Mark Kurth", "Team"]},
                "notes": {"type": "string"},
                "source": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "update_candidate",
        "description": "Update fields on an existing candidate (need page_id from a prior search). Same field set as create_candidate.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "name": {"type": "string"},
                "units": {"type": "number"},
                "volume": {"type": "number"},
                "company": {"type": "string"},
                "nmls": {"type": "string"},
                "phone": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "recruiter": {"type": "string"},
                "notes": {"type": "string"},
                "next_follow_up": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "engagement": {"type": "string"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "move_stage",
        "description": "Move a candidate to a new stage. Auto-applies the priority rule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "stage": {
                    "type": "string",
                    "enum": ["Initial Outreach", "Conversation", "Interview", "Offer", "Hired", "Passed"],
                },
            },
            "required": ["page_id", "stage"],
        },
    },
]

# ---------- speech I/O ----------

def speak(text: str) -> None:
    """Speak text via macOS `say`. Blocks until done."""
    print(f"[Jarvis] {text}")
    subprocess.run(["say", "-v", TTS_VOICE, "-r", TTS_RATE, text], check=False)


def play_chime(freq: int = 880, ms: int = 120) -> None:
    """Quick sine-wave chime so the user knows Jarvis is listening."""
    sr = 22050
    t = np.linspace(0, ms / 1000, int(sr * ms / 1000), endpoint=False)
    audio = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sd.play(audio, samplerate=sr); sd.wait()


def listen_for_wake(porcupine: pvporcupine.Porcupine) -> None:
    """Block until the wake word fires."""
    frames_per_block = porcupine.frame_length
    with sd.RawInputStream(
        samplerate=porcupine.sample_rate, blocksize=frames_per_block,
        dtype="int16", channels=1,
    ) as stream:
        while True:
            data, _ = stream.read(frames_per_block)
            pcm = struct.unpack_from("h" * frames_per_block, data)
            if porcupine.process(pcm) >= 0:
                return


def record_utterance(sample_rate: int = 16000) -> np.ndarray:
    """Record from mic until ~SILENCE_HANG_MS of quiet, or MAX_UTTERANCE_MS."""
    block_ms = 30
    block_size = int(sample_rate * block_ms / 1000)
    chunks: list[np.ndarray] = []
    silent_ms = 0
    elapsed_ms = 0
    triggered = False  # only start the silence countdown after we hear voice

    with sd.InputStream(samplerate=sample_rate, blocksize=block_size,
                        dtype="int16", channels=1) as stream:
        while elapsed_ms < MAX_UTTERANCE_MS:
            block, _ = stream.read(block_size)
            block = block[:, 0] if block.ndim > 1 else block
            chunks.append(block.copy())
            rms = float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))
            if rms >= SILENCE_RMS:
                triggered = True
                silent_ms = 0
            else:
                if triggered:
                    silent_ms += block_ms
                    if silent_ms >= SILENCE_HANG_MS:
                        break
            elapsed_ms += block_ms

    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)


def transcribe(audio: np.ndarray, model: WhisperModel,
               sample_rate: int = 16000) -> str:
    if audio.size == 0:
        return ""
    audio_f32 = audio.astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        audio_f32, language="en", beam_size=1, vad_filter=True,
    )
    return " ".join(s.text.strip() for s in segments).strip()


# ---------- Claude turn ----------

def run_tool(name: str, args: dict) -> str:
    try:
        if name == "search_candidate":
            out = notion_tools.search_candidate(args["query"])
        elif name == "get_pipeline_summary":
            out = notion_tools.get_pipeline_summary()
        elif name == "get_followups":
            out = notion_tools.get_followups(args.get("within_days", 7))
        elif name == "create_candidate":
            out = notion_tools.create_candidate(**args)
        elif name == "update_candidate":
            pid = args.pop("page_id")
            out = notion_tools.update_candidate(pid, **args)
        elif name == "move_stage":
            out = notion_tools.move_stage(args["page_id"], args["stage"])
        else:
            out = {"error": f"unknown tool: {name}"}
    except Exception as e:
        out = {"error": str(e)}
    return json.dumps(out, default=str)


def claude_turn(client: Anthropic, user_text: str, history: list[dict]) -> str:
    """Run a tool-use loop with Claude until it produces a final text reply."""
    history.append({"role": "user", "content": user_text})
    for _ in range(6):  # safety cap
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )
        history.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            # Final text reply -- collect any text blocks
            return " ".join(
                b.text for b in resp.content if b.type == "text"
            ).strip()

        # Execute the tool calls and feed results back.
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result_str = run_tool(block.name, dict(block.input))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
        history.append({"role": "user", "content": tool_results})

    return "I appear to have lost the thread, sir."


# ---------- main loop ----------

def main() -> None:
    for var in ("PICOVOICE_ACCESS_KEY", "ANTHROPIC_API_KEY", "NOTION_TOKEN"):
        if not os.environ.get(var):
            print(f"error: {var} not set. See SETUP-Jarvis.txt.", file=sys.stderr)
            sys.exit(1)

    print("Loading Whisper (this takes ~20s the first run while the model downloads)...")
    whisper_model = WhisperModel(
        WHISPER_MODEL, device="auto", compute_type="int8",
    )
    print(f"Whisper ready ({WHISPER_MODEL}).")

    porcupine = pvporcupine.create(
        access_key=os.environ["PICOVOICE_ACCESS_KEY"],
        keywords=[WAKE_KEYWORD],
    )
    print(f"Listening for \"{WAKE_KEYWORD}\". Press Ctrl+C to stop.")

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Per-session conversation history (resets when restarted).
    history: list[dict] = []

    try:
        while True:
            listen_for_wake(porcupine)
            play_chime()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Wake. Listening...")
            audio = record_utterance()
            user_text = transcribe(audio, whisper_model)
            if not user_text:
                speak("I didn't catch that, sir.")
                continue
            print(f"[You] {user_text}")
            try:
                reply = claude_turn(client, user_text, history)
            except Exception as e:
                speak("I encountered an error, sir.")
                print("ERROR:", e, file=sys.stderr)
                continue
            if reply:
                speak(reply)
            # Trim history if it gets long.
            if len(history) > 30:
                history = history[-20:]
    except KeyboardInterrupt:
        pass
    finally:
        porcupine.delete()


if __name__ == "__main__":
    main()
