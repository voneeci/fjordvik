# Proposal: let the hook tell a search pattern from touching a .env file

From the Fjordvik code chat, 2 November 2026, at commit `3fab166`.

1. **Rule:** D8 (the check in `guardrails/claude_hook.py`).
2. **Wording:** no change to the rule. Change the check so a shell command that only
   mentions `.env` inside a search pattern (for example `grep -E "...|/\.env$"` to look for
   stray files) is allowed, while reading, copying or editing one stays blocked.
3. **Why:** the hook blocked a read-only check of the staged file list that searched for
   `.env` files. Blocking is the safe side, but a false positive teaches chats to avoid the
   check instead of running it. `check.py` already reports any tracked `.env` file, so the
   search was not needed that time.
4. **Check:** add the blocked command to the "allowed" cases in
   `guardrails/shared_tests.py`, and keep `cat .env`, `type .env` and `Get-Content .env`
   in the "blocked" cases. One option: block only when `.env` is an argument of a command
   that reads, copies or edits files (`cat`, `type`, `Get-Content`, `cp`, `copy`, `more`,
   `less`, `head`, `tail`, `sed`, `python` opening it), and allow it inside quoted patterns.
   Attena may judge the false positive acceptable instead and keep the hook as it is.

## Outcome

Accepted and narrowed, 2 November 2026 (Reece chose "narrow" in the Attena chat). The hook
now allows `.env` only inside a quoted pattern of a `grep`, `egrep`, `rg`, `findstr` or
`Select-String` stage that reads from a pipe, with no file-reading option, `$(`, backtick
or `<`. Every other mention stays blocked. The blocked command from this proposal is now
in the "allowed" cases of `guardrails/shared_tests.py`, and `cat .env`, `type .env` and
`Get-Content .env` stay "blocked". Recorded in the GUARDRAILS.md change history.
