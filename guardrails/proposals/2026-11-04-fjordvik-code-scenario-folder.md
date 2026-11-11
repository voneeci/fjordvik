# Proposal: a generated folder for the phase 3 scenarios

Fjordvik code chat, phase 3, 4 November 2026. Read at commit `66aca55`. Reece approved this in
the phase 3 plan. Fjordvik Manufacturing Oy is fictional and all its data is synthetic.

## Rule

L1 and the layout map; D3.

## Wording

Add to the data section of `guardrails/layout.md`:

> - `data/scenarios/*`: the checksum manifest of the control and drift scenarios and the planning
>   inputs for service-ai, written by the generator (D3).

Add `data/scenarios/` to `GENERATED` in `guardrails/check.py` and `guardrails/claude_hook.py`, and
to the folders named in D3.

## Why

Phase rules E2 and M5 need a control dataset with the warning signals off and two drift scenarios.
Each is a copy of `fact_asset_telemetry` at about 20 MB. Reece chose to build them on demand, because
three more copies don't belong in a public repository and the generator takes about 11 seconds. So
git holds only two small files: a manifest of their checksums, and the two visit costs that
service-ai reads. A new folder under `data/` needs a map entry first (L1). The folder's files come
from the generator, so D3 should cover it.

## What would check it

`check.py` already reads the map. The hook and the permission rules cover every folder in
`GENERATED`. The data chat adds a test that the built files match the manifest.

## Also noted

- No entry is needed for saved model files such as `.joblib`: they aren't committed, because the
  training run reproduces them (G10).
- The scenario files themselves go to `service-ai/build/ml-scenarios/`, which `service-ai/.gitignore`
  already leaves out, so nothing is written under `data/` when service-ai builds them.

## Outcome

Accepted by Attena on 11 November 2026, with Reece's approval of the plan in the Attena chat,
and committed on main together with this outcome.

- `guardrails/layout.md` has the entry as worded above.
- `data/scenarios/` is in `GENERATED` in `guardrails/check.py` and `guardrails/claude_hook.py`,
  and D3 in `GUARDRAILS.md` names it, with a change-history line.
- One addition: the permission rules in `.claude/settings.json` list each generated folder by
  name rather than reading `GENERATED`, so a deny rule `Edit(/data/scenarios/**)` was added.
  Chats open in the repository root restart to pick it up.
- `guardrails/shared_tests.py` has hook cases: writes and deletes in `data/scenarios/` are
  blocked, and reading it, or writing in `service-ai/build/ml-scenarios/`, is allowed.
- Still for the data chat: the test that the built files match the manifest.
