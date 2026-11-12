# Proposal: a home for test logs a chat saves for another part

Fjordvik code chat, phase 3 (service-ai), 12 November 2026. Read at commit `bc7b4ff`. Reece chose
on 12 November 2026, in this chat's question boxes, to ask Attena for this. Fjordvik
Manufacturing Oy is fictional and all its data is synthetic.

## Rule

G4, L1, L4 and the layout map (`<part>/evidence/*`).

## The problem

G4 says every test run saves its raw output in "its part's `evidence/` folder". Chats often run
another part's tests: builder chats run the data tests after any change (root `CLAUDE.md`), the
data chat ran every part's tests after the phase 3 inputs, and Attena runs all five after each
guardrail change. Those logs land inside folders the chat does not own. For `data/`, this breaks
a builder chat's limit of writing nothing under `data/`. Reece's view (12 November 2026): test
logs don't belong in the data folder.

About 80 such logs exist today, for example:

| Written by | Saved in other parts' folders as |
| --- | --- |
| Attena | `pytest-guardrails-*-YYYY-MM-DD.txt`, 14 runs in each of the five parts |
| The phase 2 service-ai chat | `pytest-forecast-2026-11-03.txt` in data, mcp, powerbi, power-automate; `pytest-forecast-fixes-2026-11-03.txt` in data |
| The phase 3 inputs data chat | `pytest-phase3-inputs-2026-11-11.txt` in mcp, powerbi, power-automate, service-ai |
| The service data chat (phase 1) | `pytest-service-data-2026-11-02.txt` in the other parts |

## Wording suggested

**Option 1 (suggested): logs stay with the chat that ran them.** Add to G4:

> A chat that runs another part's tests saves the output in the evidence folder of the part it
> works in (Attena: `guardrails/evidence/`), named `pytest-<topic>-<part run>-YYYY-MM-DD.txt`,
> for example `service-ai/evidence/pytest-ml-data-2026-11-12.txt`. Its handover says where.

Change the map's `<part>/evidence/*` line to say it may hold another part's run under that name.
`guardrails/CLAUDE.md` ("save the output in each part's `evidence/` folder") would change to
match, so Attena's own runs go to `guardrails/evidence/`.

**Option 2: one shared folder.** A new root folder `evidence/` for every cross-part run, named
`pytest-<topic>-<part run>-YYYY-MM-DD.txt`. Needs a map entry (L1) and a line in L4.

## The existing logs (Reece asked for them to move too)

L4 says evidence is never moved or renamed, so notes that cite a path stay right. Reece asked
on 12 November 2026 for the existing cross-part logs to move to the new home with names that
match their phase. That needs a one-off exception to L4, which only Attena can make with Reece's
yes. Suggested way:

1. List every cross-part log with `git log --diff-filter=A --format=... -- <part>/evidence/` to
   find the chat that wrote it.
2. `git mv` each to the new home and name, for example
   `data/evidence/pytest-forecast-2026-11-03.txt` to
   `service-ai/evidence/pytest-forecast-data-2026-11-03.txt`.
3. Leave old handovers as they are, and write a table of old path to new path (in the proposal
   outcome or `guardrails/evidence/`), so every old citation can still be followed. `git log
   --follow` also finds each file.
4. A line in L4's change history naming the one-off move.

## Why

Each folder then holds only what its owner wrote (RULES.md: one editor per file), `data/` holds
only data, and a builder chat's "nothing under `data/`" limit no longer clashes with G4.

## What would check it

`check.py` already reads the map. A check could flag a new evidence file whose `<part run>` names
another part but which sits in that part's own folder.

## Until Attena decides

This chat saved the phase 3 data test log as `service-ai/evidence/pytest-ml-data-2026-11-12.txt`
(Option 1's form) and moved nothing else. The handover says so.
