# Proposal: a folder for the architecture documents and decision records

Fjordvik code chat, architecture pause, 19 November 2026. Read at commit `f036850` on branch
`architecture/stations-00-03`. Reece chose on 19 November 2026, in this chat's question box,
to keep the architecture documents in `docs/architecture/` with one decision record per
file, which needs Attena's layout map entry first (rule L1). Fjordvik Manufacturing Oy is
fictional and all its data is synthetic.

## Rule

L1, L3 and the layout map ("Project documents").

## The problem

Commit `f036850` added six architecture documents flat in `docs/`, because the map allows
`docs/*.md` but no subfolder: `business-case.md`, `requirements.md`, `architecture.md`,
`threat-model.md`, `decision-log.md` and `data-model.md`. Jasila's research of 19 November
2026 (`raw/inbox/2026-11-19-jasila-fjordvik-architecture-diagrams.md` in the knowledge
folder) recommends eight architecture artefacts in `docs/architecture/`, with decision
records as small numbered files, one per decision, superseded and never edited (Nygard,
2011). Model cards and two process diagrams will follow, so `docs/` would get crowded, and
a front end that reads the folder needs a clear place to look.

## Map entries suggested

Under "Project documents":

- `docs/architecture/*.md`: the architecture documents (business case, requirements,
  solution architecture, threat model, data model, process and sequence diagrams, model
  cards), each with Mermaid diagrams.
- `docs/architecture/adr/NNNN-<title>.md`: architecture decision records, one per
  decision, numbered from `0001`, lower case with hyphens; a record is superseded by a new
  one, never edited after it is accepted.

And in L3's "one home per kind of document": architecture documents in
`docs/architecture/`, decision records in `docs/architecture/adr/`.

## The move

Once the entries exist, this chat moves the six files with `git mv` into
`docs/architecture/` and splits `decision-log.md` into 29 records (`0001` to `0029`) plus
an index (`docs/architecture/adr/README.md` would need an entry too, or the index can live
in `docs/architecture/decisions.md`; Attena's choice). Only the root `README.md` and the six
files themselves cite these paths today, and none has been pushed, so nothing outside the
branch breaks.

## Entries to come (not asked for yet)

Two more will follow once research and Reece's choices settle them, each as its own
proposal: the front end's source and build output (Reece wants Fjordvik's own front end for
viewing these documents; Jasila researches the approach first), and `.github/workflows/`
for continuous integration (proposed decision ADR-028), which a cloud deployment of the
failure risk API would also use.

## What would check it

`check.py` already reads the map. A check on `docs/architecture/adr/` names
(`^\d{4}-[a-z0-9-]+\.md$`) would keep the numbering consistent.

## Until Attena decides

The six documents stay flat in `docs/`; this chat moves nothing.
