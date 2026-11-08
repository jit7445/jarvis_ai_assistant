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


_SUFFIX = {"audio/mp4": ".m4a", "audio/webm": ".webm", "audio/mpeg": ".mp3", "audio/ogg": ".ogg"}


def download_youtube(url: str, folder: Path) -> tuple[Path, str]:
    """The audio track of a canonical YouTube URL, fetched by the gateway, and the title."""
    from urllib.parse import unquote

    from jarvis import gateway_client
    try:
        response = gateway_client.post("/youtube-audio", config.DOWNLOAD_TIMEOUT_SECONDS,
                                       json={"url": url})
    except gateway_client.GatewayError as error:
        if error.kind == "toolong":
            raise TooLong(config.MAX_VIDEO_SECONDS + 1) from None
        raise AudioUnavailable(error.kind) from None
    kind = response.headers.get("content-type", "").split(";")[0].strip()
    if kind not in _SUFFIX or not response.content or len(response.content) > config.MAX_UPLOAD_BYTES:
        raise AudioUnavailable("unexpected reply")
    path = folder / f"audio{_SUFFIX[kind]}"
    path.write_bytes(response.content)
    title = unquote(response.headers.get("x-title", ""))[:200] or "YouTube video"
    return path, title


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
