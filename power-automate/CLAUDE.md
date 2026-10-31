# fjordvik-power-automate

Power Automate intake and reminder flows over the synthetic Fjordvik dataset. One of
four folders in the fjordvik repository: data (source), mcp, powerbi,
power-automate. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` override this file.

## Rules for this repo

- Synthetic data only. Emission factors are illustrative, not cited (Reece's one-off
  exception for the Fjordvik project, 12 October 2026).
- No credentials, tenant passwords or personal email addresses in the repo, including in
  exported flows. Check exports before committing.
- `intake_rules.py` is the reference for the flow. Change a rule there first, rebuild
  (`python scripts/build_intake_files.py`), update docs/intake-rules.md, then change the
  flow. Rebuilding rewrites the workbooks with new zip timestamps but the same content:
  restore unchanged ones with `git checkout -- intake sharepoint` to avoid noise.
- The R9 range (0.5 to 2.0) is a business rule, not a published figure; say so wherever it
  appears.
- Statuses: Accepted, Rejected, Failed. Changing one by hand does nothing; see
  docs/run-statuses.md. Keep that page current if a status changes.
- Planted problems live only in `intake/problems/`; the clean files must reproduce the
  shared data in `..\data\tables` exactly.
- The data is the repository's shared `..\data\tables` folder (`intake_rules.DATA`). Never
  edit it from here; after a data change, rebuild the intake files and rerun the tests.
- Power Automate facts in the docs come from Microsoft Learn pages read on 12 October
  2026; mark anything unconfirmed as "to check during the build".
- Writing: no em dashes, Australian spelling, spell out acronyms on first use.

## Commands

```bash
python scripts/build_intake_files.py           # rebuild intake, seed and expected files
python -m pytest -q                            # 26 tests
```
