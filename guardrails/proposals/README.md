# Suggested changes to GUARDRAILS.md

One new file per suggestion, named `YYYY-MM-DD-<chat>-<topic>.md`, with:

1. **Rule:** its identifier (for example D3), or "new".
2. **Wording:** the rule as you would write it.
3. **Why:** what went wrong or could go wrong without it.
4. **Check:** the test, hook or review that would enforce it.

Attena reviews each suggestion with Reece, makes the change in `GUARDRAILS.md`, updates
`GUARDRAILS.sha256`, adds a line to the change history and notes the outcome at the end of
the suggestion file. Never edit `GUARDRAILS.md` or `GUARDRAILS.sha256` yourself.
