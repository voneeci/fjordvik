# Fjordvik Power Automate: monthly site file intake

Every month, each of Fjordvik Manufacturing Oy's six sites in Finland, Sweden and Estonia
sends the sustainability team a spreadsheet of the fuel, energy, refrigerant, flights and
waste it used. These two Power Automate cloud flows take over that routine: they collect
each file, check it against ten written rules, load accepted files into a central list,
tell sites what to fix, and chase sites that have not sent a file.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

> **Status, 12 October 2026:** the design, the rules, the test files and the tests are
> done and pass offline. The flows are built in a Microsoft 365 trial tenant next, following
> [docs/tenant-setup.md](docs/tenant-setup.md); their exports and screenshots will go in
> `flows/` and `docs/images/`.

## Problem

Every month a sustainability team receives a spreadsheet from each site, opens each one,
checks the numbers by eye, copies them into a central file, works out emissions, and emails
sites whose files are late or wrong. It is slow, and the checks depend on who is doing
them: a kWh/MWh slip or a duplicated row can reach the annual report unnoticed.

## Approach

- **One upload, one run.** A site uploads its Excel file to a SharePoint folder; the
  intake flow starts on its own.
- **Ten written rules** (R1 to R10): columns, site, month, known sources, units, numbers,
  duplicates, gaps, a change check against the same month last year, and a refusal to load
  a month twice. See [docs/intake-rules.md](docs/intake-rules.md).
- **Whole file or nothing.** An accepted file adds its rows with the factor looked up and
  tCO2e worked out; a rejected file adds nothing and its site gets an email listing what to
  fix; a technical failure removes any rows the run wrote. Every run is logged.
- **A reminder flow** on day 5 chases sites with no accepted file.
- **The rules exist twice:** as flow actions, and in plain Python (`intake_rules.py`) as
  the reference the flow is tested against.

## Architecture

```
Site Excel file ──upload──> SharePoint: Site submissions/Incoming
                                   │  trigger: When a file is created (properties only)
                                   ▼
                     Flow 1: Fjordvik - Site file intake (Power Automate)
                     reads the Submission table (Excel Online), checks R1 to R10
                        │ all pass                         │ any fail
                        ▼                                  ▼
          Emissions list (+ factor, tCO2e)        email to site, file to Rejected
          IntakeLog: Accepted, file to Processed  IntakeLog: Rejected
                        │
                        ▼
             Power BI and the MCP connector read the central data

Flow 2: Fjordvik - Monthly submission reminder (day 5) ──> emails sites with no accepted file
```

Details: [flow design](docs/flow-design.md), [SharePoint lists](docs/sharepoint-lists.md),
[run statuses](docs/run-statuses.md).

### The test files

| Folder | Holds |
| --- | --- |
| `intake/clean/` | December 2025 file for each of the six sites, built from the shared data in `../data/tables` |
| `intake/problems/` | The same month with planted problems: Tampere's electricity in MWh, Oulu's district heating left out, Gothenburg's diesel entered twice, and no file from Tartu |
| `sharepoint/seed/` | Workbooks to create the Sites, Sources, EmissionFactors and Emissions lists (Emissions: January 2023 to November 2025) |
| `expected/` | What the flows must produce for every file |

## How to run

The offline part needs Python 3.10 or newer with pytest and openpyxl.

```bash
python -m pytest
```

The rules read the repository's shared `../data/tables` folder. To rebuild the test files
after a data change: `python scripts/build_intake_files.py`. Building the flows: [docs/tenant-setup.md](docs/tenant-setup.md).

## Test evidence

```
python -m pytest -q
..........................
26 passed
```

| Test file | What it proves |
| --- | --- |
| `test_intake.py` (21) | Clean files are accepted; each problem file fails exactly its planned rules; loading the six clean December files on top of the seeded list reproduces all 1,422 shared emission rows exactly; a second load of a month is refused; each remaining rule catches its own problem; refrigerant is exempt from the change check; the missing-submission logic lists the right sites; every workbook holds one named table |
| `test_docs.py` (3) | Every rule is documented; the documented row counts and columns match the seed workbooks |
| `test_data.py` (2) | The shared data matches its manifest's checksums, and the rules read that folder |

The flows will be checked against `expected/expected_results.json` in nine test runs
(tenant-setup.md, Part D).

## Limitations

- **Not yet built in a tenant.** Two behaviours could not be confirmed from Microsoft's
  documentation and are checked on the first run: how the Excel connector returns numbers,
  and whether `isFloat()` is available (flow-design.md lists both with fallbacks).
- **Trial tenant.** Lasts 30 days and needs a payment card; the flows stop when it ends.
  The exported solution keeps the work.
- **R9's range is a business rule** (half to double the same month last year), not a
  published figure.
- **One reporting month per file**, and corrections to an accepted month need a data owner
  to remove the old rows first.

## Next steps

- Build and test the flows in the trial (tenant-setup.md), export them to `flows/`, add
  screenshots and the evidence test.
- Point Power BI at the Emissions list instead of the CSV files, and refresh it at the end
  of each accepted run.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([data/LICENSE-DATA.md](../data/LICENSE-DATA.md)).
