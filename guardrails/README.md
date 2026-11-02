# Guardrails: the checks behind GUARDRAILS.md

[GUARDRAILS.md](../GUARDRAILS.md) holds the master rules for the Fjordvik project. This
folder holds what enforces them. Attena, the guardrails code chat, maintains both; other
chats suggest changes in `proposals/`.

| File | What it does |
| --- | --- |
| `check.py` | Checks the repository: the rules file's fingerprint, em dashes, common American spellings, "projects" counts, secrets, `.env` files, files over 50 MB, the old local repositories, and an optional private list of banned names kept outside the repository. `python guardrails/check.py` prints any findings. |
| `shared_tests.py` | Tests every part runs through its own `tests/test_guardrails.py`: the checker finds nothing, the fingerprint matches, the checker catches planted breaches, and the hook blocks what it should and allows normal work. |
| `claude_hook.py` | The Claude Code hook in `../.claude/settings.json`. Before a tool call runs, it blocks hand edits to generated data, any `.env` file, `git add .`, `-A`, `-u`, `git commit -a`, hook bypasses and force pushes. |
| `pre-commit` | Runs `check.py` before each commit, once installed. |
| `proposals/` | Suggested changes to the rules, one file each, for Attena to review. |

## Installing the pre-commit check (Reece, by hand)

Only Reece changes git hook settings (RULES.md and GUARDRAILS.md rule G2). To install the
check for this clone, copy `guardrails/pre-commit` to the file `pre-commit` in the
repository's `.git/hooks` folder. To remove it, delete that copy.

## The private banned-names list

`check.py` also reads `%LOCALAPPDATA%\fjordvik-guardrails\banned-terms.txt` if it exists:
one name per line (lines starting with `#` are ignored). It is kept outside the public
repository so the list itself names no one. Without it, that check is skipped.
