import os
import re
from datetime import date
from pathlib import Path

from jarvis import config
from jarvis.research.wiki import Source
from jarvis.tools.paths import safe_path


def slug(topic: str) -> str:
    words = re.findall(r"[a-z0-9]+", topic.lower())
    return "-".join(words)[:60].strip("-") or "topic"


def render(topic: str, summary: str, sources: list[Source], fetched: date) -> str:
    day = fetched.isoformat()
    links = "\n".join(f"- [{s.title}]({s.url}) (fetched {day})" for s in sources)
    return (f"# {topic.strip()}\n\nFetched {day}\n\n## Summary\n\n{summary.strip()}\n\n"
            f"## Sources\n\n{links}\n")


def write(topic: str, summary: str, sources: list[Source], fetched: date) -> Path:
    return save(config.RESEARCH_DIR, f"{fetched.isoformat()}-{slug(topic)}",
                render(topic, summary, sources, fetched))


def save(folder_name: str, stem: str, text: str) -> Path:
    """A new Markdown file in a workspace folder; adds -2, -3... rather than replace one."""
    folder = safe_path(folder_name)
    folder.mkdir(exist_ok=True)
    base = f"{folder_name}/{stem}"
    data = text.encode("utf-8")
    for n in range(1, 100):
        path = safe_path(f"{base}{'' if n == 1 else f'-{n}'}.md")
        try:
            # O_EXCL: never replace an earlier note; O_NOFOLLOW: never write through a planted link.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path
    raise FileExistsError(base)
