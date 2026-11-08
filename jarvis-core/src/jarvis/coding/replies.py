import json
import re
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from jarvis import config

_CODE_BLOCK = re.compile(r"```.*?(?:```|$)", re.DOTALL)
_MARKUP = re.compile(r"[*_#`>|~]+|\[([^\]]*)\]\([^)]*\)")


def project_dir(folder: Path) -> Path:
    return config.CLAUDE_PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(folder))


def _when(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(str(row.get("timestamp")).replace("Z", "+00:00"))
    except ValueError:
        return None


def _texts(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    return [c["text"] for c in content
            if isinstance(c, dict) and c.get("type") == "text" and isinstance(c.get("text"), str)]


def _rows(path: Path) -> list[dict]:
    rows = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and not row.get("isSidechain"):
                    rows.append(row)
    except OSError:
        pass
    return rows


def find_reply(folder: Path, prompt: str, since: datetime) -> str | None:
    """Claude's finished answer to this prompt, sent after `since`, or None while it works."""
    folder_dir = project_dir(folder)
    try:
        logs = sorted(folder_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    for log in logs[:5]:
        if log.stat().st_mtime < since.timestamp() - 5:
            continue
        rows = _rows(log)
        start = next((i for i, r in enumerate(rows) if r.get("type") == "user"
                      and (_when(r) or since) >= since
                      and any(prompt in t for t in _texts((r.get("message") or {}).get("content")))),
                     None)
        if start is None:
            continue
        for row in rows[start + 1:]:
            message = row.get("message") or {}
            if row.get("type") == "assistant" and message.get("stop_reason") == "end_turn":
                request = row.get("requestId")
                parts = [t for r in rows[start + 1:] if r.get("type") == "assistant"
                         and r.get("requestId") == request
                         for t in _texts((r.get("message") or {}).get("content"))]
                return "\n\n".join(p.strip() for p in parts if p.strip())
        return None
    return None


def speakable(text: str, limit: int = config.SPOKEN_REPLY_CHARS) -> str:
    """Markdown and code blocks do not read aloud well; the full answer stays in VS Code."""
    text = _CODE_BLOCK.sub(" (code shown in VS Code) ", text)
    text = " ".join(_MARKUP.sub(lambda m: m.group(1) or "", text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    cut = cut[:end + 1] if end > limit // 3 else cut.rsplit(" ", 1)[0] + "..."
    return f"{cut} The rest is in VS Code."


class Watcher:
    """Waits in the background for Claude's answer; a newer prompt replaces an older wait."""

    def __init__(self, announce: Callable[[str | None], None], poll: float = 2.0) -> None:
        self.announce, self.poll = announce, poll
        self._generation = 0
        self._lock = threading.Lock()

    def watch(self, folder: Path, prompt: str, since: datetime) -> None:
        with self._lock:
            self._generation += 1
            generation = self._generation
        threading.Thread(target=self._run, args=(generation, folder, prompt, since),
                         daemon=True).start()

    def _run(self, generation: int, folder: Path, prompt: str, since: datetime) -> None:
        deadline = time.monotonic() + config.CLAUDE_REPLY_WAIT_SECONDS
        while time.monotonic() < deadline:
            if generation != self._generation:
                return
            reply = find_reply(folder, prompt, since)
            if reply is not None:
                if generation == self._generation:
                    self.announce(reply)
                return
            time.sleep(self.poll)
        if generation == self._generation:
            self.announce(None)


def now() -> datetime:
    return datetime.now(timezone.utc)
