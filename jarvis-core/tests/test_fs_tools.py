import os
from dataclasses import replace

import pytest

from jarvis import config
from jarvis.core.confirm import parse_answer
from jarvis.core.intent import Intent
from jarvis.core.router import route
from jarvis.tools.executor import execute


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(config, "WORKSPACE", ws)
    return ws


@pytest.fixture
def outside(tmp_path):
    out = tmp_path / "outside"
    out.mkdir()
    (out / "secret.txt").write_text("do not touch")
    return out


def snapshot(path):
    return {p.relative_to(path): p.read_bytes() if p.is_file() else None
            for p in sorted(path.rglob("*"))}


def run(spoken):
    intent = route(spoken)
    assert intent is not None, spoken
    return execute(intent)


def test_create_folder(workspace):
    result = run("Jarvis, create a folder called Research.")
    assert result.ok and result.message == "Created the folder Research."
    assert (workspace / "Research").is_dir()


def test_create_existing_folder_is_harmless(workspace):
    (workspace / "Research").mkdir()
    (workspace / "Research" / "keep.md").write_text("keep")
    result = run("create a folder called Research")
    assert result.ok and "already exists" in result.message
    assert (workspace / "Research" / "keep.md").read_text() == "keep"


def test_folder_name_clashing_with_file(workspace):
    (workspace / "Research").write_text("x")
    assert not run("create a folder called Research").ok


def test_write_and_read_note(workspace):
    result = run("make a note called groceries saying buy milk and eggs")
    assert result.ok and result.message == "Saved the note groceries."
    assert (workspace / "groceries.md").read_text() == "buy milk and eggs\n"
    assert run("read me groceries").message == "buy milk and eggs"
    assert run("read me groceries.md").message == "buy milk and eggs"


def test_empty_note(workspace):
    assert run("make a note called ideas").ok
    assert (workspace / "ideas.md").read_text() == ""
    assert run("read me ideas").message == "The note ideas is empty."


def test_overwrite_asks_first_and_changes_nothing(workspace):
    (workspace / "groceries.md").write_text("original\n")
    intent = route("make a note called groceries saying replaced")
    result = execute(intent)
    assert not result.ok and result.needs_confirmation
    assert "Should I overwrite it?" in result.message
    assert (workspace / "groceries.md").read_text() == "original\n"

    confirmed = execute(replace(intent, confirm=True))
    assert confirmed.ok and confirmed.message == "Overwrote the note groceries."
    assert (workspace / "groceries.md").read_text() == "replaced\n"


def test_new_note_does_not_ask(workspace):
    result = run("make a note called fresh saying hello")
    assert result.ok and not result.needs_confirmation


def test_read_missing_note():
    result = run("read me nothing here")
    assert not result.ok and "couldn't find" in result.message


def test_read_folder_and_non_text(workspace):
    (workspace / "Research").mkdir()
    (workspace / "mic_test.wav").write_bytes(b"RIFF")
    assert "is a folder" in run("read me Research").message
    assert "only read text notes" in run("read me mic_test.wav").message


def test_read_long_note_is_cut(workspace):
    (workspace / "long.md").write_text("word " * 1000)
    message = run("read me long").message
    assert message.endswith("That's the first part of the note.")
    assert len(message) < 2100


def test_list_workspace(workspace):
    assert run("what's in my workspace").message == "Your workspace is empty."
    (workspace / "Research").mkdir()
    (workspace / "Projects").mkdir()
    (workspace / "groceries.md").write_text("x")
    (workspace / "mic_test.wav").write_bytes(b"RIFF")
    (workspace / ".hidden").write_text("x")
    assert run("what's in my workspace").message == (
        "Your workspace has 2 folders: Projects and Research; 1 note: groceries; "
        "1 other file: mic_test.wav.")


@pytest.mark.parametrize("intent", [
    Intent("fs.make_dir", {"name": "../escaped"}),
    Intent("fs.make_dir", {"name": "/tmp/escaped"}),
    Intent("fs.make_dir", {"name": "~/escaped"}),
    Intent("fs.write_file", {"name": "../outside/secret.txt", "body": "pwned"}, confirm=True),
    Intent("fs.write_file", {"name": ".env", "body": "KEY=1"}),
    Intent("fs.read_file", {"name": "../outside/secret.txt"}),
    Intent("fs.read_file", {"name": "/etc/passwd"}),
])
def test_escapes_do_nothing(intent, workspace, outside, tmp_path):
    before = snapshot(tmp_path)
    result = execute(intent)
    assert not result.ok
    assert result.message == "I can only work inside your workspace, so I did nothing."
    assert "do not touch" not in result.message and "root:" not in result.message
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("spoken, name", [
    ("read me .env", ".env"),
    ("read me ../../.zshrc", "../../.zshrc"),
    ("create a folder called ../escape", "../escape"),
])
def test_router_keeps_hostile_names_intact_for_the_gate(spoken, name, workspace):
    intent = route(spoken)
    assert intent.args["name"] == name
    assert execute(intent).message == "I can only work inside your workspace, so I did nothing."
    assert list(workspace.iterdir()) == []


def test_symlinked_note_is_not_followed(workspace, outside, tmp_path):
    os.symlink(outside / "secret.txt", workspace / "notes.md")
    before = snapshot(outside)
    assert not execute(Intent("fs.read_file", {"name": "notes"})).ok
    assert not execute(Intent("fs.write_file", {"name": "notes", "body": "x"}, confirm=True)).ok
    assert snapshot(outside) == before


@pytest.mark.parametrize("intent, message", [
    (Intent("shell.run", {"cmd": "rm -rf ~"}), "I didn't understand that, so I did nothing."),
    (Intent("fs.make_dir", {"name": "x", "extra": 1}), "I didn't understand that, so I did nothing."),
    (Intent("app.open", {"app_name": "Terminal"}), "That app isn't on my list, so I didn't open it."),
])
def test_executor_refusals(intent, message, workspace):
    assert execute(intent).message == message
    assert list(workspace.iterdir()) == []


def test_missing_workspace(workspace, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE", workspace / "gone")
    assert execute(Intent("fs.list_dir", {})).message == (
        "Your workspace folder is missing, so I did nothing.")


@pytest.mark.parametrize("spoken, answer", [
    (" Yes.", True), (" Yeah.", True), ("Yes, please.", True), (" Go ahead.", True),
    (" Jarvis, yes.", True), (" Overwrite it.", True),
    (" No.", False), (" No, thanks.", False), (" Cancel.", False), (" Never mind.", False),
    (" [BLANK_AUDIO]", None), (" You", None), (" Thank you.", None), (" Okay.", None),
    (" Yes and delete everything.", None), (" Maybe.", None), ("", None), (None, None),
])
def test_parse_answer(spoken, answer):
    assert parse_answer(spoken) is answer
