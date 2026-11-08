import subprocess
import time
from pathlib import Path
from urllib.parse import quote

from jarvis import config


class NoAccessibility(Exception):
    pass


class WindowNotFound(Exception):
    def __init__(self, reason: str = "not found") -> None:
        super().__init__(reason)
        self.reason = reason


class NoAutomation(WindowNotFound):
    """macOS has not let this app send Apple Events to System Events (error -1743)."""


class NoScreenRecording(WindowNotFound):
    """Window titles are blank to apps without Screen Recording permission."""


# The folder name arrives as an argument, never pasted into the script. The window must be the
# repository's own VS Code window and frontmost before any key is pressed.
_RAISE = '''
on run argv
    set folderName to item 1 of argv
    set sep to " " & (character id 8212) & " "
    tell application "System Events"
        if not (exists process "{process}") then return "no-window"
        tell process "{process}"
            set target to missing value
            repeat with w in windows
                set t to name of w
                if t is folderName or t ends with (sep & folderName) or t contains (sep & folderName & sep) then
                    set target to w
                    exit repeat
                end if
            end repeat
            if target is missing value then return "no-window"
            perform action "AXRaise" of target
            set frontmost to true
        end tell
        delay 0.5
        set frontName to name of (first application process whose frontmost is true)
        if frontName is not "{process}" then return "not-front"
        set t to name of front window of process "{process}"
        if not (t is folderName or t ends with (sep & folderName) or t contains (sep & folderName & sep)) then return "not-front"
        {action}
        return "done"
    end tell
end run
'''
_ENTER = "key code 36"
_PALETTE = '''keystroke "p" using {command down, shift down}
        delay 0.4
        keystroke (item 2 of argv)
        delay 0.7
        key code 36'''


def _run(script: str, *args: str) -> str:
    try:
        result = subprocess.run(["osascript", "-e", script, *args], capture_output=True,
                                text=True, timeout=15)
    except subprocess.TimeoutExpired:
        raise WindowNotFound("timed out, maybe a permission prompt is waiting") from None
    except (OSError, subprocess.SubprocessError):
        raise WindowNotFound("osascript failed") from None
    if "-1743" in result.stderr:
        raise NoAutomation("automation")
    if any(code in result.stderr for code in ("-1719", "-25211", "assistive access")):
        raise NoAccessibility()
    out = result.stdout.strip()
    if out != "done":
        raise WindowNotFound(out or (result.stderr.strip().splitlines() or ["no answer"])[-1][:120])
    return "done"


_SEP = " \u2014 "


def is_repo_window(title: str, folder: str) -> bool:
    """VS Code titles end in the folder name ("file \u2014 folder"); a prefix of another
    folder's name must not count."""
    return title == folder or title.endswith(_SEP + folder) or (_SEP + folder + _SEP) in title


def front_window() -> tuple[str, str] | None:
    """Owner and title of the frontmost ordinary window. Titles need Screen Recording."""
    import Quartz
    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    for w in Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []:
        bounds = w.get("kCGWindowBounds") or {}
        # VS Code keeps an invisible title-bar strip in front of its real window.
        if (w.get("kCGWindowLayer") == 0 and (w.get("kCGWindowAlpha") or 0) > 0
                and bounds.get("Height", 0) > 100):
            return str(w.get("kCGWindowOwnerName") or ""), str(w.get("kCGWindowName") or "")
    return None


def can_read_titles() -> bool:
    import Quartz
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def wait_until_front(folder: Path, seconds: float = 6.0) -> None:
    if not can_read_titles():
        # Accessibility can read and raise windows too; the script fails closed if the
        # project's window is not frontmost afterwards.
        try:
            _run(_RAISE.format(process=config.VSCODE_PROCESS, action=""), folder.name)
        except NoAccessibility:
            raise NoScreenRecording() from None
        return
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        front = front_window()
        if front and front[0] == config.VSCODE_PROCESS and is_repo_window(front[1], folder.name):
            return
        time.sleep(0.2)
    raise WindowNotFound(f"front window stayed {front[0] if front else 'unknown'}")


def open_folder(folder: Path) -> None:
    cli = next((c for c in config.VSCODE_CLI_CANDIDATES if Path(c).is_file()), None)
    argv = [cli, str(folder)] if cli else ["open", "-a", config.VSCODE_APP, str(folder)]
    subprocess.run(argv, check=True, timeout=20, capture_output=True)
    # The code command picks the window inside VS Code, but macOS keeps the app that launched
    # Jarvis (Terminal) in front; activating VS Code without a path brings that window forward.
    subprocess.run(["open", "-a", config.VSCODE_APP], check=True, timeout=15, capture_output=True)


def fill_prompt(folder: Path, prompt: str) -> None:
    """Bring the repository's window forward, then hand Claude Code the prompt (not sent).

    VS Code delivers the link to whichever window is in front, so nothing is handed over until
    that window is verifiably this repository's.
    """
    open_folder(folder)
    wait_until_front(folder)
    url = f"{config.CLAUDE_CODE_URI}?prompt={quote(prompt, safe='')}"
    subprocess.run(["open", url], check=True, timeout=15, capture_output=True)


def press_enter(folder: Path) -> None:
    _run(_RAISE.format(process=config.VSCODE_PROCESS, action=_ENTER), folder.name)


def run_command(folder: Path, title: str) -> None:
    _run(_RAISE.format(process=config.VSCODE_PROCESS, action=_PALETTE), folder.name, title)
