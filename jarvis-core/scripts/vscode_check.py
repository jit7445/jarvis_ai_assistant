"""Show what Jarvis can see of VS Code from this terminal. Changes nothing, presses no keys.

    python scripts/vscode_check.py codemining_backend
"""
import subprocess
import sys

from jarvis import config
from jarvis.coding import vscode


def osa(script: str, *args: str) -> tuple[str, str]:
    r = subprocess.run(["osascript", "-e", script, *args], capture_output=True, text=True, timeout=15)
    return r.stdout.strip(), r.stderr.strip()


def main() -> None:
    folder = sys.argv[1] if len(sys.argv) > 1 else "codemining_backend"
    print("Screen Recording (window titles):", vscode.can_read_titles())
    print("front window (Screen Recording view):", vscode.front_window())
    out, err = osa('tell application "System Events" to get name of every window of process "Code"')
    print("VS Code windows (Accessibility view):", out or "-", "|", err or "no error")
    out, err = osa('tell application "System Events" to get name of first application process '
                   'whose frontmost is true')
    print("frontmost app:", out or "-", "|", err or "no error")
    out, err = osa(vscode._RAISE.format(process=config.VSCODE_PROCESS, action=""), folder)
    print(f"raise {folder!r}:", out or "-", "|", err or "no error")


if __name__ == "__main__":
    main()
