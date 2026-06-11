"""Claude as Jarvis's brain — a thin wrapper over the `claude` CLI.

We shell out to `claude -p` (non-interactive "print" mode) rather than the API
so Jarvis reuses the machine's existing Claude authentication and inherits the
full agent toolset (files, MCP servers, etc.). Conversation continuity comes
from `--continue`, scoped to the isolated workspace directory.
"""
import json
import subprocess

from . import config

PERSONA = (
    "You are Jarvis, a voice assistant running on an always-on Mac mini. "
    "Your replies are read aloud, so keep them short, natural, and "
    "conversational — usually one or two sentences. Do not use markdown, "
    "bullet points, code blocks, or emoji; they get spoken verbatim and sound "
    "wrong. When you take an action, briefly say what you did. If a request is "
    "ambiguous, ask one short clarifying question. Address the user directly "
    "and politely."
)


class Brain:
    def __init__(self):
        self._started = False
        config.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    def ask(self, text: str) -> str:
        cmd = [
            config.CLAUDE_BIN, "-p", text,
            "--output-format", "json",
            "--append-system-prompt", PERSONA,
            "--permission-mode", config.CLAUDE_PERMISSION_MODE,
        ]
        if config.CLAUDE_MODEL:
            cmd += ["--model", config.CLAUDE_MODEL]
        if self._started:
            cmd.append("--continue")  # keep the conversation going

        try:
            out = subprocess.run(
                cmd,
                cwd=str(config.WORKSPACE_DIR),
                capture_output=True,
                text=True,
                timeout=config.CLAUDE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return "Sorry, that took too long. Let's try again."

        if out.returncode != 0:
            err = (out.stderr or "").strip().splitlines()
            detail = err[-1] if err else "unknown error"
            return f"Sorry, I hit a problem talking to Claude: {detail}"

        self._started = True
        return _parse_result(out.stdout)


def _parse_result(stdout: str) -> str:
    stdout = stdout.strip()
    if not stdout:
        return "I didn't get a response."
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout  # fall back to whatever plain text we got
    if isinstance(data, dict):
        return (data.get("result") or "").strip() or "Done."
    return str(data)
