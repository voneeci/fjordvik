"""The intake validation rules, written once in plain Python.

The Power Automate flow applies the same rules with its own actions. This file is
the reference: the tests run it against every site file, and the expected results
it produces are what the flow must match when it runs in the tenant.

Each rule has an id (R1 to R10) used in the flow, the run log and the emails.
"""

import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

COLUMNS = ["site_id", "month", "source_id", "activity_amount", "unit"]
REPORTING_MONTH = "2025-12"

# Business rule, not an emission figure: a value below half or above double the
# same month last year is held for a person to check. Wide enough for seasonal
# growth and noise; narrow enough to catch a kWh/MWh slip (a factor of 1,000).
CHANGE_LOW, CHANGE_HIGH = 0.5, 2.0
# Refrigerant top-ups are zero most months, so a ratio against last year means nothing.
NO_CHANGE_CHECK = {"S04"}

RULES = {
    "R1": "The table has exactly the columns site_id, month, source_id, activity_amount, unit",
    "R2": "Every row's site_id is the site the file belongs to",
    "R3": "Every row is for the reporting month",
    "R4": "Every source_id is one this site reports",
    "R5": "Every unit is the unit for that source",
    "R6": "Every activity_amount is a number of zero or more",
    "R7": "No source appears twice",
    "R8": "Every source this site reports is present",
    "R9": "Each amount is between half and double the same month last year",
    "R10": "This site and month are not already loaded",
}


def read_csv(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Reference:
    """What the flow looks up: sites, sources, units, factors, history."""

    def __init__(self, loaded_rows=None):
        self.sites = {r["site_id"]: r for r in read_csv("dim_site")}
        self.facts = read_csv("fact_emissions")
        self.units = {}
        self.factors = {}
        self.expected = defaultdict(set)
        self.history = {}
        for r in self.facts:
            self.units[r["source_id"]] = r["unit"]
            country = self.sites[r["site_id"]]["country"]
            self.factors[(r["source_id"], country)] = float(r["emission_factor"])
            self.expected[r["site_id"]].add(r["source_id"])
            self.history[(r["site_id"], r["source_id"], r["date_key"])] = float(r["activity_amount"])
        # Site-months already in the central list. By default, the state before the
        # December run: January 2023 to November 2025.
        rows = self.central_before() if loaded_rows is None else loaded_rows
        self.loaded = {(r["site_id"], int(r["date_key"])) for r in rows}

    def central_before(self, month=REPORTING_MONTH):
        """The central Emissions list as it stands before the intake run."""
        key = month_key(month)
        return [r for r in self.facts if int(r["date_key"]) < key]


def month_key(month: str) -> int:
    y, m = month.split("-")
    return int(y) * 10000 + int(m) * 100 + 1


def validate(rows, columns, file_site, ref: Reference, month=REPORTING_MONTH):
    """Return a list of failures [{"rule": "R7", "detail": "..."}]; empty means accept."""
    fails = []

    def fail(rule, detail):
        fails.append({"rule": rule, "detail": detail})

    if columns != COLUMNS:
        fail("R1", f"columns are {columns}")
        return fails  # nothing else can be read reliably

    if (file_site, month_key(month)) in ref.loaded:
        fail("R10", f"{file_site} {month} is already in the central list")

    seen = defaultdict(int)
    for i, r in enumerate(rows, start=2):  # row 1 is the header
        if r["site_id"] != file_site:
            fail("R2", f"row {i}: site_id {r['site_id']} in {file_site}'s file")
        if r["month"] != month:
            fail("R3", f"row {i}: month {r['month']}, expected {month}")
        src = r["source_id"]
        seen[src] += 1
        if src not in ref.expected[file_site]:
            fail("R4", f"row {i}: {src} is not reported by {file_site}")
            continue
        if r["unit"] != ref.units[src]:
            fail("R5", f"row {i}: {src} unit {r['unit']}, expected {ref.units[src]}")
        try:
            amount = float(r["activity_amount"])
        except (TypeError, ValueError):
            fail("R6", f"row {i}: activity_amount {r['activity_amount']!r} is not a number")
            continue
        if amount < 0:
            fail("R6", f"row {i}: activity_amount {amount} is negative")
            continue
        if src in NO_CHANGE_CHECK:
            continue
        last_year = ref.history.get((file_site, src, str(month_key(month) - 10000)))
        if last_year:
            ratio = amount / last_year
            if not CHANGE_LOW <= ratio <= CHANGE_HIGH:
                fail("R9", f"row {i}: {src} is {ratio:.3f} times the same month last year")

    for src, n in seen.items():
        if n > 1:
            fail("R7", f"{src} appears {n} times")
    for src in sorted(ref.expected[file_site] - set(seen)):
        fail("R8", f"{src} is missing")
    return fails


def accepted_rows(rows, file_site, ref: Reference, month=REPORTING_MONTH):
    """The rows the flow appends to the central list: factor looked up, tCO2e worked out."""
    country = ref.sites[file_site]["country"]
    out = []
    for r in rows:
        amount = float(r["activity_amount"])
        factor = ref.factors[(r["source_id"], country)]
        out.append({"date_key": month_key(month), "site_id": file_site, "source_id": r["source_id"],
                    "activity_amount": amount, "unit": r["unit"], "emission_factor": factor,
                    "tco2e": round(amount * factor / 1000, 6)})
    return out


def missing_submissions(log_rows, ref: Reference, month=REPORTING_MONTH):
    """Flow 2: sites with no Accepted run-log entry for the month."""
    accepted = {r["site_id"] for r in log_rows if r["month"] == month and r["status"] == "Accepted"}
    return sorted(set(ref.sites) - accepted)
