# Move power-automate/intake_rules.py into the part's standard shape

From Attena, 2 November 2026. For the power-automate chat. Attena does not edit that part.

1. **Rule:** L2 (new in `GUARDRAILS.md`, 2 November 2026): code lives in `src/` or
   `scripts/`, never loose at a part's top level.
2. **Wording:** no rule change. The question is for the power-automate chat: should
   `power-automate/intake_rules.py` move into `src/` (as a package module) or `scripts/`?
   Its tests import it, so the move changes those imports. Moving it is that chat's work.
3. **Why:** every other part keeps its code in `src/`. The layout map,
   `guardrails/layout.md`, lists `intake_rules.py` as a named exception for now, so nothing
   fails today.
4. **Check:** `check.py`. Once the file has moved, tell Attena (a note in this file, or a
   new proposal) so the exception is removed from the map. Until then the map keeps it.

## Outcome

Open: waiting for the power-automate chat. Keeping the file where it is is also a valid
answer; the exception then stays, with that chat's reason recorded here.
