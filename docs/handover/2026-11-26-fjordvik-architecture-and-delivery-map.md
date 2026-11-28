# Handover: Fjordvik, the architecture block and the delivery map review

Date: 2026-11-26   Chat: Fjordvik code chat (also acting as Attena for the guardrail changes)
Read from: git `cb2b661` on `main`, level with `origin/main`. The working tree was clean.

Fjordvik Manufacturing Oy is fictional and all its data is synthetic. The emission factors are
illustrative, not cited.

## Done (19 to 26 November 2026)

- **Architecture documents for delivery map stations 00 to 03:** `docs/business-case.md`,
  `docs/requirements.md`, `docs/architecture.md`, `docs/threat-model.md`, `docs/data-model.md`
  and `docs/decision-log.md` (architecture decision records ADR-001 to 032).
- **25 drawings**, with one public page of them: `docs/architecture-drawings.html`, built by
  `docs/site/drawings/build.py`, live at
  https://voneeci.github.io/fjordvik/docs/architecture-drawings.html. The README has a section
  on how to view it, and the repository's About link points to it.
- **Data dictionary:** `docs/data-dictionary.xlsx`, built by
  `python -m fjordvik_data.dictionary` in `data/`. Every sheet carries the synthetic notice.
- **Guardrails** (as Attena): the 12 gaps for the API, the landing zone and the dashboards
  (rules D8, D18, A1, A14, G5, G9, G12, C1, P1, P2), the fixes from Jinny's review and recheck,
  layout entries, and a root `.gitignore`.
- **Review against all eleven stations of the delivery map:** a gap report (private document,
  linked below), Reece's decisions, and the business case, gate G1 and gate G2 signed.
- **Merged:** pull request 4 (`915dd4d`) and pull request 5 (`cb2b661`).

## Checked

- `python guardrails/check.py` at `f10e10f`: "Guardrails: no findings" (the private
  banned-names list is not on this laptop, so rule D2 was skipped).
- data, full suite, 26 November: 140 passed
  (`data/evidence/pytest-delivery-map-decisions-2026-11-26.txt`).
- service-ai, full suite, 26 November: 61 passed
  (`service-ai/evidence/pytest-pr4-review-fixes-2026-11-26.txt`).
- powerbi, 26 November: 579 passed, 154 skipped
  (`powerbi/evidence/pytest-review-minor-fixes-2026-11-26.txt`). The 154 live tests last ran on
  31 October 2026.
- mcp 83 passed and power-automate 30 passed, full suites, 25 November
  (`<part>/evidence/pytest-guardrails-drawings-page-2026-11-25.txt`); their guardrail tests
  passed again on 26 November.
- GitHub Pages built `cb2b661`, and the drawings page answered 200, on 26 November.
- Not checked: the full mcp, power-automate, powerbi and service-ai suites after pull request 5,
  which changed documents only.

## Decisions (Reece, in question boxes)

- 19 November: the API goes on Azure Container Apps; public pages show group totals only; the
  hook asks before any workflow edit; Fjordvik builds its own front end.
- 26 November, after the gap report:
  - Order of work: continuous integration, then show phases 2 and 3 to a user, then the phase 4
    data step and phase 4, with the API beside phase 4.
  - Scope: the API, the HTML dashboards, the landing zone and the front end are all in.
  - The bought field service product is set aside.
  - Phase 3's three missed controls are carried as stated limits.
  - ADR-026 to 029 are accepted. None is built.
  - Targets are set before go-live.
  - The API's registry is Azure Container Registry Basic.
  - The business case, G1 and G2 are signed, each with its known gaps.

## Working documents (the whole project so far)

