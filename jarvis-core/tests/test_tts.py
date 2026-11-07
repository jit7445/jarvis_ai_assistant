import subprocess

import pytest

from jarvis.speech import tts


@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def fake_run(args, **kwargs):
        recorded.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(tts, "installed_voices", lambda: frozenset({"Samantha", "Rishi"}))
    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    return recorded


@pytest.mark.parametrize("text", [
    'Done. "; ls',
    "-o /tmp/pwned.aiff",
    "$(rm -rf ~) `whoami` && echo hi | cat",
    "--help",
])
def test_hostile_text_is_spoken_not_parsed(calls, text):
    tts.speak(text)
    (args, kwargs), = calls
    assert args == ["say", "-v", "Samantha"]
    assert kwargs["input"] == text
    assert "shell" not in kwargs


def test_text_never_appears_in_argv(calls):
    tts.speak("create a folder called Research")
    (args, _), = calls
    assert not any("Research" in a for a in args)


def test_empty_text_says_nothing(calls):
    tts.speak("   ")
    assert calls == []


@pytest.mark.parametrize("voice", ["NoSuchVoice", "-o", "Samantha; ls"])
def test_unknown_voice_is_refused(calls, voice):
    with pytest.raises(ValueError):
        tts.speak("hello", voice=voice)
    assert calls == []


def test_voice_listing_parses_real_say_output():
    voices = tts.installed_voices()
    assert "Samantha" in voices
    assert "Eddy (English (UK))" in voices
