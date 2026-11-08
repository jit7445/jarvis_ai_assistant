# Phase 10 results: two services

**Goal:** the single Python app becomes two local processes: `jarvis-core`, which owns the Mac, and `jarvis-gateway`, which owns the network and the browser UI.

## The split

| | jarvis-core (Python, FastAPI) | jarvis-gateway (Node, Express) |
| --- | --- | --- |
| Owns | Microphone, wake word, whisper, router, policy gate, tools, `say`, overlay | Gemini (planner, chat, summaries), Wikipedia, YouTube download, browser UI, recent history |
| Internet | None. `gateway_client.py` is its only network code and refuses any host but 127.0.0.1; a test fails the build if core imports a Gemini, yt-dlp or requests module | Yes, and nothing else on the Mac: downloads land only in `jarvis-gateway/tmp/` |
| Gemini key | Removed from its environment by `scripts/dev.sh` | `GEMINI_API_KEY` from the shell |
| Binds | `127.0.0.1:8765` | `127.0.0.1:4300` (Vite's reload channel shares the same server) |

The policy gate did not move. Gemini's reply travels gateway to core raw and is checked in core by `to_intent` and the registry, exactly as in Phase 7. The planner prompt is served by core (`GET /tools`), so the tool list has one source of truth.

## Endpoints

| Service | Endpoint | Does | Who may call |
| --- | --- | --- | --- |
| core | `GET /health` | whisper loaded or on demand | token |
| core | `GET /tools` | registry, descriptions, app names, planner prompt | token |
| core | `POST /transcribe` | 16 kHz 16-bit WAV in, text out (20 MB cap) | token |
| core | `POST /execute` | a tool call in, a result out, after the gate; can never confirm | token |
| core | `POST /command` | typed text through the same queue and pipeline as speech | token |
| gateway | `POST /plan`, `/research`, `/summarise`, `/youtube-audio`, `/events` | the internet, for core | token |
| gateway | `GET /status`, `GET /history`, `WS /live` | the dashboard | this page (Host check; WS also Origin) |
| gateway | `POST /command` | a typed command from the dashboard | this page's own Origin only |

Every core request needs `X-Jarvis-Token` (constant-time compare) and a `Host` of `127.0.0.1:8765` or `localhost:8765`, which stops DNS-rebinding pages. The gateway checks `Host` on everything. `scripts/dev.sh` makes a new 256-bit token each run and never writes it to disk. Core's docs pages are off. History is kept in memory only (last 100 states), following the rule to log what happened rather than store what was said.

## Running

```bash
scripts/dev.sh --verbose      # gateway in the background, Jarvis in front; Ctrl+C stops both
```

Then open http://127.0.0.1:4300 for the dashboard. Without `dev.sh` (no token), Jarvis still runs with voice and offline commands; Gemini, research and YouTube downloads need the gateway.

## Pass criteria (2026-11-08, live, both services up)

| Check | Result |
| --- | --- |
| Both services start, `GET /health` answers | core `{"ok":true,"whisper":"loaded"}`; gateway `/status` shows core online and Gemini on |
| A command posted to the gateway comes back spoken | "create a folder called Research" gave "Created the folder Research." in 0.03 s |
| Gemini through the split, core holding no key | "I need somewhere to keep my recipes" created the folder (1.2 s); "how are you" got a chat reply (1.1 s); "look up black holes" saved a sourced note (24.8 s, Gemini slow that run) |
| Refusals still spoken | "open Terminal": "That app isn't on my list, so I didn't open it." |
| `curl` to core without the token is rejected | 401 for no token, a wrong token, and `POST /execute` of `fs.delete_all` |
| A command from another website is rejected | `POST /command` with a foreign Origin: 403 |
| Neither port answers from another machine | `lsof`: Python on 127.0.0.1:8765, node on 127.0.0.1:4300; the LAN address 192.168.1.34 got no connection on either port |
| Memory pressure green | node about 27 + 67 MB, core Python about 34 MB, whisper-server small (its model sits in Metal memory); system memory free 33%. Re-check with the dashboard open in a browser tab |

Tests: core 685 (`pytest`), gateway 42 (`npm test`).
