# Phase 5 results: workspace file tools

Date: 2026-11-07. Verdict: **pass**.

Workspace: `jarvis-core/workspace/` (kept in the project, gitignored).

## Implementation

| Module | Role |
| --- | --- |
| `jarvis.tools.paths.safe_path` | The only gate from a name to a path. Every file tool calls it. |
| `jarvis.tools.fs` | `make_dir`, `write_file`, `read_file`, `list_dir`. Each returns a `Result` whose `message` is what Jarvis says. |
| `jarvis.tools.executor.execute` | Validates an `Intent` against the registry, dispatches it, and turns any refusal or OS error into a spoken message. Never raises for bad input. |
| `jarvis.core.confirm.parse_answer` | Strict yes/no parsing of the spoken reply to a confirmation question. |

## safe_path, beyond the plan's version

| Rule | Why |
| --- | --- |
| Refuse names starting with `~` | pathlib does not expand `~`. With the plan's version, `~/Documents/taxes.pdf` resolves to a folder literally named `~` inside the workspace, so the plan's own escape test would not raise. |
| Refuse any path component starting with `.` | One rule covers `..`, `.env`, `.ssh`, `.git`, even inside the workspace. Spoken names never need them. |
| Refuse the workspace root itself, empty names and control characters | No tool needs to act on the root by name; NUL bytes otherwise raise `ValueError` deep in pathlib. |
| Compare resolved paths | As in the plan: collapses `..` and follows symlinks before the check. |
| Missing workspace raises `FileNotFoundError` | Fails closed instead of creating a folder somewhere unexpected. |

The file tools also open with `O_NOFOLLOW`, so a symlink planted between the check and the open makes the call fail rather than follow it.

## Behaviour

| Command | Result |
| --- | --- |
| create a folder that exists | Says it already exists; contents untouched |
| make a note called X | Writes `X.md`; "saying Y" becomes the body |
| make a note over an existing one | Asks "Should I overwrite it?"; nothing changes until a yes |
| read me X | Reads `X`, or `X.md`; only `.md` and `.txt`; cut at 2,000 characters |
| what's in my workspace | Folders, notes and other files, hidden files skipped, ten names per group |

Confirmation accepts only exact short answers: yes, yeah, yes please, go ahead, overwrite it, and so on. Anything else, including "okay", "thank you", `[BLANK_AUDIO]` and "yes and delete everything", counts as no.

## Router fix found here

The router stripped leading dots while tidying punctuation, so "read me ../../.zshrc" reached the tools as `/../.zshrc` and "read me .env" would have become `env`. Both were still contained, but cleanup must never change what was asked. It now strips trailing punctuation only, and the hostile name reaches `safe_path` intact.

## Results

| Check | Result |
| --- | --- |
| Every escape test raises | 42 cases, including symlinks out of the workspace: pass |
| Create and read work for ordinary names | pass, in tests and in the real workspace |
| Overwrite prompts first | pass; file unchanged after "no" |
| Nothing outside the workspace is opened | escape tests snapshot the surrounding directory before and after: unchanged |
| pytest | 147 passed |

Live run in the real workspace through `scripts/route_test.py --run`: created `Research`, saved `groceries`, refused to overwrite it after "no", read it back, refused `../../.zshrc` and `.env`, and listed the workspace.
