import subprocess
from pathlib import Path

from jarvis import config
from datetime import timedelta

from jarvis.coding import replies, repos, vscode
from jarvis.core.result import Result

ACCEPT = "Claude Code: Accept Proposed Changes"
REJECT = "Claude Code: Reject Proposed Changes"

_AUTOMATION = ("macOS hasn't let your terminal app control System Events. Allow it in System "
               "Settings, Privacy and Security, Automation, then ask again.")
_log = lambda label, text: None


def set_log(log) -> None:
    global _log
    _log = log


_active: Path | None = None
_pending: str | None = None
_last_reply: str | None = None
_on_reply = lambda result: None


def _announce(reply: str | None) -> None:
    global _last_reply
    if reply is None:
        _on_reply(Result(False, "Claude is still working, so I stopped waiting. Its answer will "
                                "be in VS Code."))
        return
    _last_reply = reply
    spoken = replies.speakable(reply)
    _on_reply(Result(True, f"Claude says: {spoken}" if spoken else "Claude finished."))


_watcher = replies.Watcher(_announce)


def on_reply(callback) -> None:
    """Called with a Result when Claude finishes answering a prompt Jarvis sent."""
    global _on_reply
    _on_reply = callback


def last_reply() -> Result:
    if not _last_reply:
        return Result(False, "Claude hasn't answered anything I sent yet.")
    return Result(True, f"Claude said: {replies.speakable(_last_reply)}")


def active() -> Path | None:
    return _active


def open_repo(name: str) -> Result:
    global _active
    folder = repos.find(name)
    if folder is None:
        return Result(False, f"I couldn't find a project called {' '.join(str(name).split())[:60]}.")
    try:
        vscode.open_folder(folder)
    except (OSError, subprocess.SubprocessError):
        return Result(False, "I couldn't open VS Code.")
    _active = folder
    return Result(True, f"Opened {folder.name} in VS Code.")


def _no_project() -> Result:
    return Result(False, "Which project? Say open, then the project name, in VS Code first.")


def ask(prompt: str, confirm: bool = False, spoken: str | None = None) -> Result:
    """First call fills the prompt into Claude Code and asks; the confirmed call sends it."""
    global _pending
    if _active is None:
        return _no_project()
    prompt = " ".join(str(prompt).split())[:config.MAX_PROMPT_CHARS]
    if not prompt:
        return Result(False, "What should I tell Claude?")
    if not confirm:
        try:
            vscode.fill_prompt(_active, prompt)
        except vscode.NoAutomation:
            return Result(False, _AUTOMATION)
        except vscode.NoScreenRecording:
            return Result(False, "I can't see window names, so I gave Claude nothing. Allow "
                                 "Accessibility or Screen Recording for your terminal app in System "
                                 "Settings, Privacy and Security, then restart Jarvis.")
        except vscode.WindowNotFound as error:
            _log("window", f"{_active.name}: {error.reason}")
            return Result(False, f"I couldn't bring the {_active.name} window to the front, so I "
                                 "gave Claude nothing.")
        except (OSError, subprocess.SubprocessError):
            return Result(False, "I couldn't reach Claude Code in VS Code.")
        _pending = prompt
        return Result(False, f"{spoken or f'Send to Claude: {prompt}'}?", needs_confirmation=True)
    if _pending != prompt:
        return Result(False, "That prompt is no longer waiting, so I sent nothing.")
    sent_at = replies.now() - timedelta(seconds=2)
    try:
        vscode.press_enter(_active)
    except vscode.NoAccessibility:
        return Result(False, "macOS won't let me press keys. Allow Accessibility for your terminal "
                             "app, then ask again. The prompt is waiting in Claude Code.")
    except vscode.NoAutomation:
        return Result(False, _AUTOMATION)
    except vscode.WindowNotFound as error:
        _log("window", f"{_active.name}: {error.reason}")
        return Result(False, f"I couldn't bring the {_active.name} window to the front, so I "
                             "didn't send it. The prompt is waiting in Claude Code.")
    finally:
        _pending = None
    _watcher.watch(_active, prompt, sent_at)
    return Result(True, "Sent to Claude Code. I'll tell you what it says.")


def review(confirm: bool = False) -> Result:
    return ask(config.REVIEW_PROMPT, confirm,
               spoken=f"Ask Claude to review the changes in {_active.name if _active else 'it'}")


def decide(accept: bool) -> Result:
    if _active is None:
        return _no_project()
    try:
        vscode.run_command(_active, ACCEPT if accept else REJECT)
    except vscode.NoAccessibility:
        return Result(False, "macOS won't let me press keys. Allow Accessibility for your "
                             "terminal app, then ask again.")
    except vscode.NoAutomation:
        return Result(False, _AUTOMATION)
    except vscode.WindowNotFound:
        return Result(False, f"I couldn't bring the {_active.name} window to the front.")
    return Result(True, "Accepted the changes." if accept else "Rejected the changes.")
