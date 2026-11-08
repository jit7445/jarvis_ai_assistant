import os
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

from jarvis import config

_CACHE_SECONDS = 600
_cache: tuple[float, list[Path]] | None = None


def _words(text: str) -> list[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.findall(r"[a-z0-9]+", spaced.lower())


def scan(root: Path, depth: int = config.REPO_SEARCH_DEPTH) -> list[Path]:
    """Folders holding a .git, without descending into them, hidden folders or REPO_SKIP."""
    found: list[Path] = []

    def walk(folder: Path, level: int) -> None:
        try:
            entries = list(os.scandir(folder))
        except OSError:
            return
        if any(e.name == ".git" for e in entries):
            found.append(folder)
            return
        if level >= depth:
            return
        for entry in entries:
            if (entry.name.startswith(".") or entry.name in config.REPO_SKIP
                    or not entry.is_dir(follow_symlinks=False)):
                continue
            walk(Path(entry.path), level + 1)

    walk(root, 0)
    return found


def all_repos(root: Path | None = None) -> list[Path]:
    global _cache
    if root is None and _cache and time.monotonic() - _cache[0] < _CACHE_SECONDS:
        return _cache[1]
    repos = scan(root or Path.home())
    if root is None:
        _cache = (time.monotonic(), repos)
    return repos


def _score(spoken: list[str], folder: str) -> int:
    words = _words(folder)
    if "".join(words) == "".join(spoken):
        return 3
    if set(spoken) <= set(words):
        return 2
    if "".join(spoken) in "".join(words):
        return 1
    # Misheard names: "jervis" for jarvis, "code mining back end" for codemining_backend.
    if SequenceMatcher(None, "".join(spoken), "".join(words)).ratio() >= 0.8:
        return 1
    return 0


def find(name: str, repos: list[Path] | None = None) -> Path | None:
    """The best-named repository, the most recently changed one on a tie."""
    spoken = [w for w in _words(str(name)) if w not in {"the", "my", "project", "repo",
                                                        "repository", "folder"}]
    if not spoken:
        return None
    scored = [(s, p) for p in (repos if repos is not None else all_repos())
              if (s := _score(spoken, p.name))]
    if not scored:
        return None

    def key(item):
        try:
            changed = item[1].stat().st_mtime
        except OSError:
            changed = 0.0
        return (item[0], changed)
    return max(scored, key=key)[1]
