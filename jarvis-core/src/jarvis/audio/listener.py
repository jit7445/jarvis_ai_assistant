import threading
from collections import deque
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from jarvis import config

BLOCK = config.SAMPLE_RATE // 10
PRE_ROLL_BLOCKS = 3
START_BLOCKS = 2
END_SILENCE_BLOCKS = 8
MIN_VOICED_BLOCKS = 4
MAX_BLOCKS = 120
CALIBRATION_BLOCKS = 10
MIN_THRESHOLD = 400.0
NOISE_MULTIPLE = 4.0
RELEASE_RATIO = 0.6


def rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))


class Segmenter:
    """Cuts a stream of 0.1 s blocks into utterances by loudness, against an adaptive noise floor."""

    def __init__(self) -> None:
        self.noise = 100.0
        self._calibration: list[float] = []
        self.reset()

    def reset(self) -> None:
        self._pre: deque[np.ndarray] = deque(maxlen=PRE_ROLL_BLOCKS)
        self._speech: list[np.ndarray] = []
        self._loud = 0
        self._quiet = 0
        self._active = False

    @property
    def threshold(self) -> float:
        return max(MIN_THRESHOLD, self.noise * NOISE_MULTIPLE)

    def feed(self, block: np.ndarray) -> np.ndarray | None:
        level = rms(block)
        if len(self._calibration) < CALIBRATION_BLOCKS:
            self._calibration.append(level)
            self.noise = float(np.mean(self._calibration))
            return None

        if not self._active:
            self._pre.append(block)
            if level > self.threshold:
                self._loud += 1
                if self._loud >= START_BLOCKS:
                    self._active, self._speech, self._quiet = True, list(self._pre), 0
            else:
                self._loud = 0
                self.noise = 0.95 * self.noise + 0.05 * level
            return None

        self._speech.append(block)
        self._quiet = self._quiet + 1 if level < self.threshold * RELEASE_RATIO else 0
        if len(self._speech) >= MAX_BLOCKS:
            # Nobody speaks for 12 s without a pause; this is a fan or traffic. Learn its level.
            self.noise = float(np.median([rms(b) for b in self._speech]))
            self.reset()
            return None
        if self._quiet < END_SILENCE_BLOCKS:
            return None
        speech, voiced = self._speech, len(self._speech) - self._quiet
        self.reset()
        return np.concatenate(speech).ravel() if voiced >= MIN_VOICED_BLOCKS else None


class Listener:
    """Always-on microphone that hands each finished utterance to a callback while enabled."""

    def __init__(self, on_utterance: Callable[[np.ndarray], None],
                 on_level: Callable[[float], None] | None = None) -> None:
        self._on_utterance = on_utterance
        self._on_level = on_level
        self._segmenter = Segmenter()
        self._enabled = threading.Event()
        self._stream: sd.InputStream | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled.is_set()

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if value:
            self._enabled.set()
        else:
            self._enabled.clear()

    def _callback(self, indata, frames, time, status) -> None:
        block = indata[:, 0].copy()
        if self._on_level:
            self._on_level(min(rms(block) / 3000.0, 1.0))
        if not self._enabled.is_set():
            self._segmenter.reset()
            return
        utterance = self._segmenter.feed(block)
        if utterance is not None:
            self._on_utterance(utterance)

    def start(self) -> None:
        self.enabled = True
        self._stream = sd.InputStream(samplerate=config.SAMPLE_RATE, channels=1, dtype="int16",
                                      blocksize=BLOCK, callback=self._callback)
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
