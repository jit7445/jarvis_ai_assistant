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
    (" Open my Chrome.", "app.open", {"app_name": "Chrome"}),
    (" Open up my Calendar app.", "app.open", {"app_name": "Calendar"}),
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
    " Create a folder.",
    " Create a folder called",
    " Make a note.",
    " open",
    " Open the app.",
    " Open my app.",
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


@pytest.mark.parametrize("spoken, tool, args", [
    ("create a Projects folder", "fs.make_dir", {"name": "Projects"}),
    ("make me a new folder for invoices", "fs.make_dir", {"name": "invoices"}),
    ("add a folder named Travel 2026 to my workspace", "fs.make_dir", {"name": "Travel 2026"}),
    ("I need a folder called Taxes", "fs.make_dir", {"name": "Taxes"}),
    ("new folder Recipes", "fs.make_dir", {"name": "Recipes"}),
    ("can you please set up a directory called Backups for me", "fs.make_dir", {"name": "Backups"}),
    ("let's create a folder called Ideas", "fs.make_dir", {"name": "Ideas"}),
    ("take a note called meeting: call Ravi at 5", "fs.write_file",
     {"name": "meeting", "body": "call Ravi at 5"}),
    ("write a todo note saying finish phase 8", "fs.write_file",
     {"name": "todo", "body": "finish phase 8"}),
    ("new note ideas", "fs.write_file", {"name": "ideas", "body": ""}),
    ("jot down a note called dentist that says Friday at 10", "fs.write_file",
     {"name": "dentist", "body": "Friday at 10"}),
    ("save a note titled plan with the text ship it", "fs.write_file",
     {"name": "plan", "body": "ship it"}),
    ("read me my groceries note", "fs.read_file", {"name": "groceries"}),
    ("read out the note called meeting", "fs.read_file", {"name": "meeting"}),
    ("what's in the note called groceries", "fs.read_file", {"name": "groceries"}),
    ("what does groceries say", "fs.read_file", {"name": "groceries"}),
    ("show me the note called dentist", "fs.read_file", {"name": "dentist"}),
    ("open my note ideas", "fs.read_file", {"name": "ideas"}),
    ("what do I have", "fs.list_dir", {}),
    ("list my files", "fs.list_dir", {}),
    ("show me my notes", "fs.list_dir", {}),
    ("what files do I have in my workspace", "fs.list_dir", {}),
    ("list everything", "fs.list_dir", {}),
    ("tell me what's in my workspace", "fs.list_dir", {}),
    ("launch Safari", "app.open", {"app_name": "Safari"}),
    ("start the music app", "app.open", {"app_name": "music"}),
    ("fire up chrome", "app.open", {"app_name": "chrome"}),
    ("switch to Calendar", "app.open", {"app_name": "Calendar"}),
    ("I want you to open Notes now", "app.open", {"app_name": "Notes"}),
    ("open Terminal", "app.open", {"app_name": "Terminal"}),
    ("launch iTerm", "app.open", {"app_name": "iTerm"}),
])
def test_natural_phrasings(spoken, tool, args):
    assert route(spoken) == Intent(tool, args)


@pytest.mark.parametrize("spoken", [
    # left for the planner: no name, or an app the allowlist does not know
    "Jarvis, make a new folder", "create a folder", "create a folder for", "make a note saying buy milk",
    "open my browser", "run the tests", "open Finder",
    # not commands at all
    "what's the weather today", "stop the music", "make it louder",
    "I need a break",
])
def test_left_for_the_planner(spoken):
    assert route(spoken) is None
