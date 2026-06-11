"""Speech-to-text via faster-whisper, running locally on-device."""
from faster_whisper import WhisperModel

from . import config


class Transcriber:
    def __init__(self):
        self._model = WhisperModel(
            config.STT_MODEL,
            device=config.STT_DEVICE,
            compute_type=config.STT_COMPUTE_TYPE,
        )

    def transcribe(self, audio_float32) -> str:
        """Transcribe a float32 mono [-1, 1] array to text."""
        segments, _ = self._model.transcribe(
            audio_float32,
            language="en",
            beam_size=1,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
