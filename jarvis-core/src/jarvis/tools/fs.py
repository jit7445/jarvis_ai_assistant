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


def _closest(name: str, notes_only: bool) -> Path | None:
    """A workspace item whose name is what was meant: whisper hears "grocery" for groceries,
    "offline" for Offline. Same folder only; never follows anything outside safe_path."""
    from difflib import SequenceMatcher
    wanted = safe_path(name)
    folder = wanted.parent
    if not folder.is_dir():
        return None

    def key(text: str) -> str:
        text = text.lower().strip()
        for suffix in TEXT_SUFFIXES:
            text = text.removesuffix(suffix)
        return text.removesuffix("es") if text.endswith("ies") else text.rstrip("s")

    target = key(wanted.name)
    best, best_score = None, 0.0
    for item in folder.iterdir():
        if item.name.startswith(".") or (notes_only and item.suffix.lower() not in TEXT_SUFFIXES):
            continue
        candidate = key(item.name)
        score = 1.0 if candidate == target else SequenceMatcher(None, candidate, target).ratio()
        if score > best_score:
            best, best_score = item, score
    if best is None or best_score < 0.85:
        return None
    return safe_path(str(best.relative_to(config.WORKSPACE.resolve())))


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
    if not path.exists():
        path = _closest(name, notes_only=True) or path
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


def _trash(path: Path) -> None:
    """Into the macOS Trash, so a misheard delete can be undone from Finder."""
    from Foundation import NSFileManager, NSURL
    ok, _, error = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(
        NSURL.fileURLWithPath_(str(path)), None, None)
    if not ok:
        raise OSError(str(error))


def _workspace_items() -> list[Path]:
    root = config.WORKSPACE.resolve(strict=True)
    return sorted(p for p in root.iterdir() if not p.name.startswith("."))


def delete(name: str, confirm: bool = False) -> Result:
    path = safe_path(name)
    if not path.exists() and not name.strip().lower().endswith(TEXT_SUFFIXES):
        note = _note_path(name)
        path = note if note.exists() else path
    if not path.exists() and not path.is_symlink():
        path = _closest(name, notes_only=False) or path
    if not path.exists() and not path.is_symlink():
        return Result(False, f"I couldn't find {name.strip()} in your workspace.")
    kind = "folder" if path.is_dir() else "note" if path.suffix.lower() in TEXT_SUFFIXES else "file"
    if not confirm:
        return Result(False, f"Move the {kind} {_display(path)} to the Trash?",
                      needs_confirmation=True)
    _trash(path)
    return Result(True, f"Moved the {kind} {_display(path)} to the Trash. You can get it back "
                        "from there.")


def delete_all(confirm: bool = False) -> Result:
    items = _workspace_items()
    if not items:
        return Result(True, "Your workspace is already empty.")
    if not confirm:
        return Result(False, f"Move all {len(items)} items in your workspace to the Trash?",
                      needs_confirmation=True)
    for item in items:
        _trash(item)
    return Result(True, f"Moved {len(items)} items to the Trash. You can get them back from "
                        "there.")
