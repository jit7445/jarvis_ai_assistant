# Jarvis

A local voice assistant for macOS on Apple Silicon. Push a key, speak, and Jarvis acts on your workspace or opens an allowlisted app.

## Layout

| Folder | Runtime | Owns |
| --- | --- | --- |
| [jarvis-core](jarvis-core/) | Python | The machine: microphone, whisper.cpp transcription, speech output, workspace file tools, app allowlist, policy gate |
| [jarvis-gateway](jarvis-gateway/) | Node.js | The network and the UI: browser interface, conversation history, Gemini client |

Core makes no outbound network requests. Gemini proposes actions as JSON; core validates every proposal against a fixed tool registry before anything runs.

Both services bind to `127.0.0.1` only.

## Status

Built phase by phase from the Jarvis V1 plan.

| Phase | Deliverable | State |
| --- | --- | --- |
| 0 | Environment | done |
| 1 | Microphone capture | done |
| 2 | Local transcription | done |
| 3 | Speech output | done |
| 4-12 | Command router through wake word | not started |

The gateway currently holds an earlier web prototype. It is reworked into the plan's gateway in Phase 10.
