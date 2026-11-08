import os
import subprocess
from pathlib import Path

import pytest

from jarvis import coding, config
from jarvis.coding import repos, vscode
from jarvis.core import assistant
from jarvis.core.intent import Intent
from jarvis.core.proposal import to_intent
from jarvis.core.router import route
from jarvis.tools.executor import execute
from jarvis.tools.registry import InvalidIntent

from test_assistant import SPEECH, Fake, workspace  # noqa: F401  (autouse temp workspace)

EM = "—"


class FakeCode:
    def __init__(self):
        self.calls = []
        self.fill_error = self.enter_error = None

    def open_folder(self, folder):
        self.calls.append(("open", folder.name))

    def fill_prompt(self, folder, prompt):
        if self.fill_error:
            raise self.fill_error
        self.calls.append(("fill", folder.name, prompt))

    def press_enter(self, folder):
        if self.enter_error:
            raise self.enter_error
        self.calls.append(("enter", folder.name))

    def run_command(self, folder, title):
        self.calls.append(("command", folder.name, title))


@pytest.fixture
def code(monkeypatch, tmp_path):
    fake = FakeCode()
    for name in ("open_folder", "fill_prompt", "press_enter", "run_command"):
        monkeypatch.setattr(vscode, name, getattr(fake, name))
    repo = tmp_path / "jarvis_ai_assistant"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.setattr(repos, "all_repos", lambda root=None: [repo])
    monkeypatch.setattr(coding, "_active", None)
    monkeypatch.setattr(coding, "_pending", None)
    monkeypatch.setattr(coding, "_last_reply", None)
    fake.watched = []
    monkeypatch.setattr(coding, "_watcher", type("W", (), {
        "watch": lambda self, folder, prompt, since: fake.watched.append((folder.name, prompt))})())
    return fake


# Finding repositories

def make_tree(root: Path, *paths: str) -> None:
    for p in paths:
        (root / p).mkdir(parents=True, exist_ok=True)


def test_scan_finds_repos_and_skips_private_and_heavy_folders(tmp_path):
    make_tree(tmp_path, "Desktop/app/.git", "Desktop/app/sub/.git", "code/api/.git",
              ".hidden/secret/.git", "Library/x/.git", "web/node_modules/pkg/.git",
              "a/b/c/d/e/f/deep/.git")
    found = {p.relative_to(tmp_path).as_posix() for p in repos.scan(tmp_path)}
    assert found == {"Desktop/app", "code/api"}


def test_scan_does_not_follow_symlinks(tmp_path):
    make_tree(tmp_path, "real/.git")
    (tmp_path / "link").symlink_to(tmp_path / "real")
    assert [p.name for p in repos.scan(tmp_path)] == ["real"]


@pytest.mark.parametrize("spoken, expected", [
    ("jarvis", "jarvis"), ("jarvis ai assistant", "jarvis_ai_assistant"),
    ("my jarvis ai assistant project", "jarvis_ai_assistant"), ("syndicate fe fork", "syndicate-fe-fork"),
    ("reverse engineering agent", "Reverse_engineering_agent"), ("tutor ai frontend", "tutorAiFrontend"),
    ("nothing like this", None), ("the project", None),
])
def test_find_by_spoken_name(spoken, expected, tmp_path):
    names = ["jarvis", "jarvis_ai_assistant", "syndicate-fe-fork", "syndicate-be-fork",
             "Reverse_engineering_agent", "tutorAiFrontend"]
    paths = [tmp_path / n for n in names]
    for p in paths:
        p.mkdir()
    found = repos.find(spoken, paths)
    assert (found.name if found else None) == expected


def test_tie_goes_to_most_recent(tmp_path):
    old, new = tmp_path / "a" / "shop-api", tmp_path / "b" / "shop-api"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    os.utime(old, (1, 1))
    assert repos.find("shop api", [old, new]) == new


# Window matching: never a different repository whose name merely starts the same

@pytest.mark.parametrize("title, folder, ok", [
    (f"Claude Code {EM} jarvis", "jarvis", True),
    ("jarvis", "jarvis", True),
    (f"app.py {EM} jarvis {EM} Profile", "jarvis", True),
    (f"Claude Code {EM} jarvis_ai_assistant", "jarvis", False),
    (f"Claude Code {EM} my-jarvis", "jarvis", False),
    (f"jarvis.md {EM} notes", "jarvis", False),
    ("", "jarvis", False),
])
def test_repo_window_titles(title, folder, ok):
    assert vscode.is_repo_window(title, folder) is ok


