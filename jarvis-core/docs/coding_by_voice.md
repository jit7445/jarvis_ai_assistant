# Coding by voice with Claude Code

Added at your request; not in the plan. Jarvis opens a project in VS Code and hands instructions to the Claude Code extension there.

## What you say

| You say | Jarvis does |
| --- | --- |
| "Jarvis, open jarvis ai assistant in VS Code" | Finds the git repository by name anywhere in your home folder and opens it (`code <folder>`, which focuses the window if it is already open) |
| "Jarvis, tell Claude to add a login page" (also "ask Claude Code to...", "send to Claude: ...") | Fills the prompt into a new Claude Code tab in that project's window, reads it back ("Send to Claude: add a login page?") and presses Enter only after your "yes" |
| "Jarvis, review the code" | Same flow with a fixed review prompt (bugs, risky code, missing tests, no file changes); reads back "Ask Claude to review the changes in X?" |
| "Jarvis, accept the changes" / "reject the changes" | Runs Claude Code's "Accept/Reject Proposed Changes" command in that window |

## Hearing Claude's answer

After a prompt is sent, Jarvis waits in the background (up to 15 minutes) for Claude to finish and then says "Claude says: ..." while you keep using it. "What did Claude say?" repeats the last answer.

Claude Code writes every conversation to `~/.claude/projects/<project path with non-alphanumerics as ->/<session>.jsonl`, including ones started from the VS Code extension. Jarvis reads only that project's newest logs, finds the user line holding the exact prompt it sent (after the send time), and waits for the assistant line marked `end_turn`; the answer is every text block with that line's request ID. Subagent lines are skipped. Code blocks are replaced with "(code shown in VS Code)", markdown is stripped, and speech stops after about 700 characters with "The rest is in VS Code." The answer is spoken locally and never sent anywhere.

Checked against a real log on this Mac: the prompt "commit it" from this build's own conversation returned the actual answer.

Questions about code ("explain this code", "walk me through the codebase", "what does the code in auth do") now go to Claude Code instead of Gemini chat, which cannot see your code. A newer prompt replaces an older wait.

## How the prompt reaches Claude Code

The extension (v2.1.319) registers `vscode://anthropic.claude-code/open?prompt=...`. Opening it starts a Claude Code tab with the prompt **filled in, not sent**. VS Code first asks "Allow 'Claude Code for VS Code' extension to open this URI?"; ticking "Do not ask me again" makes later prompts hands-free.

VS Code hands the link to whichever window is in front. A live test caught a prompt meant for one project landing in another window, so Jarvis now waits (up to 6 s) until the front window's title ends in the project's folder name, and gives Claude nothing if it never does. The match is exact on the folder name, so "jarvis" never matches a `jarvis_ai_assistant` window.

The "yes" step presses Enter through System Events. The script receives the folder name as an argument (never pasted into the script), raises that project's window, checks again that it is frontmost, and only then presses the key. It needs Accessibility permission for the app Jarvis runs in, the same permission as the right-Option hotkey.

## Safety

Claude Code can edit files and run commands, so a spoken prompt is close to a spoken shell command. That is why Terminal is banned from the app list. The guards here:

- The wake word is required, and every prompt is read back word for word. Only an exact yes ("yes", "yeah", "go ahead"...) sends it; "yes and also..." does not.
- The confirmed prompt must equal the one filled in; anything else sends nothing.
- The Gemini fallback can propose a coding command but cannot pre-confirm it.
- Keys are pressed only after the right window is verified in front.
- Claude Code's own Auto mode still checks each action for risk and blocks the risky ones; its on-screen prompts for terminal commands are untouched.
- Voice approval covers proposed file changes only, as you chose.

## Flexible phrasing

- whisper's spellings are accepted: "BS code", "V.S. code", "vscode" for VS Code; "cloud", "Claud" for Claude. The whisper hint now includes both names (silence and noise still transcribe to nothing).
- A false start like "open, Jarvis, open, demo repo" is collapsed.
- "Find repo called X and open it", "open the project called X", and plain "open X" when X is a project rather than an app all open the project.
- "Tell / ask / have / get / let Claude ..." all send a prompt.
- Project names tolerate mishearing ("jervis", "code mining back end").
- Anything else goes to Gemini, whose reply may now carry extra fields without being refused.

## Finding projects

`jarvis.coding.repos.scan` walks the home folder up to 5 levels, takes any folder holding `.git`, and skips hidden folders, `~/Library`, `node_modules`, virtualenvs, build output and media folders. On this Mac: 35 repositories in 0.14 s, cached for 10 minutes. Names are matched by words ("jarvis ai assistant" finds `jarvis_ai_assistant`, "tutor ai frontend" finds `tutorAiFrontend`); an exact match beats a partial one, and the most recently changed folder wins a tie.

Note: "jarvis" alone matches the old `jervis/jarvis` folder exactly. Delete that leftover or say "jarvis ai assistant".

## Live checks (2026-11-08)

| Check | Result |
| --- | --- |
| Link fills, does not send | Confirmed: prompt sat in the input box |
| Prompt lands in the right project | After the fix: filled into `jarvis-demo-repo`'s window in 1.5 s, with the window verified in front |
| Repository search | 35 repos in 0.14 s; names matched as above |
| Enter on "yes" and voice approval | Needs Jarvis running from your terminal (Accessibility); check pending on your Mac |

Tests: `tests/test_coding.py`. Full suite: 560 passed.
