import pytest

from jarvis.core.intent import Intent
from jarvis.core.router import normalise, route


@pytest.mark.parametrize("spoken, tool, args", [
    # the five plan phrases, as typed
    ("create a folder called Research", "fs.make_dir", {"name": "Research"}),
    ("make a note called groceries", "fs.write_file", {"name": "groceries", "body": ""}),
    ("read me groceries", "fs.read_file", {"name": "groceries"}),
    ("what's in my workspace", "fs.list_dir", {}),
    ("open Safari", "app.open", {"app_name": "Safari"}),

    # as whisper actually writes them
    (" Jarvis, create a folder called Research in my workspace.", "fs.make_dir", {"name": "Research"}),
    (" Create a folder in my workspace called Research Jarvis agent.", "fs.make_dir",
     {"name": "Research Jarvis agent"}),
    (" What's in my workspace?", "fs.list_dir", {}),
    (" What’s in my workspace?", "fs.list_dir", {}),
    (" Open Safari.", "app.open", {"app_name": "Safari"}),
    (" Hey Jarvis, open the Notes app, please.", "app.open", {"app_name": "Notes"}),
    (" Read me the note called groceries.", "fs.read_file", {"name": "groceries"}),
    (" Make a note called groceries, saying buy milk and eggs.", "fs.write_file",
     {"name": "groceries", "body": "buy milk and eggs"}),
    (" Can you make a new folder named Project   Alpha?", "fs.make_dir", {"name": "Project Alpha"}),
    ("SHOW ME MY WORKSPACE", "fs.list_dir", {}),
])
def test_routes(spoken, tool, args):
    assert route(spoken) == Intent(tool, args)


@pytest.mark.parametrize("spoken", [
    "",
    "   ",
    " ...",
    " Jarvis.",
    " What's the weather like today?",
    " Delete everything in my workspace.",
    " Create a folder.",
    " Create a folder called",
    " Make a note.",
    " open",
    " Open the app.",
    " Open it.",
    " Thank you.",
    " [BLANK_AUDIO]",
    " creat a foldr called Research",
])
def test_unrecognised_returns_none(spoken):
    assert route(spoken) is None


@pytest.mark.parametrize("junk", [None, 42, b"open safari", ["open safari"]])
def test_non_text_returns_none(junk):
    assert route(junk) is None


def test_never_raises_on_long_input():
    assert route("a" * 100_000) is None


def test_normalise():
    assert normalise(" Jarvis,  Create a  Folder.  ") == "Create a Folder"
