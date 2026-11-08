import io
import socket
import subprocess
import threading
import time

import httpx
import numpy as np
from scipy.io.wavfile import write

from jarvis import config


class ServerUnavailable(Exception):
    pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class WhisperServer:
    """whisper-server on 127.0.0.1 with the model held in memory, one request at a time."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._url = ""
        self._ready = threading.Event()
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._ready.is_set() and self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Launch and wait until the model is loaded (the first run also compiles Metal)."""
        if not config.WHISPER_SERVER.is_file():
            raise ServerUnavailable("not built")
        port = _free_port()
        self._url = f"http://127.0.0.1:{port}"
        self._process = subprocess.Popen(
            [str(config.WHISPER_SERVER), "-m", str(config.WHISPER_MODEL), "--host", "127.0.0.1",
             "--port", str(port), "-t", "4", "-nt"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + config.WHISPER_SERVER_START_SECONDS
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise ServerUnavailable("exited during start")
            try:
                if httpx.get(f"{self._url}/health", timeout=1.0).status_code == 200:
                    self._ready.set()
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        self.stop()
        raise ServerUnavailable("did not become ready")

    def start_in_background(self) -> None:
        def run():
            try:
                self.start()
            except ServerUnavailable:
                pass
        threading.Thread(target=run, daemon=True).start()

    def transcribe(self, audio: np.ndarray, prompt: str = "", timeout: float = 30.0) -> str:
        if not self.ready:
            raise ServerUnavailable("not running")
        wav = io.BytesIO()
        write(wav, config.SAMPLE_RATE, audio.astype(np.int16))
        fields = {"response_format": "text", "no_timestamps": "true", "temperature": "0.0"}
        if prompt:
            fields["prompt"] = prompt
        with self._lock:
            try:
                response = httpx.post(f"{self._url}/inference", data=fields,
                                      files={"file": ("audio.wav", wav.getvalue(), "audio/wav")},
                                      timeout=timeout)
                response.raise_for_status()
            except httpx.HTTPError:
                raise ServerUnavailable("request failed") from None
        return response.text

    def stop(self) -> None:
        self._ready.clear()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
