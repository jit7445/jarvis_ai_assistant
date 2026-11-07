# Phase 3 results: speech output

Date: 2026-11-07. Verdict: **pass**.

## Implementation

`jarvis.speech.tts.speak(text, voice=None)` wraps macOS `say`. Default voice is `jarvis.config.VOICE` (Samantha); Rishi (en_IN) is installed as an alternative.

The text is passed on stdin, not as an argument. The plan's list-form `subprocess.run` stops shell injection, but `say` still parses a leading `-` in argv as its own option: during testing, `say -v Samantha -o <path>` with text `-o <path>` wrote an audio file instead of speaking. On stdin the same text is spoken.

Voices are checked against the installed list (`say -v '?'`, 143 voices on this Mac) before use, so names such as `-o` or `Samantha; ls` are refused.

## Results

| Check | Target | Result |
| --- | --- | --- |
| Audible | speech plays | played through MacBook Air speakers |
| Start latency | within ~2 s | "Ready." finished in 1.50 s including the first voice lookup |
| Network | not needed | voices are installed on-device |
| `"; ls` in text | read aloud, not run | read aloud |
| `-o /tmp/should_not_exist.aiff` as text | read aloud, no file written | read aloud, no file created |

`tests/test_tts.py`: 10 tests pass, covering hostile text, empty text, refused voices and parsing of the real voice list.
