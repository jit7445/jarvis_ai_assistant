# Phase 6 results: app launcher

**Goal:** "open Safari" opens Safari, and "open Terminal" does not.

## How it works

`jarvis.config.ALLOWED_APPS` maps a lowercase spoken name to an app. `jarvis.tools.apps.resolve()` lowercases and collapses whitespace, then looks the name up. Anything not in the table raises `PermissionError`, so the only strings `open -a` can ever receive are the table's values. The call is `subprocess.run(["open", "-a", app], timeout=10)`, with no shell.

`config.BANNED_APPS` is a second gate: Terminal, iTerm, Script Editor, Keychain Access, System Settings and similar tools are refused even if someone adds them to the allowlist. The router strips "the", "up" and a trailing "app", so "open up the Notes app" becomes `Notes`.

Adding an app is a deliberate edit to `config/__init__.py`. No voice command can change either table.

## Default allowlist

| Say | Opens |
| --- | --- |
| safari | Safari |
| notes | Notes |
| music | Music |
| calendar | Calendar |
| chrome, google chrome, google, crome | Google Chrome (added 2026-11-08) |

A trailing "browser" is ignored, so "open my Chrome browser" works. The router also drops "my", "the" and "up".

## Replies

| Situation | Spoken |
| --- | --- |
| Allowlisted | "Opening Safari." |
| Not on the list, or banned | "That app isn't on my list, so I didn't open it." |
| `open` failed or timed out | "I couldn't open that app." |

## Pass criteria

| Check | Result |
| --- | --- |
| Each allowlisted app opens (real run on the Mac, 2026-11-07) | Safari, Notes, Music, Calendar all opened |
| Every unlisted name raises `PermissionError` | 17 names tested, including `safari; rm -rf ~`, `Safari.app`, `-n Safari`, paths, `None` and a list |
| `open -a` never receives an unmapped string | Tested with a recording `subprocess.run`: only mapped values reach it, and banned apps never do, even after being added to the allowlist |

`tests/test_apps.py` mocks `subprocess.run`, so the suite never launches anything. Full suite: 266 passed.
