# Say where service-ai's learning notes go

From Attena, 2 November 2026. For the service-ai chat. Attena does not edit that part.

1. **Rule:** L3 (GUARDRAILS.md section 6): phase learning notes live in the root
   `docs/learning/phase<N>-<topic>.md`.
2. **Wording:** in `service-ai/CLAUDE.md`, where it says each phase ends with
   `docs/learning/phase<N>-<topic>.md`, write the path from the repository root:

   > ... and writes the root `docs/learning/phase<N>-<topic>.md` (not
   > `service-ai/docs/learning/`).

3. **Why:** the guardrails test of 2 November 2026 (finding B4.7) noted that, read inside the
   part, the current wording points to `service-ai/docs/learning/`. The layout map allows
   only Markdown in `service-ai/docs/`, so a note there would pass the map but split the
   learning notes across two homes, which L3 forbids.
4. **Check:** `check.py` checks names in `docs/learning/`; review catches a note in the
   wrong folder.

## Outcome

Open: waiting for the service-ai chat.
