# Phase 4 results: command router

Date: 2026-11-07. Verdict: **pass**.

## Implementation

| Module | Role |
| --- | --- |
| `jarvis.core.intent` | `Intent(tool, args, confirm)`, the one shape every command must fit |
| `jarvis.tools.registry` | `TOOLS`, the fixed tool list with exact argument names and types; `check()` raises `InvalidIntent` on anything else |
| `jarvis.core.router` | `route(transcript) -> Intent | None`, plain regex matching, no model |

Every intent the router produces passes through `check()`. Phase 7 will send Gemini's proposals through the same function.

## Phrases

| Spoken | Tool | Arguments | Accepted variants |
| --- | --- | --- | --- |
| "create a folder called X" | `fs.make_dir` | `name` | make; new; named; "in my workspace" before or after the name |
| "make a note called X" | `fs.write_file` | `name`, `body` | create, write, take; named, titled; optional "saying Y" fills `body`, else `""` |
| "read me X" | `fs.read_file` | `name` | "read", "read me the note called X" |
| "what's in my workspace" | `fs.list_dir` | none | what is; list/show (me) my workspace |
| "open X" | `app.open` | `app_name` | open up; "the X app" |

## Normalisation

Collapses whitespace, converts curly apostrophes, strips surrounding punctuation, and removes a leading "Jarvis," / "hey Jarvis" / "please" / "can you" and a trailing "please" / "thanks". Matching ignores case; captured names keep the case Whisper gave them, so "Research" stays "Research".

## Decisions

- `None` for anything not matching a pattern exactly: misspellings ("creat a foldr"), missing names ("create a folder"), filler names ("open the app", "open it"), and unsupported requests ("delete everything", "what's the weather").
- The router does not judge whether a name is safe. "open terminal" routes to `app.open`; the Phase 6 allowlist refuses it. Path names are checked by `safe_path` in Phase 5.
- `confirm` is always `False` here. Whether an action overwrites something is only known when it runs, so Phase 5 sets it.

## Results

| Check | Result |
| --- | --- |
| Five plan phrases route correctly | pass |
| Real Whisper output routes (`workspace/mic_test.wav`) | "Create a folder in my workspace called Research Jarvis agent." to `fs.make_dir` with name "Research Jarvis agent" |
| Unrecognised speech returns `None` without raising | pass, including empty, `[BLANK_AUDIO]`, non-string and 100,000-character input |
| pytest | 61 passed: router 36, registry 15, speech 10 |

`scripts/route_test.py` routes typed text, a WAV file, or a live 5-second recording.

## Live voice test and the Whisper prompt

The first live test of "Jarvis, create a folder called Research." transcribed as "Jarv is created a folder called research." and routed to `None`, correctly: "is created a folder" is not a command. The fix belongs in transcription, not in a looser router.

whisper.cpp's `--prompt` biases the decoder towards expected vocabulary. Results on the same recording:

| Prompt | Transcript |
| --- | --- |
| none | Jarv is created a folder called research. |
| "Jarvis" | Jarvis created a folder called research. |
| the five command forms (`config.WHISPER_PROMPT`) | Jarvis, create a folder called Research. |

The prompt uses names the user is unlikely to say (Projects, groceries) so it does not bias real folder names; "Research" still transcribed correctly.

Prompts can make Whisper repeat the prompt on silence, which here would mean executing a command nobody said. Tested on 5 s of silence, low hiss, loud white noise and 50 Hz hum: outputs were `[BLANK_AUDIO]`, "(water rushing)" and "(music fades)". None reproduced a command, and the router returns `None` for all of them. Phase 9 should repeat this check on real room noise.

## Wider phrasing (2026-11-08)

The router now accepts many natural forms, all offline. Fillers such as "please", "can you", "I want you to", "let's", "for me" and "now" are dropped first.

| Tool | Examples that work |
| --- | --- |
| Folder | create a Projects folder; make me a new folder for invoices; add a folder named Travel 2026 to my workspace; I need a folder called Taxes; new folder Recipes; set up a directory called Backups |
| Note | make a note called groceries saying milk; take a note called meeting: call Ravi at 5; write a todo note saying finish phase 8; new note ideas; jot down a note called dentist that says Friday at 10 |
| Read | read groceries; read me my groceries note; what's in the note called groceries; what does groceries say; show me the note called dentist; open my note ideas |
| List | what do I have; list my files; show me my notes; what files do I have; list everything |
| App | open, launch, start, run, fire up, bring up, switch to (Safari, Chrome, ...) |

An app the allowlist does not know ("open my browser", "run the tests") is no longer refused by the router; it goes to the Gemini fallback, which can map "my browser" to an allowlisted app. Banned apps (Terminal, iTerm, ...) are still refused by name. Sentences with no name ("create a folder", "make a note saying buy milk") also go to the fallback rather than guessing.
