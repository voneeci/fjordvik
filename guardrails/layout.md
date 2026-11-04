# Repository layout map

Where each kind of file lives in the Fjordvik repository, and why. It keeps the repository
easy to understand as the project grows (GUARDRAILS.md rules L1 to L6). `check.py` reads
this file: a file that matches no entry below fails every part's tests.

**Adding a folder or a new kind of file.** Suggest the entry, with its purpose, in a new
file in `guardrails/proposals/`, or ask Reece. Attena adds it here (rule G9). Scratch work
never needs an entry: it stays in the chat's scratchpad (L5).

**How entries read.** Each entry is a path pattern in backticks, then its purpose. `*`
matches within one folder and `**` matches any depth. `<part>` stands for each part
named on the next line. Only entries after that line count. `check.py` also checks names:
handovers, learning notes and proposals follow GUARDRAILS.md L3, evidence names carry the
run date as a valid calendar date (L4), and no file or folder name looks like a scratch,
temporary or backup file (L5).

Parts: data, mcp, powerbi, power-automate, service-ai

## Repository root

- `README.md`: what Fjordvik is and does, and how to run each part.
- `CLAUDE.md`: working rules for every chat in the repository.
- `GUARDRAILS.md`: the master rules.
- `GUARDRAILS.sha256`: the master rules' fingerprint.
- `.gitattributes`: line-ending settings for the whole repository.
- `.claude/settings.json`: the Claude Code hook that enforces the guardrails.

## Guardrails

- `guardrails/README.md`: what each guardrails file does.
- `guardrails/CLAUDE.md`: Attena's working rules.
- `guardrails/layout.md`: this map.
- `guardrails/check.py`: the checks a script can run.
- `guardrails/claude_hook.py`: the Claude Code hook.
- `guardrails/shared_tests.py`: the guardrail tests every part runs.
- `guardrails/pre-commit`: runs `check.py` before each commit, once Reece installs it.
- `guardrails/.gitattributes`: keeps PDF reports in `evidence/` binary, so git doesn't change their bytes.
- `guardrails/proposals/*.md`: suggested rule changes, one file each, named `YYYY-MM-DD-<chat>-<topic>.md`.
- `guardrails/evidence/*`: raw output and reports of guardrails-only tests, named with the run date (L4).

## Project documents

- `docs/*.md`: project-wide documents (company profile, learning guide, plans, methods).
- `docs/process-map.html`: the reporting process map, also published on GitHub Pages.
- `docs/handover/*.md`: handover notes, named `YYYY-MM-DD-fjordvik-<topic>.md`.
- `docs/learning/service-ai.md`: the service AI learning notes, one section per phase.
- `docs/learning/phase1-service-data.md`: waiting to be merged into `service-ai.md`.
- `docs/learning/phase2-forecast.md`: waiting to be merged into `service-ai.md`.

## The standard shape of every part

- `<part>/README.md`: what the part does, leading with the business need.
- `<part>/CLAUDE.md`: working rules for the part.
- `<part>/LICENSE`: the part's licence.
- `<part>/pyproject.toml`: the part's Python package and pinned libraries.
- `<part>/.gitignore`: what git leaves out, such as `.venv` and `.env`.
- `<part>/.gitattributes`: line-ending settings for the part.
- `<part>/.env.example`: names of the settings the part reads, never values.
- `<part>/src/**/*.py`: the part's Python package.
- `<part>/scripts/*.py`: command-line scripts that run the part's jobs.
- `<part>/scripts/*.ps1`: PowerShell scripts that run the part's jobs.
- `<part>/tests/**/*.py`: the part's tests.
- `<part>/tests/fixtures/**`: small input files the tests read.
- `<part>/docs/**/*.md`: documents about the part only.
- `<part>/docs/images/**/*.png`: images the part's documents show.
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
- `powerbi/docs/measure-examples.json`: the measure examples the measure guide is built from.

## power-automate

- `power-automate/expected/**`: expected results the intake tests compare against.
- `power-automate/intake/**`: sample site files, clean and with problems.
- `power-automate/sharepoint/**`: seed data for the SharePoint lists.

## service-ai (from the approved phase plan)

- `service-ai/eval/**/*.json`: evaluation sets, written before the code they judge (A9).
- `service-ai/eval/**/*.jsonl`: evaluation sets, one item per line.
- `service-ai/eval/**/*.csv`: evaluation sets as tables.
- `service-ai/eval/**/*.md`: notes on how each evaluation set was written.
- `service-ai/results/**/*.csv`: committed results, which mcp reads.
- `service-ai/results/**/*.json`: committed results and their manifest of checksums.
- `service-ai/results/**/*.parquet`: committed results too large for CSV.
- `service-ai/results/**/*.md`: notes on each result.
- `service-ai/results/**/*.png`: charts of the results.
- `service-ai/outbox/**`: agent drafts (git-ignored, so normally never checked).

## Named exceptions

Each one is a file that doesn't fit the shape above, kept until its owner decides.

- `power-automate/intake_rules.py`: code at a part's top level (L2). The power-automate chat is asked whether to move it (proposal `2026-11-02-attena-power-automate-intake-rules.md`).
- `powerbi/evidence/dax-walkthrough-queries.json`: an evidence file with no run date in its name (L4), the queries behind the dated walkthrough output.
