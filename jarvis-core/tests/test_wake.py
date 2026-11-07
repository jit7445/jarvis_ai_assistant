import numpy as np
import pytest

from jarvis.audio.listener import BLOCK, Segmenter
from jarvis.core.router import route
from jarvis.core.wake import is_stop, split_wake

rng = np.random.default_rng(0)


def blocks(seconds: float, level: float) -> list[np.ndarray]:
    n = round(seconds * 10)
    return [(rng.normal(0, level, BLOCK)).astype(np.int16) for _ in range(n)]


def feed_all(segmenter: Segmenter, stream: list[np.ndarray]) -> list[np.ndarray]:
    return [u for b in stream if (u := segmenter.feed(b)) is not None]


@pytest.mark.parametrize("text, command", [
    (" Jarvis.", ""),
    (" Hi, Jarvis.", ""),
    (" Hello Jarvis!", ""),
    (" Hey, Jarvis?", ""),
    (" Jarvis, create a folder called Research.", "create a folder called Research."),
    (" Hello, Jarvis. What's in my workspace?", "What's in my workspace?"),
    (" Hi Jarvis, open Safari.", "open Safari."),
    (" Jarv is, open Safari.", "open Safari."),
    (" Jervis, read me groceries.", "read me groceries."),
    ("JARVIS make a note called ideas", "make a note called ideas"),
])
def test_wake_phrases(text, command):
    assert split_wake(text) == command


@pytest.mark.parametrize("text", [
    " I was telling Jarvis about it.",
    " So, hi Jarvis is a nice name.",
    " Create a folder called Research.",
    " Jarvisson called yesterday.",
    " Hello there.",
    " Hi.",
    " [BLANK_AUDIO]",
    "",
    None,
])
def test_no_wake(text):
    assert split_wake(text) is None


def test_wake_then_router():
    assert route(split_wake(" Hello Jarvis, create a folder called Projects.")).args == {
        "name": "Projects"}


def test_segmenter_cuts_one_utterance_with_pre_roll():
    seg = Segmenter()
    stream = blocks(2, 15) + blocks(1.5, 3000) + blocks(1, 15)
    out = feed_all(seg, stream)
    assert len(out) == 1
    seconds = out[0].size / (BLOCK * 10)
    assert 1.5 <= seconds <= 2.6


def test_segmenter_splits_two_utterances():
    seg = Segmenter()
    stream = blocks(1, 15) + blocks(1, 3000) + blocks(1.2, 15) + blocks(1, 3000) + blocks(1, 15)
    assert len(feed_all(seg, stream)) == 2


def test_short_pause_inside_a_sentence_is_kept_together():
    seg = Segmenter()
    stream = blocks(1, 15) + blocks(0.8, 3000) + blocks(0.4, 15) + blocks(0.8, 3000) + blocks(1, 15)
    assert len(feed_all(seg, stream)) == 1


@pytest.mark.parametrize("stream", [
    blocks(5, 15),                                  # silence
    blocks(5, 200),                                 # steady quiet hum
    blocks(1, 15) + blocks(0.2, 3000) + blocks(1, 15),  # click or knock
    blocks(1, 15) + blocks(0.1, 3000) + blocks(0.1, 15) + blocks(0.1, 3000) + blocks(1, 15),
])
def test_segmenter_ignores_noise(stream):
    assert feed_all(Segmenter(), stream) == []


def test_segmenter_adapts_to_loud_room():
    seg = Segmenter()
    feed_all(seg, blocks(4, 600))
    assert seg.threshold > 1500
    assert feed_all(seg, blocks(2, 600)) == []
    assert len(feed_all(seg, blocks(1, 9000) + blocks(1, 600))) == 1


def test_steady_noise_that_starts_later_is_learned_not_transcribed():
    seg = Segmenter()
    assert feed_all(seg, blocks(1.5, 15) + blocks(30, 1500)) == []
    assert seg.threshold > 4000
    assert len(feed_all(seg, blocks(1, 12000) + blocks(1, 1500))) == 1



@pytest.mark.parametrize("text", [
    " Close Jarvis.", " Stop Jarvis.", " Stop, Jarvis!", " Quit Jarvis.", " Goodbye, Jarvis.",
    " Jarvis, stop.", " Jarvis, close.", " Hey Jarvis, shut down.", " Jervis, go to sleep.",
    " Close the Jarvis.", " Jarvis, please stop.", " Stop Jarvis please.", " Bye bye Jarvis.",
])
def test_named_stop_always_works(text):
    assert is_stop(text) and is_stop(text, addressed=True)


@pytest.mark.parametrize("text", [" Stop.", " Close.", " Goodbye!", " Quit.", " Please stop."])
def test_bare_stop_only_when_addressed(text):
    assert not is_stop(text)
    assert is_stop(text, addressed=True)


@pytest.mark.parametrize("text", [
    " We should stop Jarvis from opening Safari.",
    " Close the door, Jarvis is listening.",
    " Stop the music.",
    " Jarvis, open Safari.",
    " Jarvis, create a folder called stop.",
    " Bus stop Jarvis road.",
    " [BLANK_AUDIO]", "", None,
])
def test_not_a_stop(text):
    assert not is_stop(text, addressed=True)
