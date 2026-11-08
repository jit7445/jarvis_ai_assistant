import threading
import time
import wave
from pathlib import Path

import CoreMedia
import numpy as np
import objc
import ScreenCaptureKit as SC
from Foundation import NSObject

SAMPLE_RATE = 16000
LOUD = 0.01


class SystemAudioUnavailable(Exception):
    """No Screen Recording permission, no display, or the stream would not start."""


def _samples(buffer) -> np.ndarray:
    block = CoreMedia.CMSampleBufferGetDataBuffer(buffer)
    if block is None:
        return np.zeros(0, dtype=np.float32)
    length = CoreMedia.CMBlockBufferGetDataLength(block)
    status, data = CoreMedia.CMBlockBufferCopyDataBytes(block, 0, length, None)
    if status != 0 or not data:
        return np.zeros(0, dtype=np.float32)
    # With one channel ScreenCaptureKit delivers plain 32-bit float samples.
    return np.frombuffer(bytes(data), dtype=np.float32)


class _Output(NSObject, protocols=[objc.protocolNamed("SCStreamOutput"),
                                   objc.protocolNamed("SCStreamDelegate")]):
    def initWithOwner_(self, owner):
        self = objc.super(_Output, self).init()
        if self is not None:
            self.owner = owner
        return self

    def stream_didOutputSampleBuffer_ofType_(self, stream, buffer, kind):
        if kind == SC.SCStreamOutputTypeAudio:
            self.owner._audio(_samples(buffer))

    def stream_didStopWithError_(self, stream, error):
        self.owner.failed = True


def _wait(start, timeout: float = 10.0):
    """Run an async ScreenCaptureKit call and return what its completion handler received."""
    done, box = threading.Event(), {}

    def handler(*args):
        box["args"] = args
        done.set()
    start(handler)
    if not done.wait(timeout):
        raise SystemAudioUnavailable("timed out")
    return box["args"]


class SystemAudioRecorder:
    """Records what the Mac plays (any app, not the microphone) into a 16 kHz mono WAV file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.frames = 0
        self.last_loud = time.monotonic()
        self.failed = False
        self._lock = threading.Lock()
        self._wav = None
        self._stream = None
        self._output = None

    @property
    def seconds(self) -> float:
        return self.frames / SAMPLE_RATE

    def _audio(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return
        if float(np.abs(samples).max()) > LOUD:
            self.last_loud = time.monotonic()
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        with self._lock:
            if self._wav is not None:
                self._wav.writeframes(pcm)
                self.frames += samples.size

    def start(self) -> None:
        content, error = _wait(lambda h: SC.SCShareableContent
                               .getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
                                   False, True, h))
        if error is not None or content is None or not content.displays():
            raise SystemAudioUnavailable("no permission or no display")
        config = SC.SCStreamConfiguration.alloc().init()
        config.setCapturesAudio_(True)
        config.setSampleRate_(SAMPLE_RATE)
        config.setChannelCount_(1)
        config.setExcludesCurrentProcessAudio_(True)
        # Audio needs a display filter, but the picture is unused: keep it tiny and rare.
        config.setWidth_(2)
        config.setHeight_(2)
        config.setMinimumFrameInterval_(CoreMedia.CMTimeMake(1, 1))
        flt = SC.SCContentFilter.alloc().initWithDisplay_excludingWindows_(content.displays()[0], [])
        self._output = _Output.alloc().initWithOwner_(self)
        self._stream = SC.SCStream.alloc().initWithFilter_configuration_delegate_(
            flt, config, self._output)
        for kind in (SC.SCStreamOutputTypeScreen, SC.SCStreamOutputTypeAudio):
            ok, error = self._stream.addStreamOutput_type_sampleHandlerQueue_error_(
                self._output, kind, None, None)
            if not ok:
                raise SystemAudioUnavailable("could not add output")
        wav = wave.open(str(self.path), "wb")
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        with self._lock:
            self._wav = wav
        (error,) = _wait(self._stream.startCaptureWithCompletionHandler_)
        if error is not None:
            self._close()
            raise SystemAudioUnavailable("stream did not start")
        self.last_loud = time.monotonic()

    def stop(self) -> float:
        if self._stream is not None:
            try:
                _wait(self._stream.stopCaptureWithCompletionHandler_)
            except SystemAudioUnavailable:
                pass
            self._stream = None
        self._close()
        return self.seconds

    def _close(self) -> None:
        with self._lock:
            if self._wav is not None:
                self._wav.close()
                self._wav = None
