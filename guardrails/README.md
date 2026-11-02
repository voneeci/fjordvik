# Guardrails: the checks behind GUARDRAILS.md

[GUARDRAILS.md](../GUARDRAILS.md) holds the master rules for the Fjordvik project. This
folder holds what enforces them. Attena, the guardrails code chat, maintains both; other
chats suggest changes in `proposals/`.

| File | What it does |
| --- | --- |
| `check.py` | Checks the repository: the fingerprints of eleven guardrail files (`GUARDRAILS.sha256`, including each part's `tests/test_guardrails.py`), document, evidence and scratch names (L3 to L5), em dashes, common American spellings, "projects" counts, secrets and connection strings, `.env` files, files over 50 MB, the old local repositories, the layout map (every file on it), and an optional private list of banned names kept outside the repository. `python guardrails/check.py` prints any findings. |
| `claude_hook.py` | The Claude Code hook in `../.claude/settings.json`. Before a tool call runs, it blocks hand edits and shell writes to generated data, any `.env` file (a quoted search pattern on piped file names may name one), the private banned-names list, `git add .`, `-A`, `-u`, `git commit -a`, hook bypasses, writes to `.git/hooks/` and force pushes. It checks commands from Bash, PowerShell, Monitor and the terminal tool (`mcp__terminal__run_in_terminal`) from the folder they run in, following `cd`, and reads wrapped commands such as `bash -c` and `powershell -Command`. It checks the files Artifact and SendUserFile would send, reads file paths in one canonical form, and finds the repository root with git. It asks Reece before any change to the guardrail files (rule G9), including a git rollback or a move of `.claude`, and it blocks any call it cannot read. It covers the common forms of each breach; GUARDRAILS.md lists what it doesn't catch. |
| `shared_tests.py` | Tests every part runs through its own `tests/test_guardrails.py`: the checker finds nothing, the fingerprints match, the checker catches planted breaches, and the hook blocks, asks or allows as it should. |
| `layout.md` | The layout map: where each kind of file lives in the repository, and why (rules L1 to L6). A file it doesn't list fails the tests. To add a folder, suggest the entry in `proposals/`. |
| `evidence/` | Raw output and reports of guardrails-only tests, such as the read-only tests of 2 November 2026. |
| `.gitattributes` | Keeps the PDF reports in `evidence/` binary, so git doesn't change their bytes. |
| `pre-commit` | Runs `check.py` before each commit. Reece installed it on 2 November 2026. |
| `proposals/` | Suggested changes to the rules, one file each, named `YYYY-MM-DD-<chat>-<topic>.md`, for Attena to review. |
| `CLAUDE.md` | Attena's working rules for this folder. |

## The two layers in `.claude/settings.json`

- **The hook** (above) runs before each matching tool call and reads the call itself.
- **Permission rules** are applied by Claude Code in every mode, whatever form a path
  takes. Deny rules stop reading `.env` files and the private list's folder, and editing
  the generated data folders and `.git/hooks/`. Ask rules prompt Reece before editing the
  guardrail files. They cover the file tools and shell redirects, not every shell command,
  which is why the hook stays.

A hook that times out blocks the call (`"onFailure": "block"`), so a slow check can't let a
call through.

## Installing the pre-commit check (Reece, by hand)

Only Reece changes git hook settings (RULES.md and GUARDRAILS.md rule G2). The check is
installed for this clone. To install it in another clone, from that clone's root in
PowerShell run `Copy-Item guardrails\pre-commit .git\hooks\pre-commit`. To remove it, delete
that copy.

## The private banned-names list (Reece, by hand)

`check.py` also reads `%LOCALAPPDATA%\fjordvik-guardrails\banned-terms.txt` if it exists:
one name per line (lines starting with `#` are ignored). It is kept outside the public
repository so the list itself names no one. Without it, that check is skipped and
`check.py` prints a notice. The hook and a permission rule stop every chat reading or
writing the list, so only Reece creates and edits it:

1. In PowerShell, run `New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\fjordvik-guardrails"`.
2. Run `notepad "$env:LOCALAPPDATA\fjordvik-guardrails\banned-terms.txt"`, choose Yes to create it, type one name per line, and save.
3. From the repository root, run `python guardrails\check.py`. The notice is gone, and any line starting `D2` names a file that holds a banned name (never the name itself).

## Where a chat starts (rule G11)

Claude Code loads `.claude/settings.json`, and so the hook and the permission rules, only
from the folder a chat starts in. Start every Claude Code chat in this repository with the
repository root as its folder, and `cd` into a part to work there. A chat started in a part
folder runs with no guardrail hook. The settings command finds the hook through the chat's
project folder first, then through git from the chat's current folder, so a `cd` elsewhere
doesn't lock the chat.

## If the hook breaks

The hook fails closed, so a broken hook blocks every tool call in this repository,
including the edit that would fix it. Reece restores the last committed copies by hand:
`git checkout -- guardrails/claude_hook.py .claude/settings.json` from the repository root,
then restarts the chat.
