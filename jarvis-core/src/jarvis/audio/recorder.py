import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from jarvis import config

BLOCK = config.SAMPLE_RATE // 10


class Recorder:
    def __init__(self, on_level: Callable[[float], None] | None = None):
        self._on_level = on_level
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time, status) -> None:
        with self._lock:
            self._chunks.append(indata.copy())
        if self._on_level:
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            self._on_level(min(rms / 3000.0, 1.0))

    def start(self) -> None:
        self.stop()
        with self._lock:
            self._chunks = []
        self._stream = sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, dtype="int16",
                                      blocksize=BLOCK, callback=self._callback)
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            chunks, self._chunks = self._chunks, []
        if not chunks:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(chunks).ravel()

    def record_for(self, seconds: float) -> np.ndarray:
        self.start()
        sd.sleep(int(seconds * 1000))
        return self.stop()
