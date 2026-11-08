# Phase 9 results: integrated prototype

**Goal:** press a key (or say "Jarvis"), speak, and Jarvis does the thing and tells you it did.

## What changed

- **Whisper stays loaded.** `whisper-server` (built from the same pinned whisper.cpp v1.9.1, static arm64) starts with Jarvis on a free port on `127.0.0.1`, holds the model in memory, and takes each command over HTTP with the wake-word hint per request. If it is not up yet or fails, Jarvis falls back to a one-off `whisper-cli` run. Video notes keep using `whisper-cli`, because the server handles one request at a time and a long video would block commands.
- **Delete, with a question first.** `fs.delete` and `fs.delete_all` move items to the macOS Trash (recoverable from Finder), always after a spoken yes; the model can never pre-confirm. "Delete all my notes" is deliberately not "everything".
- **Names as meant.** Reading or deleting finds the closest note when whisper bends a name ("grocery" for groceries, "shoping list"), within the same workspace folder, at 85% similarity or better.
- Every state still ends in a spoken message; the tests in `tests/` cover silence, noise, refusals, crashes in transcription, unanswered confirmations and planner failures.

## Latency (2026-11-08, M1 8 GB)

| Step | Before (Phase 2 style) | Now |
| --- | --- | --- |
| Transcribe a command | ~0.43 s (`whisper-cli` loads the model each time) | ~0.18 s (resident server) |
| End of speech to reply text (router commands) | | 0.15 to 0.23 s |
| `say` start-up and render of a short reply | | ~0.48 s |
| Add for the Gemini fallback | | 0.7 to 1.6 s (Phase 7) |

Key release to spoken reply is well under a second for known commands and about 2 to 3 s through Gemini, against a pass mark of about 5 s. The server's first start after a reboot takes about 13 s while Metal compiles; Jarvis uses `whisper-cli` meanwhile.

## End-to-end run (`scripts/e2e_test.py`)

Spoken commands are made with `say` (Samantha), then go through the real whisper server, router and tools into a temporary workspace. Replies are muted and app launching is stubbed.

| Test | Expected | Result |
| --- | --- | --- |
| Five known commands, spoken | All execute and are confirmed aloud | 5/5 (whisper wrote "grocery" for groceries once; the note was saved and confirmed, and "read me groceries" still found it) |
| Silence after the hotkey | Says it heard nothing | "I didn't hear anything." |
| Background noise | Never executes a wrong tool | "I didn't hear anything.", workspace unchanged |
| Wi-Fi off | Everything except Phases 7 and 8 works | Router commands ran with no planner; Phase 2 already showed whisper works offline. A run with Wi-Fi physically off is still worth doing on your Mac |
| "Open Terminal" | Refused aloud | "That app isn't on my list, so I didn't open it." Nothing launched |
| "Delete everything in my workspace" | Asks first | "Move all N items in your workspace to the Trash?"; "no" left everything in place |
| Twenty commands in a row | No memory growth, no slowdown | 0.19 s average at the start and the end, 0.22 s worst; Python 59 to 62 MB, whisper-server 121 to 125 MB; system memory free 33% (normal) |

Full suite: 658 passed.
