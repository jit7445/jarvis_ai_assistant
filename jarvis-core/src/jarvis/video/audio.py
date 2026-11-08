import subprocess
from pathlib import Path

from jarvis import config

WAV_BYTES_PER_SECOND = 16000 * 2


class AudioUnavailable(Exception):
    pass


class TooLong(Exception):
    def __init__(self, seconds: float) -> None:
        super().__init__(seconds)
        self.seconds = seconds


def ffmpeg() -> str | None:
    return next((p for p in config.FFMPEG_CANDIDATES if Path(p).is_file()), None)


def download_youtube(url: str, folder: Path) -> tuple[Path, str]:
    """The audio track of a canonical YouTube URL, and the video's title."""
    import yt_dlp
    options = {
        "format": "bestaudio[ext=m4a]/bestaudio", "outtmpl": str(folder / "audio.%(ext)s"),
        "quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True,
        "socket_timeout": 20, "max_filesize": 300 * 1024 * 1024,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("is_live"):
                raise AudioUnavailable("live stream")
            if (info.get("duration") or 0) > config.MAX_VIDEO_SECONDS:
                raise TooLong(info["duration"])
            ydl.process_ie_result(info, download=True)
    except yt_dlp.utils.YoutubeDLError:
        raise AudioUnavailable("download failed") from None
    files = sorted(folder.glob("audio.*"))
    if not files:
        raise AudioUnavailable("no audio")
    title = info.get("title") if isinstance(info.get("title"), str) else "YouTube video"
    return files[0], title


def to_wav(source: Path, wav: Path) -> float:
    """16 kHz mono WAV for whisper, cut at the length limit. Returns its length in seconds."""
    tool = ffmpeg()
    if tool:
        argv = [tool, "-nostdin", "-loglevel", "error", "-y", "-i", str(source), "-vn", "-ac", "1",
                "-ar", "16000", "-t", str(config.MAX_VIDEO_SECONDS), "-c:a", "pcm_s16le", str(wav)]
    else:
        argv = ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(source), str(wav)]
    try:
        subprocess.run(argv, capture_output=True, check=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        raise AudioUnavailable("could not decode") from None
    if not wav.is_file():
        raise AudioUnavailable("no output")
    seconds = max(0, wav.stat().st_size - 44) / WAV_BYTES_PER_SECOND
    if seconds > config.MAX_VIDEO_SECONDS + 1:
        raise TooLong(seconds)
    return seconds
