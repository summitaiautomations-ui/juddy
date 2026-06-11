"""Wake-word detection via openWakeWord.

Uses the bundled pretrained "hey_jarvis" model, so there is nothing to train —
`setup.sh` downloads the model files on first run.
"""
from openwakeword.model import Model

from . import config


class WakeWord:
    def __init__(self):
        # ONNX runtime avoids the tflite-runtime wheel, which is awkward to
        # install on Apple Silicon.
        self._model = Model(
            wakeword_models=[config.WAKE_MODEL],
            inference_framework="onnx",
        )
        self._key = config.WAKE_MODEL

    def reset(self):
        """Clear the rolling activation buffer (call after handling a command)."""
        self._model.reset()

    def detected(self, frame_int16) -> bool:
        """Feed one 80 ms frame; return True if the wake word just fired."""
        scores = self._model.predict(frame_int16)
        return scores.get(self._key, 0.0) >= config.WAKE_THRESHOLD
