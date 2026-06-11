"""Text-to-speech via the macOS `say` command.

Claude's replies can contain markdown that sounds wrong read aloud, so we strip
it down to plain prose first.
"""
import re
import subprocess

from . import config

_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_URL = re.compile(r"https?://\S+")
_MD_MARKS = re.compile(r"[*_#>`]+")


def speak_friendly(text: str) -> str:
    """Reduce markdown / code / URLs to something natural to hear."""
    text = _CODE_BLOCK.sub(" (code omitted) ", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _URL.sub(" a link ", text)
    text = _MD_MARKS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


class Speaker:
    def __init__(self):
        self._proc = None

    def say(self, text: str, friendly: bool = True):
        spoken = speak_friendly(text) if friendly else text
        if not spoken:
            return
        cmd = ["say"]
        if config.TTS_VOICE:
            cmd += ["-v", config.TTS_VOICE]
        if config.TTS_RATE:
            cmd += ["-r", str(config.TTS_RATE)]
        cmd.append(spoken)
        self._proc = subprocess.Popen(cmd)
        self._proc.wait()
        self._proc = None

    def stop(self):
        """Interrupt speech in progress (barge-in)."""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