def test_wait_until_front_fails_closed(monkeypatch):
    monkeypatch.setattr(vscode, "can_read_titles", lambda: True)
    monkeypatch.setattr(vscode, "front_window", lambda: ("Code", f"x {EM} other"))
    with pytest.raises(vscode.WindowNotFound):
        vscode.wait_until_front(Path("/x/jarvis"), seconds=0.3)


def test_fill_prompt_waits_for_window_then_sends_encoded_link(monkeypatch):
    seen = []
    monkeypatch.setattr(vscode, "open_folder", lambda f: seen.append(("open", f.name)))
    monkeypatch.setattr(vscode, "wait_until_front", lambda f: seen.append(("front", f.name)))
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw: seen.append(argv))
    vscode.fill_prompt(Path("/x/jarvis"), "add a login page & tests; rm -rf ~ #now")
    assert seen[:2] == [("open", "jarvis"), ("front", "jarvis")]
    assert seen[2] == ["open", "vscode://anthropic.claude-code/open?prompt="
                       "add%20a%20login%20page%20%26%20tests%3B%20rm%20-rf%20~%20%23now"]


def test_keypress_script_gets_folder_as_argument_not_code(monkeypatch):
    seen = []
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw: seen.append(argv) or
                        subprocess.CompletedProcess(argv, 0, stdout="done\n", stderr=""))
    vscode.press_enter(Path('/x/evil" & do shell script "rm'))
    argv = seen[0]
    assert argv[:2] == ["osascript", "-e"] and argv[3] == 'evil" & do shell script "rm'
    assert "evil" not in argv[2]


@pytest.mark.parametrize("stdout, stderr, error", [
    ("not-front\n", "", vscode.WindowNotFound), ("no-window\n", "", vscode.WindowNotFound),
    ("", "execution error: not allowed assistive access. (-1719)", vscode.NoAccessibility),
])
def test_keypress_failures(stdout, stderr, error, monkeypatch):
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw:
                        subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=stderr))
    with pytest.raises(error):
        vscode.press_enter(Path("/x/jarvis"))


# The flow: open, fill, read back, send only on yes

def test_open_then_ask_then_send(code):
    assert execute(Intent("code.open_repo", {"name": "jarvis ai assistant"})).message == \
        "Opened jarvis_ai_assistant in VS Code."
    first = execute(Intent("code.ask_claude", {"prompt": "add a login page"}))
    assert first.needs_confirmation and first.message == "Send to Claude: add a login page?"
    assert ("enter", "jarvis_ai_assistant") not in code.calls
    sent = execute(Intent("code.ask_claude", {"prompt": "add a login page"}, confirm=True))
    assert sent.message == "Sent to Claude Code. I'll tell you what it says."
    assert code.watched == [("jarvis_ai_assistant", "add a login page")]
    assert code.calls == [("open", "jarvis_ai_assistant"),
                          ("fill", "jarvis_ai_assistant", "add a login page"),
                          ("enter", "jarvis_ai_assistant")]


def test_nothing_without_an_open_project(code):
    assert execute(Intent("code.ask_claude", {"prompt": "x"})).message.startswith("Which project?")
    assert code.calls == []


def test_unknown_project(code, monkeypatch):
    monkeypatch.setattr(repos, "all_repos", lambda root=None: [])
    assert execute(Intent("code.open_repo", {"name": "zebra"})).message == \
        "I couldn't find a project called zebra."


