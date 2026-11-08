import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from jarvis import config, gateway_client
from jarvis.core.result import Result
from jarvis.research import note, summarise
from jarvis.speech import stt
from jarvis.video import audio, source

MAX_SUMMARY_CHARS = 6000

# Replaced in tests.
find = source.find
current = source.current
download = audio.download_youtube
to_wav = audio.to_wav
transcribe = stt.transcribe_file



def _summarise(title: str, transcript: str) -> str:
    """Gemini, through the gateway, which fences the transcript as untrusted text."""
    data = gateway_client.post("/summarise", config.SUMMARY_TIMEOUT_SECONDS,
                               json={"kind": "video", "title": title, "transcript": transcript}).json()
    summary = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(summary, str):
        raise gateway_client.GatewayError("bad")
    return summary


summary_of = _summarise
today = date.today


# A live recording starts while Jarvis is still saying it is listening, and that comes out of
# the same speakers being recorded.
_OWN_VOICE = re.compile(r"^.{0,80}?taking notes.{0,80}?stop notes.{0,40}?done\.?\s*",
                        re.IGNORECASE | re.DOTALL)


def _drop_own_voice(text: str) -> str:
    return _OWN_VOICE.sub("", text, count=1)


def _one_line(text: str) -> str:
    return " ".join(re.sub(r"[#\[\]`]", "", text).split())[:150] or "Video"


def render(video: source.Video, title: str, seconds: float, summary: str, transcript: str,
           made: date, note_text: str = "") -> str:
    minutes = max(1, round(seconds / 60))
    heard = "Recorded" if video.kind == "live" else "Length"
    lines = [f"# {title}", "", f"Source: {video.ref}",
             f"{heard}: about {minutes} min. Transcribed {made.isoformat()} on this Mac (whisper base.en).",
             "", "## Summary", "", summary or note_text, "", "## Transcript", "", transcript, ""]
    return "\n".join(lines)


def notes_current() -> Result:
    """A YouTube tab or QuickTime file is read whole; anything else is heard live."""
    from jarvis.video import live
    try:
        video = current()
    except source.VideoNotFound:
        return live.start()
    return _make(video)


def notes_file(query: str) -> Result:
    try:
        video = find(query)
    except source.VideoNotFound:
        return Result(False, f"I couldn't find a video called {' '.join(str(query).split())[:60]}.")
    return _make(video)


def _make(video: source.Video) -> Result:
    with tempfile.TemporaryDirectory(prefix="jarvis-video-") as tmp:
        folder = Path(tmp)
        try:
            if video.kind == "youtube":
                media, title = download(video.ref, folder)
            else:
                media, title = Path(video.ref), video.title
            seconds = to_wav(media, folder / "audio.wav")
            if seconds < 1:
                return Result(False, "That video has no sound I can use.")
            return notes_from_wav(video, title, folder / "audio.wav", seconds)
        except audio.TooLong:
            return Result(False, f"That video is longer than {config.MAX_VIDEO_SECONDS // 60} "
                                 "minutes, so I left it.")
        except audio.AudioUnavailable:
            return Result(False, "I couldn't get the sound from that video.")


def notes_from_wav(video: source.Video, title: str, wav: Path, seconds: float) -> Result:
    try:
        text = transcribe(wav, timeout=seconds * 0.6 + 120)
    except subprocess.TimeoutExpired:
        return Result(False, "Transcribing took too long, so I stopped.")
    except (OSError, subprocess.SubprocessError):
        return Result(False, "I couldn't transcribe that video.")
    transcript = _drop_own_voice(text)[:config.MAX_TRANSCRIPT_CHARS]
    if stt.is_noise(transcript):
        return Result(False, "I couldn't hear any speech in that video.")
    title = _one_line(title)

    summary, fallback, spoken = "", "", f"Saved notes on {title} in your videos folder."
    try:
        summary = summarise.clean(summary_of(title, transcript), MAX_SUMMARY_CHARS)
    except (gateway_client.GatewayError, ValueError) as error:
        if getattr(error, "kind", "") == "setup":
            fallback = "No summary: the gateway or its Gemini key is not set up. The transcript is below."
            spoken = f"Saved the transcript of {title}. Start the gateway with a Gemini key for a summary."
        else:
            fallback = "No summary: Gemini could not be reached. The transcript is below."
            spoken = f"Saved the transcript of {title}, but I couldn't reach Gemini for a summary."
    made = today()
    note.save(config.VIDEO_DIR, f"{made.isoformat()}-{note.slug(title)}",
              render(video, title, seconds, summary, transcript, made, fallback))
    return Result(True, spoken)
