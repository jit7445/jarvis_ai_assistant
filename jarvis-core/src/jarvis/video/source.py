import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jarvis import config

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}

# Fixed scripts with nothing interpolated. "is running" keeps a closed app from being launched.
_BROWSER = ('if application "{app}" is running then tell application "{app}" to '
            'return URL of active tab of front window')
PLAYERS = {
    "Safari": ('if application "Safari" is running then tell application "Safari" to '
               'return URL of current tab of front window', "url"),
    "Google Chrome": (_BROWSER.format(app="Google Chrome"), "url"),
    "Brave Browser": (_BROWSER.format(app="Brave Browser"), "url"),
    "Microsoft Edge": (_BROWSER.format(app="Microsoft Edge"), "url"),
    "Arc": (_BROWSER.format(app="Arc"), "url"),
    "QuickTime Player": ('if application "QuickTime Player" is running then tell application '
                         '"QuickTime Player" to return POSIX path of (file of front document as alias)',
                         "file"),
}


@dataclass(frozen=True)
class Video:
    kind: str  # "youtube" or "file"
    ref: str   # canonical YouTube URL, or an absolute file path
    title: str


class VideoNotFound(Exception):
    pass


class NotAllowed(VideoNotFound):
    """macOS refused to let this process ask the app (Automation permission, error -1743)."""

    def __init__(self, app: str) -> None:
        super().__init__(app)
        self.app = app


def youtube_url(url: object) -> str | None:
    """The canonical watch URL rebuilt from the video ID alone, or None if it is not one."""
    if not isinstance(url, str):
        return None
    try:
        parts = urlparse(url.strip())
    except ValueError:
        return None
    if parts.scheme not in ("https", "http"):
        return None
    host = (parts.hostname or "").lower()
    video_id = None
    if host == "youtu.be":
        video_id = parts.path.lstrip("/").split("/")[0]
    elif host in _YOUTUBE_HOSTS:
        if parts.path == "/watch":
            video_id = parse_qs(parts.query).get("v", [None])[0]
        elif parts.path.startswith(("/shorts/", "/live/", "/embed/")):
            video_id = parts.path.split("/")[2]
    if not video_id or not _VIDEO_ID.match(video_id):
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def media_path(path: object) -> Path | None:
    """A readable video or audio file outside hidden folders and ~/Library, or None."""
    if not isinstance(path, str) or not path.startswith("/") or any(ord(c) < 32 for c in path):
        return None
    try:
        real = Path(path).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    home = Path.home().resolve()
    inside = home in real.parents or Path("/Volumes") in real.parents
    if (not inside or not real.is_file() or real.suffix.lower() not in config.MEDIA_SUFFIXES
            or any(part.startswith(".") for part in real.parts)
            or (home / "Library") in real.parents):
        return None
    return real


class _Denied(Exception):
    pass


def _osascript(script: str) -> str | None:
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True,
                                timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if "-1743" in result.stderr:
        raise _Denied()
    return result.stdout.strip() or None


def _frontmost() -> str:
    try:
        import AppKit
        app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        return str(app.localizedName()) if app else ""
    except Exception:
        return ""


def current() -> Video:
    """The video playing now: the front app first, then any open browser tab or QuickTime."""
    front = _frontmost()
    order = sorted(PLAYERS, key=lambda name: name != front)
    denied = None
    for name in order:
        script, kind = PLAYERS[name]
        try:
            out = _osascript(script)
        except _Denied:
            denied = denied or name
            continue
        if kind == "url" and (url := youtube_url(out)):
            return Video("youtube", url, "")
        if kind == "file" and (path := media_path(out)):
            return Video("file", str(path), path.stem)
    if denied:
        raise NotAllowed(denied)
    raise VideoNotFound("nothing playing")


def find(query: str) -> Video:
    """The most recently changed media file in the home folder whose name contains the query."""
    words = " ".join(str(query).split())
    if not words or len(words) > 100 or any(ord(c) < 32 for c in words):
        raise VideoNotFound(query)
    try:
        out = subprocess.run(["mdfind", "-onlyin", str(Path.home()), "-name", words],
                             capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        raise VideoNotFound(query) from None
    matches = [p for line in out.splitlines() if (p := media_path(line))]
    if not matches:
        raise VideoNotFound(query)
    best = max(matches, key=lambda p: p.stat().st_mtime)
    return Video("file", str(best), best.stem)
