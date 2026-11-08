import pytest

from jarvis.core import assistant
from jarvis.core.intent import Intent
from jarvis.core.proposal import to_intent
from jarvis.core.router import route
from jarvis.tools import fs
from jarvis.tools.executor import execute

from test_assistant import SPEECH, Fake, workspace  # noqa: F401  (autouse temp workspace)


@pytest.fixture(autouse=True)
def trash(monkeypatch, tmp_path):
    bin_ = tmp_path / "Trash"
    bin_.mkdir()
    monkeypatch.setattr(fs, "_trash", lambda path: path.rename(bin_ / path.name))
    return bin_


def fill(ws):
    (ws / "Projects").mkdir()
    (ws / "groceries.md").write_text("milk\n")
    (ws / "ideas.txt").write_text("x\n")
    (ws / ".hidden").write_text("x\n")


def test_delete_one_asks_then_trashes(workspace, trash):
    fill(workspace)
    first = execute(Intent("fs.delete", {"name": "groceries"}))
    assert first.needs_confirmation and first.message == "Move the note groceries to the Trash?"
    assert (workspace / "groceries.md").exists()
    done = execute(Intent("fs.delete", {"name": "groceries"}, confirm=True))
    assert done.message.startswith("Moved the note groceries to the Trash.")
    assert not (workspace / "groceries.md").exists() and (trash / "groceries.md").exists()


def test_delete_folder_and_missing(workspace):
    fill(workspace)
    assert execute(Intent("fs.delete", {"name": "Projects"})).message == \
        "Move the folder Projects to the Trash?"
    assert execute(Intent("fs.delete", {"name": "nothing"})).message == \
        "I couldn't find nothing in your workspace."


@pytest.mark.parametrize("name", ["../../.zshrc", "/etc/hosts", "~", ".hidden", ".", ""])
def test_delete_cannot_leave_the_workspace(name, workspace, trash):
    fill(workspace)
    result = execute(Intent("fs.delete", {"name": name}, confirm=True))
    assert not result.ok
    assert list(trash.iterdir()) == []


def test_delete_all_asks_with_count_and_skips_hidden(workspace, trash):
    fill(workspace)
    first = execute(Intent("fs.delete_all", {}))
    assert first.needs_confirmation and first.message == \
        "Move all 3 items in your workspace to the Trash?"
    done = execute(Intent("fs.delete_all", {}, confirm=True))
    assert done.message.startswith("Moved 3 items to the Trash.")
    assert [p.name for p in workspace.iterdir()] == [".hidden"]


def test_empty_workspace(workspace):
    assert execute(Intent("fs.delete_all", {})).message == "Your workspace is already empty."


@pytest.mark.parametrize("answer, kept", [(" Yes.", False), (" No.", True), (" [BLANK_AUDIO]", True),
                                          (" Yes, and the rest too.", True)])
def test_spoken_delete_everything(answer, kept, workspace):
    fill(workspace)
    fake = Fake(" Jarvis, delete everything in my workspace.", answer=answer)
    assistant.handle(SPEECH, fake.hooks())
    assert fake.spoken[0] == "Move all 3 items in your workspace to the Trash?"
    assert (workspace / "Projects").exists() is kept


def test_model_cannot_skip_the_question():
    assert to_intent({"tool": "fs.delete_all", "confirm": True}).confirm is False


@pytest.mark.parametrize("spoken, tool, args", [
    ("Delete everything in my workspace.", "fs.delete_all", {}),
    ("clear my workspace", "fs.delete_all", {}), ("empty the workspace", "fs.delete_all", {}),
    ("delete the note called groceries", "fs.delete", {"name": "groceries"}),
    ("remove the Projects folder", "fs.delete", {"name": "Projects"}),
    ("get rid of ideas", "fs.delete", {"name": "ideas"}),
])
def test_delete_phrases(spoken, tool, args):
    assert route(spoken) == Intent(tool, args)


def test_all_my_notes_is_not_everything():
    assert route("delete all my notes") is None


def test_real_trash_api_signature(tmp_path):
    """Calls macOS for a path that does not exist: proves the call shape, trashes nothing."""
    import importlib
    real = importlib.reload(fs)._trash
    with pytest.raises(OSError):
        real(tmp_path / "does-not-exist")