| Document | Path or link | What it is | Status | Fresh chat |
|---|---|---|---|---|
| Project rules | `CLAUDE.md`, `GUARDRAILS.md`, `guardrails/layout.md` | Working rules, master guardrails, where files may sit | Current | Read first |
| Overview | `README.md` | The business needs, the parts, the seven service AI capabilities | Current | Read first |
| Gap report | https://claude.ai/artifact/TAPdL1r1FrRWxTHcQaRSqD | The project against all eleven stations, with 17 ordered actions (private to Reece) | Current | Read first |
| Gap report note | `C:\Users\reece\Projects\knowledge\raw\inbox\2026-11-26-fjordvik-code-delivery-map-gap-report.md` | The report's findings and decisions as a file | Current, except its "next step" line, which this note replaces | Read first |
| Business case | `docs/business-case.md` | Station 00, second edition | Current, signed | Read first |
| Requirements | `docs/requirements.md` | Station 01: use cases U1 to U14, requirements, metric catalogue | Current, G1 taken | Read first |
| Architecture | `docs/architecture.md` | Station 02: C4 drawings, interfaces, environments, station table, next steps | Current; review gate open | Read first |
| Decision log | `docs/decision-log.md` | ADR-001 to 032, all accepted | Current | Read first |
| Phase rules | `service-ai/docs/phase-rules.md` | Method rules for each service AI phase, with the wider phase 4 and 7 scope | Current | Read first for phase 4 |
| Data model | `docs/data-model.md` | Station 03: conceptual model, data flows, 15 stars, findings | Current, G2 given | Know it exists |
| Threat model | `docs/threat-model.md` | Trust boundaries B1 to B8, five open items | Current; no boundary yet for the four additions | Know it exists |
| Data dictionary | `docs/data-dictionary.xlsx` | Generated workbook, 20 sheets | Current, generated | Know it exists |
| Drawings page | `docs/architecture-drawings.html`, `docs/site/drawings/` | Generated page and its builder | Current, generated | Know it exists |
| Process map | `docs/process-map.html` | The monthly reporting process | Current | Know it exists |
| Company and guides | `docs/company-profile.md`, `docs/learning-guide.md`, `docs/learning/service-ai.md`, `docs/portfolio-project-plan.md`, `docs/portfolio-user-guide.md`, `docs/scorecard-method.md` | Background, the project guide, learning notes, portfolio plan and guide | Current | Know they exist |
| Part documents | `data/README.md`, `mcp/README.md`, `powerbi/README.md`, `power-automate/README.md`, `service-ai/README.md`, and each part's `CLAUDE.md` | What each part does and its rules | Current | Read the part you work in |
| Earlier handovers | `docs/handover/` (seven notes, 30 October to 12 November) | One note per phase | Reference | Read `2026-11-12-fjordvik-phase3-ml.md` before phase 4 |
| Guardrail code | `guardrails/check.py`, `guardrails/claude_hook.py`, `guardrails/shared_tests.py`, `guardrails/README.md` | The checks, the hook and their tests | Current; only Attena edits them | Know they exist |
| Open proposal | `guardrails/proposals/2026-11-12-fjordvik-code-test-log-home.md` | A home for cross-part test logs | No outcome yet | Know it exists |
| Attena notes | `knowledge\raw\inbox\2026-11-19-attena-fjordvik-api-guardrail-check.md`, `2026-11-19-attena-fjordvik-guardrails-recorded.md`, `2026-11-25-attena-fjordvik-guardrail-review-fixes.md` | The 12 gaps, their recording, and the review fixes | Reference | Know they exist |
| Jasila's research | `knowledge\raw\inbox\2026-11-19-jasila-fjordvik-azure-api-deployment.md`, `-data-lake.md`, `-html-dashboards-superseding.md`, `-front-end-superseding.md`, `2026-11-25-jasila-fjordvik-architecture-drawing-review.md` | Research behind the four additions and the drawing review | Reference | Read the API note before the API's paperwork |
| Jinny's reports | `C:\Users\reece\Projects\Project Grow\docs\checks\2026-11-25\` and `2026-11-26\` | Guardrail review, recheck, and the pull request 4 review | Reference; all findings closed | Know they exist |
| Delivery map | https://voneeci.github.io/how-i-build/data-product-delivery-map.html, `C:\Users\reece\Projects\how-i-build\data-product-delivery-map.md` | The process the project is measured against | Current | Know it exists |
| Plan files | `C:\Users\reece\.claude\plans\jolly-percolating-eclipse.md`, `happy-sparking-torvalds.md` | The 3 November phase 7 decisions; the guardrail plan | Superseded by the repository documents | Reference only |
| Drawings review page | https://claude.ai/artifact/5Juq88PDxEqKvxkHDja25q | The private page Reece used to review the drawings | Superseded by the public drawings page | Reference only |
| Star diagram script | `stars_gen.py` in this chat's scratchpad | The script that first wrote the data model stars | Not in the repository and may be cleared; the documents say the drawings are kept by hand | Know it may be gone |

The project has no `STATUS.md`.

## Open

- **Ten of the gap report's 17 actions:** the backlog file (7); a use case, decision record,
  interface contract and threat model boundary for each of the four additions, the API first
  (9); a Definition of Done (10); continuous integration (12); showing phases 2 and 3 to a user
  (13); the phase 4 data step (14); phase 4's evaluation set and constraint checker, by
  different chats (15); a rerun of the 154 live Power BI tests (16); a first tagged release
  with a timed clean rebuild (17). This note completes action 11 once it is merged.
- **Reece:** whether the writing actions (7 and 10) or continuous integration comes first. The
  last question box was left unanswered at the stop.
- **Reece:** the architecture review gate of station 02; who reads the failure risk API (needed
  for its use case); the private banned-names list on this laptop (rule D2 is skipped until it
  is there).
- **Attena:** an outcome for the proposal of 12 November.
- **This note** is on the branch `docs/handover-2026-11-26`, pushed, not merged.
- Not found: a price for Claude usage, and a chosen Microsoft 365 plan with its price.

## Rule changes in this block

`GUARDRAILS.md`, `.claude/settings.json`, the root `CLAUDE.md` and `data/CLAUDE.md` changed.
Every Claude Code chat working in the Fjordvik repository must restart or `/clear`.

## Next step

Reece: say whether to merge the branch `docs/handover-2026-11-26`, and whether the writing
actions or continuous integration come first. Claude, by default in the order Reece set: on a
new branch from `main`, write `docs/backlog.md` (action 7), gathering every open item from the
gap report, the threat model's open items, the architecture next steps and the handovers' open
lists, each with an owner and an order; then the Definition of Done under "Every phase" in
`service-ai/docs/phase-rules.md` (action 10), which needs Reece's yes because it adds to that
file.

## Fresh chat opening message

Load these skills now with the Skill tool, before reading anything else: reece-voice,
chat-prompt, handover-note.
Read `docs/handover/2026-11-26-fjordvik-architecture-and-delivery-map.md`, then read every
document marked "read first" under Working documents.
Reply first with a checklist of every instruction in this message and the note, each marked done
or not done (with the reason). Then continue from Next step.
Before saying you're done, check your work against every line of this message and the note.

## Log

Task: Fjordvik architecture block and delivery map review
Minutes (Reece's time): 1 to 3 hours (his answer on 26 November 2026)
Rework needed: yes. The drawings review page showed raw code when its host stopped drawing the
diagrams, so the page now loads its own renderer. Jinny's guardrail review asked for rework (one
blocker, six findings) and her pull request 4 review found two things to fix and nine minor
ones; all are closed. One mangled file path in `GUARDRAILS.md` was caught and corrected before
it was committed.
