"""Build the site submission workbooks, the SharePoint seed workbooks and the expected results.

  intake/clean/      one workbook per site for December 2025, from the shared data
  intake/problems/   the same month with planted problems (see PROBLEMS below)
  sharepoint/seed/   workbooks to create the SharePoint lists from (Sites, Sources,
                     EmissionFactors, and Emissions for January 2023 to November 2025)
  expected/          what the flow must produce for each file, from intake_rules.py

Every workbook holds one Excel table, because Power Automate's Excel connector only
reads rows inside a table. Run:  python scripts/build_intake_files.py
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from intake_rules import COLUMNS, REPORTING_MONTH, RULES, Reference, accepted_rows, month_key, validate  # noqa: E402

FIXED_TIME = datetime(2026, 1, 5, 9, 0, 0)  # file properties, so rebuilds don't differ

# Planted problems, one kind per site. EE02 sends nothing at all (a missing submission).
PROBLEMS = {
    "FI01": "unit error: purchased electricity entered in MWh instead of kWh",
    "FI03": "missing row: district heating left out",
    "SE01": "duplicate row: diesel entered twice",
    "EE02": "no file: the site misses the deadline",
}


def write_table(path, sheet, table, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(columns)
    for r in rows:
        ws.append([r[c] for c in columns])
    last = chr(ord("A") + len(columns) - 1)
    t = Table(displayName=table, ref=f"A1:{last}{len(rows) + 1}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)
    for i, c in enumerate(columns):
        ws.column_dimensions[chr(ord("A") + i)].width = max(12, len(c) + 4)
    wb.properties.creator = "fjordvik-power-automate"
    wb.properties.created = wb.properties.modified = FIXED_TIME
    wb.save(path)


def submission_rows(ref, site):
    key = str(month_key(REPORTING_MONTH))
    return [{"site_id": site, "month": REPORTING_MONTH, "source_id": r["source_id"],
             "activity_amount": float(r["activity_amount"]), "unit": r["unit"]}
            for r in ref.facts if r["site_id"] == site and r["date_key"] == key]


def with_problem(site, rows):
    rows = [dict(r) for r in rows]
    if site == "FI01":
        for r in rows:
            if r["source_id"] == "S05":
                r["activity_amount"] = round(r["activity_amount"] / 1000, 3)
                r["unit"] = "MWh"
    elif site == "FI03":
        rows = [r for r in rows if r["source_id"] != "S06"]
    elif site == "SE01":
        rows.append(dict(next(r for r in rows if r["source_id"] == "S02")))
    return rows


def main():
    ref = Reference()
    for folder in ("intake", "sharepoint", "expected"):
        if (REPO / folder).exists():
            shutil.rmtree(REPO / folder)

    expected = {"reporting_month": REPORTING_MONTH, "rules": RULES, "clean": {}, "problems": {}}
    log = {"clean": [], "problems": []}
    for site in sorted(ref.sites):
        rows = submission_rows(ref, site)
        name = f"{site}_{REPORTING_MONTH}.xlsx"
        for kind in ("clean", "problems"):
            if kind == "problems" and site == "EE02":
                continue  # no file sent
            these = rows if kind == "clean" else with_problem(site, rows)
            write_table(REPO / "intake" / kind / name, "Submission", "Submission", COLUMNS, these)
            fails = validate(these, COLUMNS, site, ref)
            status = "Rejected" if fails else "Accepted"
            expected[kind][name] = {
                "status": status,
                "rules_failed": sorted({f["rule"] for f in fails}, key=lambda r: int(r[1:])),
                "failures": fails,
                "rows_appended": len(these) if not fails else 0,
                "tco2e_appended": round(sum(r["tco2e"] for r in accepted_rows(these, site, ref)), 6)
                if not fails else 0,
            }
            log[kind].append({"site_id": site, "month": REPORTING_MONTH, "status": status})
    from intake_rules import missing_submissions
    expected["missing_submissions"] = {k: missing_submissions(v, ref) for k, v in log.items()}
    expected["problem_descriptions"] = PROBLEMS

    seed = REPO / "sharepoint" / "seed"
    write_table(seed / "Sites.xlsx", "Sites", "Sites",
                ["site_id", "site_name", "country", "site_type", "contact_email"],
                [{**s, "contact_email": ""} for s in ref.sites.values()])
    sources = {r["source_id"]: r for r in __import__("intake_rules").read_csv("dim_source")}
    write_table(seed / "Sources.xlsx", "Sources", "Sources",
                ["source_id", "source_name", "scope", "category", "unit"],
                [{**s, "scope": int(s["scope"]), "unit": ref.units[k]} for k, s in sources.items()])
    write_table(seed / "EmissionFactors.xlsx", "EmissionFactors", "EmissionFactors",
                ["source_id", "country", "emission_factor"],
                [{"source_id": s, "country": c, "emission_factor": f}
                 for (s, c), f in sorted(ref.factors.items())])
    emissions_cols = ["date_key", "site_id", "source_id", "activity_amount", "unit",
                      "emission_factor", "tco2e"]
    write_table(seed / "Emissions.xlsx", "Emissions", "Emissions", emissions_cols,
                [{"date_key": int(r["date_key"]), "site_id": r["site_id"], "source_id": r["source_id"],
                  "activity_amount": float(r["activity_amount"]), "unit": r["unit"],
                  "emission_factor": float(r["emission_factor"]), "tco2e": float(r["tco2e"])}
                 for r in ref.central_before()])

    out = REPO / "expected" / "expected_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Clean: {sum(1 for v in expected['clean'].values() if v['status'] == 'Accepted')} of "
          f"{len(expected['clean'])} accepted. Problems: "
          + ", ".join(f"{k} {v['status']} {v['rules_failed']}" for k, v in expected["problems"].items())
          + f". Missing: {expected['missing_submissions']['problems']}")


if __name__ == "__main__":
    main()
