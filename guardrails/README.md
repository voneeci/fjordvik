# Guardrails: the checks behind GUARDRAILS.md

[GUARDRAILS.md](../GUARDRAILS.md) holds the master rules for the Fjordvik project. This
folder holds what enforces them. Attena, the guardrails code chat, maintains both; other
chats suggest changes in `proposals/`.

| File | What it does |
| --- | --- |
| `check.py` | Checks the repository: the rules file's fingerprint, em dashes, common American spellings, "projects" counts, secrets and connection strings, `.env` files, files over 50 MB, the old local repositories, and an optional private list of banned names kept outside the repository. `python guardrails/check.py` prints any findings. |
| `shared_tests.py` | Tests every part runs through its own `tests/test_guardrails.py`: the checker finds nothing, the fingerprint matches, the checker catches planted breaches, and the hook blocks, asks or allows as it should. |
| `claude_hook.py` | The Claude Code hook in `../.claude/settings.json`. Before a tool call runs, it blocks hand edits and shell writes to generated data, any `.env` file (a quoted search pattern on piped file names may name one), the private banned-names list, `git add .`, `-A`, `-u`, `git commit -a`, hook bypasses and force pushes. It asks Reece before any edit to the guardrail files (rule G9), and it blocks any call it cannot read. |
| `pre-commit` | Runs `check.py` before each commit, once installed. |
| `proposals/` | Suggested changes to the rules, one file each, for Attena to review. |
| `CLAUDE.md` | Attena's working rules for this folder. |

## Installing the pre-commit check (Reece, by hand)

Only Reece changes git hook settings (RULES.md and GUARDRAILS.md rule G2). To install the
check for this clone, copy `guardrails/pre-commit` to the file `pre-commit` in the
repository's `.git/hooks` folder. To remove it, delete that copy.

## The private banned-names list (Reece, by hand)

`check.py` also reads `%LOCALAPPDATA%\fjordvik-guardrails\banned-terms.txt` if it exists:
one name per line (lines starting with `#` are ignored). It is kept outside the public
repository so the list itself names no one. Without it, that check is skipped and
`check.py` prints a notice. The hook stops every chat reading or writing the list, so
only Reece creates and edits it:

1. In PowerShell, run `New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\fjordvik-guardrails"`.
2. Run `notepad "$env:LOCALAPPDATA\fjordvik-guardrails\banned-terms.txt"`, choose Yes to create it, type one name per line, and save.
3. From the repository root, run `python guardrails\check.py`. The notice is gone, and any line starting `D2` names a file that holds a banned name (never the name itself).

## If the hook breaks

The hook fails closed, so a broken hook blocks every tool call in this repository,
including the edit that would fix it. Reece restores the last committed copy by hand:
`git checkout -- guardrails/claude_hook.py` from the repository root, then restarts the
chat.
