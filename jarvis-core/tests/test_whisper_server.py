import subprocess

import httpx
import numpy as np
import pytest

from jarvis import config
from jarvis.speech import server as server_module
from jarvis.speech import stt
from jarvis.speech.server import ServerUnavailable, WhisperServer

AUDIO = (np.sin(np.linspace(0, 2000, 16000)) * 8000).astype(np.int16)


class Ready(WhisperServer):
    ready = True

    def __init__(self):
        super().__init__()
        self._url = "http://127.0.0.1:1"


@pytest.fixture(autouse=True)
def reset_server(monkeypatch):
    monkeypatch.setattr(stt, "server", None)


def test_request_carries_prompt_and_text_format(monkeypatch):
    seen = {}

    def post(url, data, files, timeout):
        seen.update(url=url, data=data, name=files["file"][0], body=files["file"][1][:4])
        return httpx.Response(200, text=" Jarvis, open Safari.\n", request=httpx.Request("POST", url))
    monkeypatch.setattr(server_module.httpx, "post", post)
    assert Ready().transcribe(AUDIO, "hint") == " Jarvis, open Safari.\n"
    assert seen["url"] == "http://127.0.0.1:1/inference"
    assert seen["data"] == {"response_format": "text", "no_timestamps": "true", "temperature": "0.0",
                            "prompt": "hint"}
    assert seen["body"] == b"RIFF"


def test_stt_uses_server_with_the_wake_prompt(monkeypatch):
    calls = []
    srv = Ready()
    monkeypatch.setattr(srv, "transcribe", lambda a, p: calls.append(p) or " (pop) Open Safari. ")
    monkeypatch.setattr(stt, "server", srv)
    monkeypatch.setattr(stt, "_transcribe_cli", lambda a: pytest.fail("CLI used"))
    assert stt.transcribe(AUDIO) == "Open Safari."
    assert calls == [config.WHISPER_PROMPT]


@pytest.mark.parametrize("state", ["none", "not_ready", "fails"])
def test_falls_back_to_cli(state, monkeypatch):
    if state == "not_ready":
        monkeypatch.setattr(stt, "server", WhisperServer())
    elif state == "fails":
        srv = Ready()
        monkeypatch.setattr(srv, "transcribe", lambda a, p: (_ for _ in ()).throw(ServerUnavailable()))
        monkeypatch.setattr(stt, "server", srv)
    monkeypatch.setattr(stt, "_transcribe_cli", lambda a: "from cli")
    assert stt.transcribe(AUDIO) == "from cli"


def test_http_errors_become_unavailable(monkeypatch):
    def post(url, **kw):
        raise httpx.ConnectError("gone")
    monkeypatch.setattr(server_module.httpx, "post", post)
    with pytest.raises(ServerUnavailable):
        Ready().transcribe(AUDIO)


def test_binds_to_localhost_only(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-server"
    binary.write_text("")
    monkeypatch.setattr(config, "WHISPER_SERVER", binary)
    seen = []

    class FakeProcess:
        def __init__(self, argv, **kw):
            seen.append(argv)

        def poll(self):
            return None

    monkeypatch.setattr(server_module.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(server_module.httpx, "get",
                        lambda url, timeout: httpx.Response(200, request=httpx.Request("GET", url)))
    srv = WhisperServer()
    srv.start()
    argv = seen[0]
    assert argv[argv.index("--host") + 1] == "127.0.0.1"
    assert srv.ready


def test_missing_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "WHISPER_SERVER", tmp_path / "nope")
    with pytest.raises(ServerUnavailable):
        WhisperServer().start()
