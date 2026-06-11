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
        return self._run(audio_float32, beam_size=1)

    def transcribe_file(self, path) -> str:
        """Transcribe an audio file (any format ffmpeg can read) to text.

        Used for captured recordings (Plaud, mic notes); a higher beam size
        trades a little speed for accuracy on longer, unattended audio.
        """
        return self._run(str(path), beam_size=5)

    def _run(self, audio, beam_size: int) -> str:
        segments, _ = self._model.transcribe(
            audio,
            language="en",
            beam_size=beam_size,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
