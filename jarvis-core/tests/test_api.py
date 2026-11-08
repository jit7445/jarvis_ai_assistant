import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io.wavfile import write

from jarvis import api, config
from jarvis.speech import stt

from test_assistant import workspace  # noqa: F401  (autouse temp workspace)

PORT = 8765
TOKEN = "s3cret-token"
AUTH = {config.TOKEN_HEADER: TOKEN}


@pytest.fixture
def client():
    commands = []

    def run_command(text):
        commands.append(text)
        return "Created the folder Research."
    c = TestClient(api.create_app(TOKEN, PORT, run_command), base_url=f"http://127.0.0.1:{PORT}")
    c.commands = commands
    return c


def wav(rate=16000, seconds=1.0, dtype=np.int16):
    buf = io.BytesIO()
    write(buf, rate, (np.sin(np.linspace(0, 2000, int(rate * seconds))) * 8000).astype(dtype))
    return buf.getvalue()


@pytest.mark.parametrize("headers", [{}, {config.TOKEN_HEADER: "wrong"}, {config.TOKEN_HEADER: ""},
                                     {"Authorization": f"Bearer {TOKEN}"}])
def test_every_route_needs_the_token(headers, client):
    for method, path in [("get", "/health"), ("get", "/tools"), ("post", "/execute"),
                         ("post", "/transcribe"), ("post", "/command")]:
        assert getattr(client, method)(path, headers=headers).status_code == 401


@pytest.mark.parametrize("host", ["evil.example.com", f"evil.example.com:{PORT}", "localhost:9999",
                                  f"192.168.1.20:{PORT}", f"0.0.0.0:{PORT}"])
def test_foreign_host_header_is_refused(host, client):
    assert client.get("/health", headers={**AUTH, "Host": host}).status_code == 403


def test_empty_token_never_matches():
    c = TestClient(api.create_app("", PORT, lambda t: ""), base_url=f"http://127.0.0.1:{PORT}")
    assert c.get("/health", headers={config.TOKEN_HEADER: ""}).status_code == 401


def test_health_and_tools(client):
    assert client.get("/health", headers=AUTH).json() == {"ok": True, "whisper": "on demand"}
    tools = client.get("/tools", headers=AUTH).json()
    assert tools["tools"]["fs.make_dir"] == {"args": ["name"], "about": "Create a folder. name: the folder name."}
    assert "safari" in tools["apps"] and "You cannot see the user's code" in tools["prompt"]
    assert str(config.WORKSPACE) not in str(tools)


def test_transcribe(client, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", lambda audio: f"heard {audio.size} samples")
    r = client.post("/transcribe", content=wav(), headers=AUTH)
    assert r.json() == {"text": "heard 16000 samples"}


@pytest.mark.parametrize("body", [b"not audio", b"", wav(rate=44100), wav(dtype=np.float32)])
def test_transcribe_refuses_other_audio(body, client, monkeypatch):
    monkeypatch.setattr(stt, "transcribe", lambda audio: pytest.fail("should not transcribe"))
    assert client.post("/transcribe", content=body, headers=AUTH).status_code == 415


def test_too_large_is_refused_before_reading(client):
    r = client.post("/transcribe", content=b"x", headers={**AUTH, "Content-Length": str(10**9)})
    assert r.status_code == 413


def test_execute_runs_through_the_gate(client, workspace):
    r = client.post("/execute", json={"tool": "fs.make_dir", "args": {"name": "Research"}}, headers=AUTH)
    assert r.json() == {"ok": True, "message": "Created the folder Research.", "needs_confirmation": False}
    assert (workspace / "Research").is_dir()


@pytest.mark.parametrize("body", [{"tool": "shell.run", "args": {"cmd": "ls"}},
                                  {"tool": "fs.read_file", "args": {"name": "../../.ssh/id_rsa"}},
                                  {"tool": "fs.make_dir"}, "rm -rf ~", [], {"tool": None}])
def test_execute_refuses_what_the_gate_refuses(body, client):
    r = client.post("/execute", json=body, headers=AUTH)
    assert r.status_code == 422 and r.json()["ok"] is False


def test_execute_can_never_confirm(client, workspace):
    (workspace / "Research").mkdir()
    r = client.post("/execute", json={"tool": "fs.delete_all", "args": {}, "confirm": True}, headers=AUTH)
    assert r.json()["needs_confirmation"] is True
    assert (workspace / "Research").exists()


def test_command_goes_through_the_app_pipeline(client):
    r = client.post("/command", json={"text": "  create a folder called Research "}, headers=AUTH)
    assert r.json() == {"reply": "Created the folder Research."}
    assert client.commands == ["create a folder called Research"]


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": 5}, {"text": "x" * 2001}, ["text"]])
def test_command_needs_text(body, client):
    assert client.post("/command", json=body, headers=AUTH).status_code == 422


def test_docs_pages_are_off(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path, headers=AUTH).status_code == 404


def test_serve_binds_localhost_only(monkeypatch):
    seen = {}

    class FakeServer:
        def __init__(self, cfg):
            seen["host"], seen["port"] = cfg.host, cfg.port

        def run(self):
            pass
    import uvicorn
    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    api.serve(api.create_app(TOKEN, PORT, lambda t: ""), PORT)
    assert seen == {"host": "127.0.0.1", "port": PORT}
