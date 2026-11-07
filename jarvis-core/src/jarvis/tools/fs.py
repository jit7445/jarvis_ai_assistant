import os
from pathlib import Path

from jarvis import config
from jarvis.core.result import Result
from jarvis.tools.paths import safe_path

TEXT_SUFFIXES = (".md", ".txt")
MAX_READ_CHARS = 2000
MAX_LISTED = 10


def _note_path(name: str) -> Path:
    name = name.strip()
    if not name.lower().endswith(TEXT_SUFFIXES):
        name += ".md"
    return safe_path(name)


def _display(path: Path) -> str:
    return path.stem if path.suffix.lower() in TEXT_SUFFIXES else path.name


def _spoken_list(items: list[str]) -> str:
    shown = items[:MAX_LISTED]
    text = ", ".join(shown[:-1]) + (" and " if len(shown) > 1 else "") + shown[-1]
    return text + (f", and {len(items) - MAX_LISTED} more" if len(items) > MAX_LISTED else "")


def make_dir(name: str) -> Result:
    path = safe_path(name)
    if path.is_dir():
        return Result(True, f"The folder {path.name} already exists.")
    if path.exists():
        return Result(False, f"There is already a file called {path.name}.")
    path.mkdir(parents=True)
    return Result(True, f"Created the folder {path.name}.")


def write_file(name: str, body: str, confirm: bool = False) -> Result:
    path = _note_path(name)
    if path.is_dir():
        return Result(False, f"{path.stem} is a folder, not a note.")
    existed = path.exists()
    if existed and not confirm:
        return Result(False, f"A note called {path.stem} already exists. Should I overwrite it?",
                      needs_confirmation=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (body.strip() + "\n" if body.strip() else "").encode("utf-8")
    # O_NOFOLLOW: if a symlink is planted between safe_path() and here, fail instead of following it.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return Result(True, f"{'Overwrote' if existed else 'Saved'} the note {path.stem}.")


def read_file(name: str) -> Result:
    path = safe_path(name)
    if not path.exists() and not name.strip().lower().endswith(TEXT_SUFFIXES):
        path = _note_path(name)
    if path.is_dir():
        return Result(False, f"{path.name} is a folder. Ask me what's in your workspace instead.")
    if not path.exists():
        return Result(False, f"I couldn't find a note called {name.strip()}.")
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return Result(False, f"I can only read text notes, and {path.name} isn't one.")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        raw = f.read(MAX_READ_CHARS * 4 + 1)
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return Result(True, f"The note {path.stem} is empty.")
    if len(text) > MAX_READ_CHARS:
        return Result(True, text[:MAX_READ_CHARS] + " ... That's the first part of the note.")
    return Result(True, text)


def list_dir() -> Result:
    root = config.WORKSPACE.resolve(strict=True)
    entries = sorted((p for p in root.iterdir() if not p.name.startswith(".")),
                     key=lambda p: p.name.lower())
    folders = [p.name for p in entries if p.is_dir()]
    notes = [_display(p) for p in entries if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES]
    others = [p.name for p in entries if p.is_file() and p.suffix.lower() not in TEXT_SUFFIXES]
    if not (folders or notes or others):
        return Result(True, "Your workspace is empty.")
    parts = []
    for items, one, many in ((folders, "folder", "folders"), (notes, "note", "notes"),
                             (others, "other file", "other files")):
        if items:
            parts.append(f"{len(items)} {one if len(items) == 1 else many}: {_spoken_list(items)}")
    return Result(True, "Your workspace has " + "; ".join(parts) + ".")