def test_confirm_cannot_send_a_different_prompt(code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    execute(Intent("code.ask_claude", {"prompt": "add a login page"}))
    result = execute(Intent("code.ask_claude", {"prompt": "delete the repo"}, confirm=True))
    assert result.message == "That prompt is no longer waiting, so I sent nothing."
    assert not any(c[0] == "enter" for c in code.calls)


def test_wrong_window_gives_claude_nothing(code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    code.fill_error = vscode.WindowNotFound()
    result = execute(Intent("code.ask_claude", {"prompt": "x"}))
    assert not result.needs_confirmation and "gave Claude nothing" in result.message


@pytest.mark.parametrize("error, phrase", [(vscode.NoAccessibility(), "Allow Accessibility"),
                                           (vscode.WindowNotFound(), "didn't send it")])
def test_send_failures_leave_prompt_waiting(error, phrase, code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    execute(Intent("code.ask_claude", {"prompt": "x"}))
    code.enter_error = error
    result = execute(Intent("code.ask_claude", {"prompt": "x"}, confirm=True))
    assert phrase in result.message and "waiting in Claude Code" in result.message


@pytest.mark.parametrize("answer, sent", [(" Yes.", True), (" No.", False), (" [BLANK_AUDIO]", False),
                                          (" Yes and also delete everything.", False)])
def test_spoken_yes_is_required(answer, sent, code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    fake = Fake(" Jarvis, tell Claude to add a login page.", answer=answer)
    assistant.handle(SPEECH, fake.hooks())
    assert fake.spoken[0] == "Send to Claude: add a login page?"
    assert (("enter", "jarvis_ai_assistant") in code.calls) is sent


def test_review_reads_back_short_and_sends_fixed_prompt(code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    r = execute(Intent("code.review", {}))
    assert r.message == "Ask Claude to review the changes in jarvis_ai_assistant?"
    assert code.calls[-1] == ("fill", "jarvis_ai_assistant", config.REVIEW_PROMPT)
    assert execute(Intent("code.review", {}, confirm=True)).message.startswith("Sent to Claude Code.")


@pytest.mark.parametrize("tool, title, spoken", [
    ("code.accept", "Claude Code: Accept Proposed Changes", "Accepted the changes."),
    ("code.reject", "Claude Code: Reject Proposed Changes", "Rejected the changes."),
])
def test_voice_approval(tool, title, spoken, code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    assert execute(Intent(tool, {})).message == spoken
    assert code.calls[-1] == ("command", "jarvis_ai_assistant", title)


def test_planner_cannot_preconfirm():
    assert to_intent({"tool": "code.ask_claude", "args": {"prompt": "x"}, "confirm": True}).confirm is False
    assert to_intent({"tool": "code.ask_claude", "args": {"prompt": "x", "confirm": True}}).confirm is False
    with pytest.raises(InvalidIntent):
        to_intent({"tool": "code.ask_claude", "args": {}})


@pytest.mark.parametrize("spoken, args", [
    ("open, Jarvis, open, demo repo in BS code.", {"name": "demo"}),
    ("find repo, call code mining backend and open it.", {"name": "code mining backend"}),
    ("open the project called livedoc", {"name": "livedoc"}),
    ("open demo repo in V.S. code", {"name": "demo"}),
])
def test_misheard_and_loose_open_phrases(spoken, args):
    assert route(spoken) == Intent("code.open_repo", args)


@pytest.mark.parametrize("spoken", ["tell cloud to add a login page", "have Claude add a login page",
                                    "get Claude to add a login page", "let Claude add a login page"])
def test_loose_claude_phrases(spoken):
    assert route(spoken) == Intent("code.ask_claude", {"prompt": "add a login page"})


def test_open_unknown_app_falls_back_to_a_project(monkeypatch, tmp_path):
    repo = tmp_path / "livedoc"
    repo.mkdir()
    monkeypatch.setattr(repos, "all_repos", lambda root=None: [repo])
    assert route("open livedoc") == Intent("code.open_repo", {"name": "livedoc"})
    assert route("open Safari") == Intent("app.open", {"app_name": "Safari"})
    assert route("open Terminal") == Intent("app.open", {"app_name": "Terminal"})


@pytest.mark.parametrize("spoken, folder", [
    ("jervis", "jarvis"), ("code mining back end", "codemining_backend"), ("live doc", "livedoc"),
])
def test_misheard_project_names(spoken, folder, tmp_path):
    paths = [tmp_path / n for n in ("jarvis", "codemining_backend", "livedoc", "moviessite")]
    for p in paths:
        p.mkdir()
    assert repos.find(spoken, paths).name == folder


# Routing

@pytest.mark.parametrize("spoken, tool, args", [
    ("open jarvis in VS Code", "code.open_repo", {"name": "jarvis"}),
    ("open my jarvis ai assistant project in vscode", "code.open_repo", {"name": "jarvis ai assistant"}),
    ("open VS Code with syndicate fe fork", "code.open_repo", {"name": "syndicate fe fork"}),
    ("Jarvis, tell Claude to add a login page", "code.ask_claude", {"prompt": "add a login page"}),
    ("ask Claude Code to write tests for the router", "code.ask_claude",
     {"prompt": "write tests for the router"}),
    ("send to Claude: fix the typo in README", "code.ask_claude", {"prompt": "fix the typo in README"}),
    ("review the code", "code.review", {}), ("ask Claude to review my changes", "code.review", {}),
    ("accept the changes", "code.accept", {}), ("approve the edits", "code.accept", {}),
    ("reject the changes", "code.reject", {}),
])
def test_coding_phrases(spoken, tool, args):
    assert route(spoken) == Intent(tool, args)


def test_arguments_beside_tool_are_accepted():
    assert to_intent({"tool": "code.open_repo", "name": "codemining_backend"}).args == {
        "name": "codemining_backend"}
    with pytest.raises(InvalidIntent):
        to_intent({"tool": "code.open_repo", "project": "x"})


@pytest.mark.parametrize("spoken, prompt", [
    ("Explain the code of code mining.", "Explain the code of code mining"),
    ("explain this code", "explain this code"),
    ("walk me through the codebase", "walk me through the codebase"),
    ("what does the code in auth do", "what does the code in auth do"),
    ("summarize the repo", "summarize the repo"),
])
def test_code_questions_go_to_claude(spoken, prompt):
    assert route(spoken) == Intent("code.ask_claude", {"prompt": prompt})


@pytest.mark.parametrize("spoken", ["read groceries", "read me my groceries note", "explain black holes"])
def test_not_code_questions(spoken):
    assert route(spoken) is None or route(spoken).tool != "code.ask_claude"


def test_planner_prompt_routes_code_questions_to_claude():
    from jarvis.planner.prompt import system_prompt
    assert "You cannot see the user's code" in system_prompt()



# Reading Claude's answer back

import json
from datetime import datetime, timedelta, timezone

from jarvis.coding import replies

T0 = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)


def ts(seconds):
    return (T0 + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def write_log(folder, monkeypatch, tmp_path, rows):
    monkeypatch.setattr(config, "CLAUDE_PROJECTS", tmp_path / "projects")
    d = replies.project_dir(folder)
    d.mkdir(parents=True)
    (d / "session.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def user(text, t):
    return {"type": "user", "timestamp": ts(t), "message": {"role": "user", "content": text}}


def said(text, t, req, stop=None, side=False):
    return {"type": "assistant", "timestamp": ts(t), "requestId": req, "isSidechain": side,
            "message": {"role": "assistant", "stop_reason": stop,
                        "content": [{"type": "text", "text": text}] if text else
                                   [{"type": "thinking", "thinking": "hmm"}]}}


def test_project_dir_matches_claude_code_naming():
    assert replies.project_dir(Path("/Users/x/projects/Reverse_engineering_agent")).name == \
        "-Users-x-projects-Reverse-engineering-agent"


def test_reply_found_after_the_prompt_only(monkeypatch, tmp_path):
    folder = Path("/Users/x/codemining")
    write_log(folder, monkeypatch, tmp_path, [
        user("explain this code", -100), said("Old answer.", -90, "r0", "end_turn"),
        user("explain this code", 5),
        said("Reading files.", 6, "r1", "tool_use"),
        said("", 9, "r1", "tool_use"),
        said("This is a Flask API.", 20, "r2"), said("It has three routes.", 21, "r2"),
        said("A subagent note.", 21, "r2", "end_turn", side=True),
        said("", 22, "r2", "end_turn"),
    ])
    assert replies.find_reply(folder, "explain this code", T0) == \
        "This is a Flask API.\n\nIt has three routes."


def test_no_reply_while_claude_is_working(monkeypatch, tmp_path):
    folder = Path("/Users/x/codemining")
    write_log(folder, monkeypatch, tmp_path, [user("explain this code", 5),
                                              said("Reading.", 6, "r1", "tool_use")])
    assert replies.find_reply(folder, "explain this code", T0) is None
    assert replies.find_reply(Path("/Users/x/other"), "explain this code", T0) is None


def test_speakable_drops_code_and_markdown():
    text = "## Summary\n**Flask** API with `routes`.\n```python\nimport os\n```\nSee [docs](http://x)."
    assert replies.speakable(text) == "Summary Flask API with routes. (code shown in VS Code) See docs."
    long = replies.speakable("This is a sentence. " * 100)
    assert long.endswith("The rest is in VS Code.") and len(long) < config.SPOKEN_REPLY_CHARS + 40


def test_watcher_announces_once_and_newer_prompt_wins(monkeypatch):
    heard, answers = [], iter([None, "first done"])
    monkeypatch.setattr(replies, "find_reply", lambda f, p, s: "done" if p == "second" else next(answers))
    w = replies.Watcher(heard.append, poll=0)
    w._generation = 5
    w._run(4, Path("/x"), "first", T0)
    assert heard == []
    w._run(5, Path("/x"), "second", T0)
    assert heard == ["done"]


def test_announcement_and_repeat(code):
    spoken = []
    coding.on_reply(spoken.append)
    coding._announce("**It is** a Flask API.")
    assert spoken[-1].message == "Claude says: It is a Flask API."
    assert execute(Intent("code.last_reply", {})).message == "Claude said: It is a Flask API."
    coding._announce(None)
    assert spoken[-1].message.startswith("Claude is still working")


@pytest.mark.parametrize("spoken", ["what did Claude say", "read me Claude's answer", "repeat the answer",
                                    "what was cloud's reply", "read what Claude said again"])
def test_repeat_phrases(spoken):
    assert route(spoken) == Intent("code.last_reply", {})


def test_without_screen_recording_accessibility_checks_the_window(monkeypatch):
    monkeypatch.setattr(vscode, "can_read_titles", lambda: False)
    seen = []
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw: seen.append(argv) or
                        subprocess.CompletedProcess(argv, 0, stdout="done\n", stderr=""))
    vscode.wait_until_front(Path("/x/jarvis"))
    assert seen[0][3] == "jarvis" and "key code" not in seen[0][2]


@pytest.mark.parametrize("stdout, stderr, error", [
    ("not-front\n", "", vscode.WindowNotFound),
    ("", "not allowed assistive access (-1719)", vscode.NoScreenRecording),
])
def test_without_either_permission_nothing_is_handed_over(stdout, stderr, error, monkeypatch):
    monkeypatch.setattr(vscode, "can_read_titles", lambda: False)
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw:
                        subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=stderr))
    with pytest.raises(error):
        vscode.wait_until_front(Path("/x/jarvis"))


def test_screen_recording_message(code):
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    code.fill_error = vscode.NoScreenRecording()
    assert "Allow Accessibility or Screen Recording" in execute(
        Intent("code.ask_claude", {"prompt": "x"})).message


def test_open_folder_also_activates_vscode(monkeypatch):
    seen = []
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw: seen.append(argv))
    vscode.open_folder(Path("/x/jarvis"))
    assert seen[-1] == ["open", "-a", "Visual Studio Code"]
    assert seen[0][-1] == "/x/jarvis"



@pytest.mark.parametrize("stdout, stderr, error, reason", [
    ("", "System Events got an error: Not authorized to send Apple events to System Events. (-1743)",
     vscode.NoAutomation, "automation"),
    ("no-window\n", "", vscode.WindowNotFound, "no-window"),
    ("not-front\n", "", vscode.WindowNotFound, "not-front"),
    ("", "syntax error: something (-2741)", vscode.WindowNotFound, "syntax error: something (-2741)"),
])
def test_window_failures_say_why(stdout, stderr, error, reason, monkeypatch):
    monkeypatch.setattr(vscode.subprocess, "run", lambda argv, **kw:
                        subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=stderr))
    with pytest.raises(error) as caught:
        vscode.press_enter(Path("/x/jarvis"))
    assert caught.value.reason == reason


def test_timeout_is_explained(monkeypatch):
    def slow(argv, **kw):
        raise subprocess.TimeoutExpired(argv, 15)
    monkeypatch.setattr(vscode.subprocess, "run", slow)
    with pytest.raises(vscode.WindowNotFound) as caught:
        vscode.press_enter(Path("/x/jarvis"))
    assert "permission prompt" in caught.value.reason


def test_automation_refusal_is_spoken_and_reason_logged(code):
    logged = []
    coding.set_log(lambda label, text: logged.append((label, text)))
    execute(Intent("code.open_repo", {"name": "jarvis ai assistant"}))
    code.fill_error = vscode.NoAutomation("automation")
    assert "control System Events" in execute(Intent("code.ask_claude", {"prompt": "x"})).message
    code.fill_error = vscode.WindowNotFound("not-front")
    execute(Intent("code.ask_claude", {"prompt": "x"}))
    assert logged[-1] == ("window", "jarvis_ai_assistant: not-front")


@pytest.mark.skipif(not Path("/usr/bin/osascript").exists(), reason="macOS only")
def test_frontmost_check_really_runs():
    """Mocked tests missed an AppleScript precedence error; run the real expression."""
    line = next(l.strip() for l in vscode._RAISE.splitlines() if "whose frontmost is true" in l)
    expr = line.removeprefix("set frontName to ")
    r = subprocess.run(["osascript", "-e", f'tell application "System Events" to return {expr}'],
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0 and r.stdout.strip(), r.stderr


def test_raise_script_compiles(tmp_path):
    if not Path("/usr/bin/osacompile").exists():
        pytest.skip("macOS only")
    for action in ("", vscode._ENTER, vscode._PALETTE):
        script = vscode._RAISE.format(process="Code", action=action)
        r = subprocess.run(["osacompile", "-o", str(tmp_path / "s.scpt"), "-e", script],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
