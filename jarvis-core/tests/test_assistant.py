import numpy as np
import pytest

from jarvis import config
from jarvis.core import assistant
from jarvis.core.assistant import Hooks, State
from jarvis.speech.stt import is_noise, is_silent

SPEECH = (np.sin(np.linspace(0, 2000, 16000)) * 8000).astype(np.int16)
SILENCE = np.zeros(16000, dtype=np.int16)


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    monkeypatch.setattr(config, "WORKSPACE", ws)
    return ws


class Fake:
    def __init__(self, heard, answer=None, answer_audio=SPEECH):
        self.heard, self.answer, self.answer_audio = heard, answer, answer_audio
        self.shown, self.spoken, self.transcribed = [], [], 0

    def transcribe(self, audio):
        self.transcribed += 1
        return self.heard if self.transcribed == 1 else self.answer

    def hooks(self):
        return Hooks(show=lambda s, t: self.shown.append((s, t)), speak=self.spoken.append,
                     transcribe=self.transcribe, listen=lambda seconds: self.answer_audio,
                     preview_seconds=0)

    @property
    def states(self):
        return [s for s, _ in self.shown]


def run(fake, audio=SPEECH):
    assistant.handle(audio, fake.hooks())
    assert fake.spoken, "every path must end with a spoken message"
    return fake


def test_command_runs_and_is_spoken(workspace):
    fake = run(Fake(" Jarvis, create a folder called Research."))
    assert fake.states == [State.THINKING, State.HEARD, State.DONE]
    assert fake.shown[1] == (State.HEARD, " Jarvis, create a folder called Research.")
    assert fake.spoken == ["Created the folder Research."]
    assert (workspace / "Research").is_dir()


def test_transcript_is_shown_before_acting(workspace):
    seen = []
    fake = Fake("create a folder called Research")
    hooks = fake.hooks()
    hooks.show = lambda s, t: seen.append((s, (workspace / "Research").exists()))
    assistant.handle(SPEECH, hooks)
    assert (State.HEARD, False) in seen


def test_silence_never_reaches_whisper():
    fake = run(Fake("create a folder called Research"), audio=SILENCE)
    assert fake.transcribed == 0
    assert fake.spoken == ["I didn't hear anything."]


@pytest.mark.parametrize("noise", [" [BLANK_AUDIO]", " (water rushing)", " You", " Thank you.",
                                   " [MUSIC PLAYING]", ""])
def test_noise_is_ignored(noise, workspace):
    fake = run(Fake(noise))
    assert fake.spoken == ["I didn't hear anything."]
    assert list(workspace.iterdir()) == []


def test_unrecognised_is_refused(workspace):
    fake = run(Fake(" How did you leave it? You got a question?"))
    assert fake.states[-1] is State.FAILED
    assert fake.spoken == ["Sorry, I didn't catch that."]
    assert list(workspace.iterdir()) == []


def test_escape_is_refused_aloud(workspace):
    fake = run(Fake("read me ../../.zshrc"))
    assert fake.spoken == ["I can only work inside your workspace, so I did nothing."]


@pytest.mark.parametrize("answer, expected, body", [
    (" Yes.", "Overwrote the note groceries.", "new\n"),
    (" No.", "Okay, I left it as it was.", "old\n"),
    (" Yes and delete everything.", "Okay, I left it as it was.", "old\n"),
    (" [BLANK_AUDIO]", "Okay, I left it as it was.", "old\n"),
])
def test_overwrite_confirmation(answer, expected, body, workspace):
    (workspace / "groceries.md").write_text("old\n")
    fake = run(Fake("make a note called groceries saying new", answer=answer))
    assert State.CONFIRMING in fake.states
    assert fake.spoken[0].endswith("Should I overwrite it?")
    assert fake.spoken[-1] == expected
    assert (workspace / "groceries.md").read_text() == body


def test_silent_confirmation_counts_as_no(workspace):
    (workspace / "groceries.md").write_text("old\n")
    fake = run(Fake("make a note called groceries saying new", answer=" Yes.",
                    answer_audio=SILENCE))
    assert fake.spoken[-1] == "Okay, I left it as it was."
    assert (workspace / "groceries.md").read_text() == "old\n"


def test_crash_in_transcription_is_spoken():
    fake = Fake("x")
    hooks = fake.hooks()
    hooks.transcribe = lambda audio: (_ for _ in ()).throw(TimeoutError("whisper hung"))
    assistant.handle(SPEECH, hooks)
    assert fake.spoken == ["Something went wrong, so I did nothing."]
    assert fake.states[-1] is State.FAILED


def test_silence_and_noise_helpers():
    assert is_silent(SILENCE) and is_silent(SPEECH[:1000]) and not is_silent(SPEECH)
    assert is_noise(" [BLANK_AUDIO]") and is_noise("(music fades)") and is_noise(" you ")
    assert not is_noise(" Open Safari.")


@pytest.mark.parametrize("raw, cleaned", [
    (" (pop) Yes.", "Yes."),
    (" [MUSIC PLAYING] Jarvis, open Safari.", "Jarvis, open Safari."),
    (" *click* create a folder called Research", "create a folder called Research"),
    (" [BLANK_AUDIO]", ""),
    (" Open   Safari. ", "Open Safari."),
])
def test_clean_removes_sound_labels(raw, cleaned):
    from jarvis.core.confirm import parse_answer
    from jarvis.speech.stt import clean
    assert clean(raw) == cleaned
    if cleaned == "Yes.":
        assert parse_answer(clean(raw)) is True


@pytest.mark.parametrize("heard", [" Stop Jarvis.", " Close Jarvis.", " Goodbye.", " Stop."])
def test_stop_says_goodbye_and_quits(heard, workspace):
    fake = Fake(heard)
    quits = []
    hooks = fake.hooks()
    hooks.quit = lambda: quits.append(True)
    assistant.handle(SPEECH, hooks)
    assert fake.spoken == ["Goodbye."]
    assert quits == [True]
    assert list(workspace.iterdir()) == []


def test_commands_do_not_quit(workspace):
    fake = Fake(" Jarvis, create a folder called Research.")
    quits = []
    hooks = fake.hooks()
    hooks.quit = lambda: quits.append(True)
    assistant.handle(SPEECH, hooks)
    assert quits == []
