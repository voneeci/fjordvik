# One learning document for all service phases

Suggested by the Fjordvik phase 2 code chat, 3 November 2026, at Reece's request ("I don't
want these learning documents to become separate documents"). Reece chose, in the question
box: one file in the repository with a section per phase, plus a private Claude Docs copy
with a tab per phase for reading.

1. **Rule:** L3 (GUARDRAILS.md section 5), and the layout map entry for `docs/learning/`.
2. **Wording:** in L3, replace "phase learning notes in `docs/learning/phase<N>-<topic>.md`"
   with:
   > the service AI learning notes in one file, `docs/learning/service-ai.md`, with a
   > contents list and one section per phase (`## Phase <N>: <topic>`), each added when its
   > phase ends

   In `guardrails/layout.md`, replace the `docs/learning/*.md` entry with
   `docs/learning/service-ai.md`: the service AI learning notes, one section per phase.
3. **Why:** Reece wants one document he and readers open once, not a growing set of files.
   Today `check.py` only accepts `phase<N>-<topic>.md` names in `docs/learning/`, so the
   merged file would fail every part's tests until the rule and the map change.
4. **Check:** `check.py`'s name pattern for `docs/learning` (line 73) becomes the single
   name `service-ai.md`, and a test in `shared_tests.py` flags any other file there.
   Review catches a phase that ends without its section.

**Follow-up once this lands** (not for Attena): a code chat merges
`docs/learning/phase1-service-data.md` and `docs/learning/phase2-forecast.md` into
`docs/learning/service-ai.md` with `git mv` and an edit, so history follows the file, and
updates the links in `README.md`, `service-ai/README.md` and `service-ai/CLAUDE.md` (which
says each phase ends with `docs/learning/phase<N>-<topic>.md`). Handover notes already
committed keep the old paths they cite, since git history still holds those files.

## Outcome

Adopted by Attena on 4 November 2026 (Reece approved, in the Attena chat), with the wording
above in L3 and the layout map, and a planted-breach case in `shared_tests.py`. One addition:
until a code chat merges the notes, `check.py` and the map also accept
`phase1-service-data.md` and `phase2-forecast.md` by name, so they keep passing. A new
`phase<N>` file now fails. Once the notes are merged, Attena removes those two names.
