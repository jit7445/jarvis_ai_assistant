# Phase 7 results: Gemini fallback

**Goal:** when the router returns `None`, ask Gemini to map the sentence onto an existing tool, and treat the answer as a suggestion from a stranger.

## Flow

1. The router (Phase 4) tries first. Every command it knows runs without the network.
2. Only if it returns `None`, and `GEMINI_API_KEY` is set, the sentence goes to `gemini-3.5-flash-lite` (`config.GEMINI_MODEL`).
3. The reply goes through `jarvis.core.proposal.to_intent`: it must be a JSON object with only `tool` and `args`, the tool must be in the registry, the arguments must match its schema exactly (`registry.check`), and every `name` goes through `safe_path`. The model cannot set `confirm`, so an overwrite it proposes still needs a spoken yes. `app.open` still needs the allowlist.
4. Anything that fails a check is refused aloud and nothing runs.

`Planner` in `jarvis/planner/__init__.py` is the interface; `jarvis/planner/gemini.py` is the only file that knows about Google. Swapping providers means one new file.

## What is sent

| Sent | Never sent |
| --- | --- |
| The transcript (after the wake word is removed) | File contents, file names already in the workspace |
| The system prompt: tool names, argument names, the allowlisted app names | The workspace path, home folder, username, environment variables, clipboard, the key in the prompt |

`tests/test_planner.py` checks the request carries only the transcript and that the prompt contains no workspace path, home folder or username. Free-tier requests may be used by Google to improve its products; this rule is what makes that acceptable.

## Failure is a normal state

| Situation | Spoken |
| --- | --- |
| No key set, or `--offline` | "Sorry, I didn't catch that." (as before Phase 7) |
| Model says no tool fits | "Sorry, I didn't catch that." |
| HTTP 429 | "Gemini is busy right now, so I did nothing." |
| HTTP 400, 401, 403 (bad key) | "Gemini refused my request. Check the API key." |
| No network, timeout, server error, non-JSON reply | "I couldn't reach Gemini, so I did nothing." |
| Unknown tool, wrong arguments, escaping path | "Gemini suggested something I can't do, so I did nothing." |

The timeout is 10 s (`config.PLANNER_TIMEOUT_SECONDS`), the API's minimum: a 6 s deadline was rejected with HTTP 400 "Minimum allowed deadline is 10s". Retries are off, so Jarvis answers quickly instead of waiting through backoff. Measured against real endpoints on 2026-11-07: a dummy key at Google's endpoint gave `PlannerSetup` in 0.13 s; an unreachable host gave `PlannerUnavailable` at once.

## Pass criteria

| Check | Result |
| --- | --- |
| An unrecognised sentence produces a valid tool call | Tested with a faked reply end to end ("I need somewhere to keep shopping stuff" creates the folder). Live, 2026-11-08: see below |
| A reply naming a fake tool is refused | `shell.run`, `fs.delete`, extra arguments, a `confirm` field, non-objects: all refused, nothing runs |
| A reply naming `../../.ssh/id_rsa` is refused | Refused by `safe_path`, along with `/etc/passwd`, `~/.zshrc`, `.env` and null bytes |
| With Wi-Fi off, every Phase 4 command still works | Router commands never call the planner; tested with a planner that fails if called |

## Live check (2026-11-08, gemini-3.5-flash-lite, nothing executed)

| Sentence | Proposal | Jarvis |
| --- | --- | --- |
| I need a place to keep my recipes | `fs.make_dir {name: recipes}` | accepted, 1.60 s |
| jot down that the dentist is on Friday | `fs.write_file {name: dentist, body: The dentist is on Friday}` | accepted, 1.64 s |
| what notes do I have | `fs.list_dir {}` | accepted, 1.51 s |
| fire up the browser | `app.open {app_name: safari}` | accepted, 1.62 s |
| start a terminal for me | `{tool: null}` | no tool fits, 1.51 s |
| show me the ssh key in the folder above | `{tool: null}` | no tool fits, 1.02 s |
| what is the weather today | `{tool: null}` | no tool fits, 0.69 s |

Round trips take 0.7 to 1.6 s, on top of transcription.

`google-genai` is pinned to 2.33.0. 3.0.0 came out on 2026-11-06, a major version one day old. Full suite: 321 passed.
