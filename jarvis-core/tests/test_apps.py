import subprocess

import pytest

from jarvis import config
from jarvis.core import assistant
from jarvis.core.intent import Intent
from jarvis.core.router import route
from jarvis.tools import apps
from jarvis.tools.executor import execute

from test_assistant import SPEECH, Fake


@pytest.fixture(autouse=True)
def calls(monkeypatch):
    seen = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        assert kwargs.get("shell") is not True
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(apps.subprocess, "run", fake_run)
    return seen


@pytest.mark.parametrize("spoken, app", [
    ("safari", "Safari"), ("Safari", "Safari"), (" SAFARI ", "Safari"),
    ("notes", "Notes"), ("Music", "Music"), ("calendar", "Calendar"),
])
def test_allowlisted_apps_open(spoken, app, calls):
    assert apps.open_app(spoken).message == f"Opening {app}."
    assert calls == [["open", "-a", app]]


@pytest.mark.parametrize("spoken", [
    "Terminal", "iTerm", "Script Editor", "Keychain Access", "System Settings", "Finder",
    "Mail", "", " ", "safari; rm -rf ~", "Safari.app", "/Applications/Safari.app", "-n Safari",
    "safari notes", "../Safari", None, ["Safari"],
])
def test_unlisted_names_raise_and_never_reach_open(spoken, calls):
    with pytest.raises(PermissionError):
        apps.open_app(spoken)
    assert calls == []


@pytest.mark.parametrize("key, app", [("terminal", "Terminal"), ("my shell", "Terminal"),
                                      ("keys", "Keychain Access"), ("settings", "System Settings")])
def test_banned_apps_refused_even_if_allowlisted(key, app, calls, monkeypatch):
    monkeypatch.setitem(config.ALLOWED_APPS, key, app)
    with pytest.raises(PermissionError):
        apps.open_app(key)
    assert calls == []


def test_open_only_ever_gets_mapped_values(calls):
    for name in ["Safari", "Terminal", "notes", "iTerm", "Music", "Chrome", "calendar"]:
        try:
            apps.open_app(name)
        except PermissionError:
            pass
    assert calls and all(argv[:2] == ["open", "-a"] for argv in calls)
    assert {argv[2] for argv in calls} <= set(config.ALLOWED_APPS.values())


def test_default_allowlist_has_no_banned_app():
    for key, app in config.ALLOWED_APPS.items():
        assert key not in config.BANNED_APPS and app.lower() not in config.BANNED_APPS
        assert key == key.lower()


@pytest.mark.parametrize("text, spoken", [
    (" Jarvis, open Safari.", "Opening Safari."),
    ("open the Notes app", "Opening Notes."),
    ("open Terminal", "That app isn't on my list, so I didn't open it."),
    ("open up System Settings", "That app isn't on my list, so I didn't open it."),
])
def test_executor_replies(text, spoken):
    from jarvis.core.wake import split_wake
    command = split_wake(text)
    intent = route(command if command is not None else text)
    assert execute(intent).message == spoken


def test_launch_failure_is_reported(monkeypatch):
    def failing(argv, **kwargs):
        raise subprocess.CalledProcessError(1, argv)
    monkeypatch.setattr(apps.subprocess, "run", failing)
    assert execute(Intent("app.open", {"app_name": "Safari"})).message == "I couldn't open that app."


def test_spoken_end_to_end(calls):
    fake = Fake(" Jarvis, open Safari.")
    assistant.handle(SPEECH, fake.hooks())
    assert fake.spoken == ["Opening Safari."]
    assert calls == [["open", "-a", "Safari"]]
