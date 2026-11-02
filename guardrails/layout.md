# Repository layout map

Where each kind of file lives in the Fjordvik repository, and why. It keeps the repository
easy to understand as the project grows (GUARDRAILS.md rules L1 to L6). `check.py` reads
this file: a file that matches no entry below fails every part's tests.

**Adding a folder or a new kind of file.** Suggest the entry, with its purpose, in a new
file in `guardrails/proposals/`, or ask Reece. Attena adds it here (rule G9). Scratch work
never needs an entry: it stays in the chat's scratchpad (L5).

**How entries read.** Each entry is a path pattern in backticks, then its purpose. `*`
matches within one folder and `**` matches any depth. `<part>` stands for each part
named on the next line.

Parts: data, mcp, powerbi, power-automate, service-ai

## Repository root

- `README.md`: what Fjordvik is and does, and how to run each part.
- `CLAUDE.md`: working rules for every chat in the repository.
- `GUARDRAILS.md`: the master rules.
- `GUARDRAILS.sha256`: the master rules' fingerprint.
- `.gitattributes`: line-ending settings for the whole repository.
- `.claude/settings.json`: the Claude Code hook that enforces the guardrails.

## Guardrails

- `guardrails/*`: the checks behind GUARDRAILS.md, this map and Attena's working rules.
- `guardrails/proposals/*.md`: suggested rule changes, one file each.

## Project documents

- `docs/*.md`: project-wide documents (company profile, learning guide, plans, methods).
- `docs/process-map.html`: the reporting process map, also published on GitHub Pages.
- `docs/handover/*.md`: handover notes, named `YYYY-MM-DD-fjordvik-<topic>.md`.
- `docs/learning/*.md`: one learning note per service phase, named `phase<N>-<topic>.md`.

## The standard shape of every part

- `<part>/README.md`: what the part does, leading with the business need.
- `<part>/CLAUDE.md`: working rules for the part.
- `<part>/LICENSE`: the part's licence.
- `<part>/pyproject.toml`: the part's Python package and pinned libraries.
- `<part>/.gitignore`: what git leaves out, such as `.venv` and `.env`.
- `<part>/.gitattributes`: line-ending settings for the part.
- `<part>/.env.example`: names of the settings the part reads, never values.
- `<part>/src/**`: the part's Python package.
- `<part>/scripts/*`: command-line scripts that run the part's jobs.
- `<part>/tests/**`: the part's tests.
- `<part>/docs/**`: documents about the part only.
- `<part>/evidence/*`: raw output of test and acceptance runs, flat, named with the run date (L4).

## data

- `data/LICENSE-DATA.md`: the data licence and credits.
- `data/tables/*`: the generated tables every part reads (change only through the generator, D3).
- `data/erp-extract/**`: the generated enterprise resource planning (ERP) extract (D3).
- `data/corpus/**`: the generated manuals and policies (D3).
- `data/generator-truth/**`: the answer key for evaluation only (D3, D10).
- `data/reference/*`: reference data fetched from its publisher, cited (D6).
- `data/sql/*`: database scripts that load the tables.

## mcp

- `mcp/claude_desktop_config.example.json`: an example Claude Desktop connector setting.

## powerbi

- `powerbi/*.pbip`: Power BI project files that open each report.
- `powerbi/Fjordvik*.Report/**`: the report definitions.
- `powerbi/Fjordvik*.SemanticModel/**`: the semantic model definitions.

## power-automate

- `power-automate/expected/**`: expected results the intake tests compare against.
- `power-automate/intake/**`: sample site files, clean and with problems.
- `power-automate/sharepoint/**`: seed data for the SharePoint lists.

## service-ai (from the approved phase plan)

- `service-ai/eval/**`: evaluation sets, written before the code they judge (A9).
- `service-ai/results/**`: committed results with a manifest, which mcp reads.
- `service-ai/outbox/**`: agent drafts (git-ignored, so normally never checked).

## Named exceptions

Each one is a file that doesn't fit the shape above, kept until its owner decides.

- `power-automate/intake_rules.py`: code at a part's top level (L2). The power-automate chat is asked whether to move it (proposal `2026-11-02-attena-power-automate-intake-rules.md`).
- `powerbi/evidence/dax-walkthrough-queries.json`: an evidence file with no run date in its name (L4), the queries behind the dated walkthrough output.
