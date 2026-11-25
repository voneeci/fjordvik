"""Build Fjordvik's data dictionary workbook.

    python -m fjordvik_data.dictionary --out <path>.xlsx

Reads the governed tables in data/tables, the Power BI model's measures, the service AI
result files and the curated text in dictionary_text.py, then writes one workbook: a read
me, a column reference, the metric catalogue with yearly values and full lineage, every
field, every Power BI measure, the tables, the rules and tools, and copies of the small
reference tables. Read only: it never writes under data/.

All data is synthetic: Fjordvik Manufacturing Oy is fictional and the emission factors
are illustrative, not cited.
"""

import argparse
import csv
import datetime
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from . import dictionary_text as T
from . import xlsx

DATA = Path(__file__).resolve().parents[2]
REPO = DATA.parent
TABLES = DATA / "tables"
MODEL = REPO / "powerbi" / "FjordvikEmissions.SemanticModel" / "definition" / "tables"
RESULTS = REPO / "service-ai" / "results"
YEARS = (2023, 2024, 2025)
EMISSION_TABLES = ("fact_emissions", "fact_energy_upstream", "fact_purchases", "fact_freight", "fact_use_phase")
SMALL = ("dim_date", "dim_site", "dim_source", "dim_scope3_category", "dim_supplier", "dim_contract", "dim_product",
         "dim_product_group", "dim_region", "dim_product_code", "dim_score_criterion", "dim_part", "bridge_part_compatibility")


def load(name):
    with (TABLES / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def headers():
    out = {}
    for p in sorted(TABLES.glob("*.csv")):
        with p.open(encoding="utf-8", newline="") as f:
            out[p.stem] = next(csv.reader(f))
    return out


# ---------------------------------------------------------------- Power BI measures
def measures():
    """Every measure in the model: name, folder, description, format and DAX."""
    found = []
    for p in sorted(MODEL.glob("*.tmdl")):
        lines = p.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            m = re.match(r"\tmeasure '?([^'=]+?)'?\s*=\s*(.*)$", line)
            if not m:
                continue
            desc = lines[i - 1].strip()[3:].strip() if lines[i - 1].strip().startswith("///") else ""
            dax, folder, fmt, j = [m.group(2).strip()] if m.group(2).strip() else [], "", "", i + 1
            while j < len(lines) and not re.match(r"\t(measure|column|partition|hierarchy|///)", lines[j]):
                prop = re.match(r"\t\t(formatString|displayFolder|lineageTag|formatStringDefinition|annotation|changedProperty|isHidden)\b:?\s*(.*)", lines[j])
                if prop:
                    if prop.group(1) == "formatString":
                        fmt = prop.group(2).strip()
                    if prop.group(1) == "displayFolder":
                        folder = prop.group(2).strip()
                elif lines[j].strip() and not folder and not fmt:
                    dax.append(lines[j].strip())
                j += 1
            found.append({"name": m.group(1).strip(), "table": p.stem, "folder": folder, "description": desc,
                          "format": fmt, "dax": " ".join(d for d in dax if d not in ("```",))})
    return found


def anchor(name):
    """GitHub's heading anchor for a measure in the measure guide."""
    return re.sub(r"[^a-z0-9 -]", "", name.lower()).replace(" ", "-")


# ---------------------------------------------------------------- metric values
class Values:
    """Works out each active metric's value for a calendar year from the tables."""

    def __init__(self):
        self.t = {n: load(n) for n in (*EMISSION_TABLES, "fact_scope2_market", "fact_site_metrics", "fact_sales",
                                       "fact_budget", "fact_product_rating", "dim_score_criterion", "fact_service_event",
                                       "fact_parts_order", "fact_portal_event", "fact_data_issue", "dim_technician",
                                       "dim_source", "dim_customer")}
        self.scope = {r["source_id"]: int(r["scope"]) for r in self.t["dim_source"]}
        self.cat = {r["source_id"]: r["scope3_category"] for r in self.t["dim_source"]}
        self.weight = {r["criterion_id"]: float(r["weight"]) for r in self.t["dim_score_criterion"]}
        self.ship_sites = {r["site_id"] for r in self.t["fact_sales"]}
        self.pump_days = defaultdict(int)
        with (TABLES / "fact_asset_telemetry.csv").open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                self.pump_days[int(r["date_key"][:4])] += 1

    @staticmethod
    def year_of(r, field="date_key"):
        return int(str(r[field])[:4])

    def sum(self, table, column, y, where=lambda r: True, field="date_key"):
        return sum(float(r[column]) for r in self.t[table] if self.year_of(r, field) == y and where(r))

    def em(self, y, where=lambda r: True):
        return sum(self.sum(t, "tco2e", y, where) for t in EMISSION_TABLES)

    def activity(self, y, where):
        return self.sum("fact_emissions", "activity_amount", y, where)

    def avg_fte(self, y):
        by_month = defaultdict(float)
        for r in self.t["fact_site_metrics"]:
            if self.year_of(r) == y:
                by_month[r["date_key"]] += float(r["fte"])
        return sum(by_month.values()) / len(by_month)

    def score(self, y):
        num = den = 0.0
        for r in self.t["fact_product_rating"]:
            if self.year_of(r) == y:
                w = self.weight[r["criterion_id"]]
                num, den = num + int(r["rating"]) * w, den + w
        return num / den

    def events(self, y, kind=None):
        return [r for r in self.t["fact_service_event"]
                if self.year_of(r, "reported_date") == y and (kind is None or r["event_type"] == kind)]

    def value(self, code, y):
        s1 = lambda r: self.scope[r["source_id"]] == 1
        s2 = lambda r: self.scope[r["source_id"]] == 2
        s3 = lambda r: self.scope[r["source_id"]] == 3
        cat = lambda n: (lambda r: self.cat[r["source_id"]] == str(n))
        src = lambda *ids: (lambda r: r["source_id"] in ids)
        unit = lambda u: (lambda r: r["unit"] == u)
        revenue = self.sum("fact_site_metrics", "revenue_eur", y)
        margin = lambda yy: self.sum("fact_sales", "margin_eur", yy)
        quarantined = self.sum("fact_data_issue", "amount_eur", y, lambda r: r["status"] == "Quarantined")
        f = {
            "EM_SCOPE1_TCO2E": lambda: self.em(y, s1),
            "EM_SCOPE2_LOC_TCO2E": lambda: self.em(y, s2),
            "EM_SCOPE2_MKT_TCO2E": lambda: self.sum("fact_scope2_market", "tco2e", y),
            "EM_SCOPE3_TCO2E": lambda: self.em(y, s3),
            "EM_TOTAL_TCO2E": lambda: self.em(y),
            "EM_TOTAL_MKT_TCO2E": lambda: self.em(y) - self.em(y, s2) + self.sum("fact_scope2_market", "tco2e", y),
            "EM_OPERATIONAL_TCO2E": lambda: self.em(y, s1) + self.em(y, s2),
            "EM_PER_MEUR": lambda: self.em(y) / (revenue / 1e6),
            "EM_PER_FTE": lambda: self.em(y) / self.avg_fte(y),
            "EM_GO_SHARE": lambda: self.sum("fact_scope2_market", "activity_amount", y, lambda r: r["contract_id"] != "")
            / self.activity(y, src("S05")),
            "EN_ELECTRICITY_KWH": lambda: self.activity(y, src("S05")),
            "EN_HEAT_GAS_KWH": lambda: self.activity(y, src("S01", "S06")),
            "EN_ENERGY_KWH": lambda: self.activity(y, unit("kWh")),
            "EN_LIQUID_FUEL_L": lambda: self.activity(y, unit("litre")),
            "EN_REFRIGERANT_KG": lambda: self.activity(y, src("S04")),
            "EN_WASTE_T": lambda: self.activity(y, src("S08")),
            "EN_FLIGHTS_PKM": lambda: self.activity(y, src("S07")),
            "EN_ELEC_PER_UNIT": lambda: self.activity(y, lambda r: r["source_id"] == "S05" and r["site_id"] in self.ship_sites)
            / self.sum("fact_sales", "units", y),
            "FIN_REVENUE_EUR": lambda: revenue,
            "FIN_FTE_AVG": lambda: self.avg_fte(y),
            "FIN_REVENUE_PER_FTE": lambda: revenue / self.avg_fte(y),
            "SALES_NET_EUR": lambda: self.sum("fact_sales", "net_sales_eur", y),
            "SALES_UNITS": lambda: self.sum("fact_sales", "units", y),
            "SALES_MARGIN_EUR": lambda: margin(y),
            "SALES_MARGIN_PCT": lambda: margin(y) / self.sum("fact_sales", "net_sales_eur", y),
            "SALES_BUDGET_NET_EUR": lambda: self.sum("fact_budget", "budget_net_sales_eur", y),
            "SALES_VS_BUDGET_EUR": lambda: self.sum("fact_sales", "net_sales_eur", y) - self.sum("fact_budget", "budget_net_sales_eur", y),
            "PF_MARGIN_CHANGE_EUR": lambda: None if y == YEARS[0] else margin(y) - margin(y - 1),
            "PF_SCORE": lambda: self.score(y),
            "PF_USE_PER_KEUR": lambda: self.sum("fact_use_phase", "tco2e", y) / (self.sum("fact_use_phase", "net_sales_eur", y) / 1000),
            "SVC_FAILURES": lambda: len(self.events(y, "Failure")),
            "SVC_FAILURE_SHARE": lambda: len(self.events(y, "Failure")) / len(self.events(y)),
            "SVC_MEDIAN_DOWNTIME_H": lambda: statistics.median(float(r["downtime_hours"]) for r in self.events(y, "Failure")),
            "SVC_MTBF_DAYS": lambda: self.pump_days[y] / len(self.events(y, "Failure")),
            "SVC_TECH_UTILISATION": lambda: sum(float(r["labour_hours"] or 0) for r in self.events(y))
            / (sum(float(r["weekly_hours"]) for r in self.t["dim_technician"])
               * (datetime.date(y + 1, 1, 1) - datetime.date(y, 1, 1)).days / 7),
            "SVC_PARTS_REVENUE_EUR": lambda: self.sum("fact_parts_order", "net_amount_eur", y, field="order_date"),
            "SVC_PORTAL_SHARE": lambda: self.sum("fact_parts_order", "net_amount_eur", y, lambda r: r["channel"] == "Portal", "order_date")
            / self.sum("fact_parts_order", "net_amount_eur", y, field="order_date"),
            "SVC_PORTAL_CLICK_RATE": lambda: self._click_rate(y),
            "EM_CAT1_TCO2E": lambda: self.em(y, cat(1)),
            "EM_CAT3_TCO2E": lambda: self.em(y, cat(3)),
            "EM_CAT4_TCO2E": lambda: self.em(y, cat(4)),
            "EM_CAT5_TCO2E": lambda: self.em(y, cat(5)),
            "EM_CAT6_TCO2E": lambda: self.em(y, cat(6)),
            "EM_CAT9_TCO2E": lambda: self.em(y, cat(9)),
            "EM_CAT11_TCO2E": lambda: self.em(y, cat(11)),
            "DQ_SALES_RECON_EUR": lambda: round(revenue - self.sum("fact_sales", "net_sales_eur", y) - quarantined, 2),
            "DQ_EMISSIONS_RECON_T": lambda: round(self.em(y) - self.recalculated(y), 3),
            "DQ_ISSUES": lambda: sum(1 for r in self.t["fact_data_issue"] if self.year_of(r) == y),
            "DQ_QUARANTINED_EUR": lambda: quarantined,
        }
        return f[code]() if code in f else None

    def recalculated(self, y):
        """Activity times factor, divided by 1,000, over the five emission tables."""
        return sum(float(r["activity_amount"]) * float(r["emission_factor"]) / 1000
                   for t in EMISSION_TABLES for r in self.t[t] if self.year_of(r) == y)

    def _click_rate(self, y):
        shown = [r for r in self.t["fact_portal_event"] if self.year_of(r, "event_date") == y]
        return sum(int(r["clicked"]) for r in shown) / len(shown) if shown else None

    def example(self, code):
        """(value, start, end) for metrics with no yearly value."""
        if code == "SVC_CONTRACT_SHARE":
            c = self.t["dim_customer"]
            return sum(r["service_contract"] != "None" for r in c) / len(c), "2025-12-31", "2025-12-31"
        if code.startswith("AI_"):
            ml = {r["metric"]: float(r["value"]) for r in csv.DictReader((RESULTS / "ml" / "metrics.csv").open(encoding="utf-8"))}
            fc = json.loads((RESULTS / "forecast" / "summary.json").read_text(encoding="utf-8"))
            return {"AI_FORECAST_MASE": (fc["warehouses"]["FI03"]["3-month"]["mase"]["driver_base"], "2025-01-01", "2025-12-31"),
                    "AI_FAILURE_AP_MULTIPLE": (ml["ap_ratio_to_dummy"], "2025-07-01", "2025-12-31"),
                    "AI_WARNED_RECALL": (ml["model_recall_of_warned_failures"], "2025-07-01", "2025-12-31"),
                    "AI_ALERT_COST_EUR": (ml["model_cost_eur"], "2025-07-01", "2025-12-31")}[code]
        return None


def tidy(x, unit=""):
    """Round for display: shares and ratios to 4 places, amounts to 2; whole numbers stay whole."""
    if x is None:
        return ""
    if isinstance(x, int):
        return x
    x = round(x, 4) if ("%" in unit or "ratio" in unit or "times" in unit or abs(x) < 10) else round(x, 2)
    if x == 0:
        return 0
    return int(x) if x.is_integer() and "%" not in unit else x


# ---------------------------------------------------------------- sheets
COLUMN_REFERENCE = {
    "Metrics": [
        ("Code", "The metric's identifier: a theme prefix and a short name. Stable even if a table or measure is renamed."),
        ("Theme", "The area of the business the metric belongs to."),
        ("Status", "Active: worked out from recorded data. Dormant: the data it needs is not recorded yet, so it has no value and stays off the dashboards."),
        ("Metric", "The metric's business name."),
        ("What it measures", "The metric in plain English."),
        ("What it is for", "Why Fjordvik tracks it."),
        ("Actual or derived", "Actual: a figure Fjordvik records and enters. Derived: worked out from actual figures."),
        ("Unit", "The unit of the values."),
        ("Grain", "The finest level the metric can be broken down to."),
        ("How often", "How often the underlying data arrives."),
        ("Owner", "The role responsible for the underlying data."),
        ("Source system", "Where the underlying data comes from."),
        ("How it is worked out", "The calculation in words; for an actual metric, how it is entered."),
        ("Where it is worked out", "Which part of the platform calculates it: the SQL pipeline, Power BI, the connector, the generator or this dictionary."),
        ("Input fields", "The table columns the metric reads (see the Fields sheet)."),
        ("Depends on", "Other metric codes it is worked out from."),
        ("Used by", "Where the metric appears: report pages, Claude tools, models or the API."),
        ("Power BI measure", "The measure that shows it in the reports; its DAX is in powerbi/docs/measure-guide.md."),
        ("Classification", "Proposed for a live deployment: Public, Internal, Confidential or Personal data."),
        ("Public page", "Whether it may appear on a public page: only group-level totals may (rule P1)."),
        ("2023, 2024, 2025", "The metric's value for the calendar year, worked out from the tables on every build. Blank for a dormant metric or one with no yearly value."),
        ("Example value", "The latest value, for orientation; for a model result, the test result."),
        ("Example from, Example to", "The period the example value covers."),
    ],
    "Fields": [
        ("Table", "The table (or result file) the column belongs to."),
        ("Table business name", "The table's business name."),
        ("Column", "The column's name in the data."),
        ("Business name", "What the column is called in plain English."),
        ("What it holds", "The column in plain English."),
        ("Unit", "The unit of the values, where there is one."),
        ("Kind of value", "Text, whole number, decimal or date, read from the values."),
        ("Key", "PK: part of the row's identity. FK: points to a row in another table, named in Joins to."),
        ("Joins to", "The table and column a foreign key points to."),
        ("Blank rows", "How many rows have no value."),
        ("Distinct values", "How many different values the column holds."),
        ("Lowest, Highest", "The smallest and largest value of a number or date column."),
        ("Example", "One value from the data."),
        ("Used by metrics", "The metric codes that read this column."),
        ("Source system", "Where the table's data comes from."),
        ("Owner", "The role responsible for the table's data."),
        ("Classification", "Proposed for a live deployment."),
    ],
    "Measures": [
        ("Measure", "The Power BI measure's name, as shown in the reports."),
        ("Folder", "The group the measure sits in."),
        ("What it shows", "The measure's description, written in the model."),
        ("Metric code", "The catalogue metric it shows; blank for measures that support a visual (titles, labels, bridge steps) or compare periods."),
        ("Format", "How Power BI displays the value."),
        ("DAX", "The formula, on one line."),
        ("Measure guide", "Where the measure is explained with an example value."),
    ],
    "Tables": [
        ("Table", "The table's name in the data."),
        ("Business name", "What the table is called in plain English."),
        ("Kind", "Fact (events to add up), dimension (things to filter and group by) or bridge (links two dimensions)."),
        ("What it is", "The table in plain English."),
        ("What it is for", "Where Fjordvik uses it."),
        ("One row is", "What one row holds."),
        ("Rows", "How many rows the table holds today."),
        ("Source system", "Where its data comes from."),
        ("Owner", "The role responsible for it."),
        ("How often", "How often it changes."),
        ("Classification", "Proposed for a live deployment."),
    ],
    "Rules and tools": [
        ("Kind", "Intake rule (site workbooks), SQL check (ERP extract) or Claude tool (the read-only connector)."),
        ("Name", "The rule's or tool's name."),
        ("What it checks or does", "In plain English."),
        ("Why", "What it protects against or answers."),
        ("Where it runs", "The part of the platform that runs it."),
    ],
}


def read_me(n_metrics, n_fields, n_measures):
    """The read-me sheet, laid out like the council data dictionary: a title band, then
    coloured sections of numbered items, each a bold title over a wrapped description."""
    sections = [
        ("green", "What this document is", [
            ("A generated workbook, not a copy kept by hand",
             "Every sheet is built from the governed tables, the Power BI model, the service AI results and one file of curated "
             "descriptions (data/src/fjordvik_data/dictionary_text.py). A test fails when a column, measure or metric has no "
             "description, or when this workbook differs from a fresh build, so it can't drift from the data."),
            ("Synthetic data only",
             "Fjordvik Manufacturing Oy is a fictional company, and this is a portfolio project. Every figure is synthetic. The "
             "emission factors are illustrative, not cited, and must not be used for real reporting."),
            ("Every column is explained",
             "The Column reference sheet lists every column of every sheet, its kind and what it means."),
            ("Active and dormant metrics",
             "A metric is active only when the data it needs is recorded. A dormant metric has no values and stays off the "
             "dashboards until Fjordvik records what it needs; no estimate or default fills the gap."),
        ]),
        ("blue", "What each sheet is for", [
            ("Metrics", f"The {n_metrics} business metrics, active and dormant: what each measures and is for, its owner and "
                        "source, how it is worked out, its inputs and dependencies, where it is used, and its values for 2023 to 2025."),
            ("Fields", f"All {n_fields} columns in the 31 governed tables and the service AI result files: business name, "
                       "description, unit, kind of value, key role, blanks, range, an example and the metrics that use it."),
            ("Measures", f"The {n_measures} Power BI measures: what each shows, its DAX, the metric it shows and its entry in "
                         "the measure guide."),
            ("Tables", "The 31 governed tables: what one row holds, how many rows there are, the source, the owner and the classification."),
            ("Rules and tools", "The ten intake rules for site workbooks, the SQL checks on the ERP extract and the seven read-only Claude tools."),
            ("Column reference", "What every column of every sheet in this workbook means."),
            *[(t, f"{T.TABLES[t][0]}: {T.TABLES[t][1]} A copy of the table; the large fact tables stay in data/tables.")
              for t in SMALL],
        ]),
        ("blue", "How the sheets connect", [
            ("Metric codes link metrics and fields", "A metric's Input fields name rows on the Fields sheet, and a field's Used "
                                                     "by metrics names the metric codes back."),
            ("Measure names link metrics and measures", "A metric's Power BI measure names a row on the Measures sheet, and a "
                                                        "measure's Metric code names the metric back."),
            ("Table names link fields and tables", "A field's Table names a row on the Tables sheet."),
            ("Key columns link the reference tables", "A column marked FK on the Fields sheet joins to the table named in Joins "
                                                      "to; the small reference tables are the sheets named after them."),
        ]),
        ("orange", "Where to go for more", [
            ("How the data model fits together", "docs/data-model.md: the data model drawings, the data flows, what one row of each table holds, and the owners of each kind of data."),
            ("How the platform fits together", "docs/architecture.md: the system, its containers and the service AI pipeline."),
            ("Every measure's formula", "powerbi/docs/measure-guide.md: each Power BI measure with its DAX and an example value."),
            ("Where each source comes from", "data/README.md: every source, its owner, its system and how often it arrives."),
        ]),
    ]
    rows, styles, merges, heights = [], {}, [], {}

    def add(cells, style=None, merge=True, height=None):
        rows.append(list(cells) + [""] * (10 - len(cells)))
        r = len(rows)
        if style:
            styles.update({(r, c): style for c in range(1, 11)})
        if merge:
            merges.append(f"A{r}:J{r}")
        if height:
            heights[r] = height
        return r

    add(["Fjordvik Data Dictionary: Read Me First"], "title", height=34)
    add(["Built from the repository by python -m fjordvik_data.dictionary in the data folder. Synthetic data only; "
         "the emission factors are illustrative."], "subtitle", height=20)
    add([], merge=False)
    add([], merge=False, height=6)
    for colour, heading, items in sections:
        add([heading], f"{colour}_section", height=24)
        for i, (title, text) in enumerate(items, 1):
            r = add(["!" if colour == "orange" else i, title], f"{colour}_item", merge=False, height=18)
            r2 = add(["", text], f"{colour}_text", merge=False, height=max(18, 14 * -(-len(text) // 105)))
            styles[(r, 1)] = styles[(r2, 1)] = f"{colour}_number"
            merges += [f"A{r}:A{r2}", f"B{r}:J{r}", f"B{r2}:J{r2}"]
        add([], merge=False)
        add([], merge=False)
    return {"name": "Read me", "rows": rows, "styles": styles, "merges": merges, "heights": heights,
            "widths": [4] + [11] * 9, "default_style": lambda r, c: "default"}


def table_sheet(name, rows, widths, wrap=(), freeze="A2", zoom=None, table=None):
    """A data sheet laid out like the council dictionary's: an Excel table in the blue
    Medium 2 style with banded rows, a bold white header and a bold first column."""
    wrap = set(wrap)

    def style(r, c):
        if r == 1:
            return "head"
        if c == 1:
            return "cell_first"
        return "cell_wrap" if c in wrap else "cell"
    return {"name": name, "rows": rows, "widths": widths, "default_style": style, "heights": {1: 26},
            "freeze": freeze, "zoom": zoom, "table": table or re.sub(r"\W", "_", name)}


def column_reference_rows(sheet_headers):
    """One row per column of every sheet: the sheet, the column, its kind and its meaning."""
    def kind(col):
        if col in ("Code", "Measure", "Table", "Name", "Column") or col.endswith("_id") or col.endswith("_key"):
            return "key"
        if col in ("2023", "2024", "2025", "Rows", "Blank rows", "Distinct values", "Lowest", "Highest", "Example value"):
            return "number"
        if col in ("Example from", "Example to"):
            return "date"
        return "text"
    out = [["Sheet", "Column", "Kind", "What it is and why it's there"]]
    for sheet, cols in COLUMN_REFERENCE.items():
        for col, meaning in cols:
            parts = col.split(", ")
            for part in (parts if len(parts) > 1 and all(p in sheet_headers.get(sheet, []) for p in parts) else [col]):
                out.append([sheet, part, kind(part), meaning])
    for t in SMALL:
        for col in sheet_headers[t]:
            bname, desc, unit = T.COLUMN_OVERRIDES.get((t, col)) or T.COLUMNS[col]
            out.append([t, col, kind(col), f"{bname}: {desc}" + (f" Unit: {unit}." if unit and unit != "See unit" else "")])
    return out


def build():
    hdr = headers()
    tables = {n: load(n) for n in hdr if n != "fact_asset_telemetry"}
    vals = Values()
    ms = measures()
    keys = {"date_key": "dim_date", "site_id": "dim_site", "source_id": "dim_source", "supplier_id": "dim_supplier",
            "contract_id": "dim_contract", "product_id": "dim_product", "region_id": "dim_region",
            "product_group": "dim_product_group", "criterion_id": "dim_score_criterion", "customer_id": "dim_customer",
            "asset_id": "dim_asset", "part_id": "dim_part", "technician_id": "dim_technician",
            "scope3_category": "dim_scope3_category", "sales_product_id": "dim_product", "made_at_site_id": "dim_site",
            "home_site_id": "dim_site", "based_on_source_id": "dim_source", "service_event_id": "fact_service_event"}
    pk = {"dim_date": ["date_key"], "dim_site": ["site_id"], "dim_source": ["source_id"], "dim_scope3_category": ["scope3_category"],
          "dim_supplier": ["supplier_id"], "dim_contract": ["contract_id"], "dim_product": ["product_id"],
          "dim_product_group": ["product_group"], "dim_region": ["region_id"], "dim_product_code": ["business_unit", "local_item_number"],
          "dim_score_criterion": ["criterion_id"], "dim_customer": ["customer_id"], "dim_asset": ["asset_id"], "dim_part": ["part_id"],
          "dim_technician": ["technician_id"], "fact_service_event": ["event_id"], "fact_data_issue": ["issue_id"],
          "fact_parts_order": ["order_id", "order_line"], "fact_portal_event": ["event_id"],
          "bridge_part_compatibility": ["part_id", "product_group"]}

    # Metrics
    used_by = defaultdict(list)
    m_rows = [["Code", "Theme", "Status", "Metric", "What it measures", "What it is for", "Actual or derived", "Unit", "Grain",
               "How often", "Owner", "Source system", "How it is worked out", "Where it is worked out", "Input fields",
               "Depends on", "Used by", "Power BI measure", "Classification", "Public page", "2023", "2024", "2025",
               "Example value", "Example from", "Example to"]]
    for m in T.METRICS:
        for f in m["inputs"]:
            used_by[f].append(m["code"])
        ys = [tidy(vals.value(m["code"], y), m["unit"]) if m["status"] == "Active" else "" for y in YEARS]
        ex = vals.example(m["code"]) if m["status"] == "Active" else None
        if ex:
            exv, exf, ext = tidy(ex[0], m["unit"]), ex[1], ex[2]
        elif m["status"] == "Active" and ys[-1] != "":
            exv, exf, ext = ys[-1], "2025-01-01", "2025-12-31"
        else:
            exv = exf = ext = ""
        m_rows.append([m["code"], m["theme"], m["status"], m["name"], m["description"], m["use"], m["kind"], m["unit"],
                       m["grain"], m["frequency"], m["owner"], m["source"], m["calculation"], m["where"],
                       "; ".join(m["inputs"]), "; ".join(m["depends"]), "; ".join(m["used_by"]), m["measure"],
                       m["classification"], m["public"], *ys, exv, exf, ext])

    # Fields
    f_rows = [["Table", "Table business name", "Column", "Business name", "What it holds", "Unit", "Kind of value", "Key",
               "Joins to", "Blank rows", "Distinct values", "Lowest", "Highest", "Example", "Used by metrics",
               "Source system", "Owner", "Classification"]]
    for t, cols in hdr.items():
        name, _, _, src, owner, _, cls = T.TABLES[t]
        rows = tables.get(t)
        for c in cols:
            bname, desc, unit = T.COLUMN_OVERRIDES.get((t, c)) or T.COLUMNS[c]
            if rows is not None:
                v = [r[c] for r in rows]
            else:  # telemetry: read one column at a time
                with (TABLES / f"{t}.csv").open(encoding="utf-8", newline="") as fh:
                    v = [r[c] for r in csv.DictReader(fh)]
            filled = [x for x in v if x != ""]
            kind = ("date" if filled and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) for x in filled[:2000]) else
                    "whole number" if filled and all(re.fullmatch(r"-?\d+", x) for x in filled[:2000]) else
                    "decimal" if filled and all(re.fullmatch(r"-?\d+(\.\d+)?", x) for x in filled[:2000]) else "text")
            lo = hi = ""
            if kind in ("whole number", "decimal"):
                nums = [float(x) for x in filled]
                lo, hi = (min(nums), max(nums)) if nums else ("", "")
                lo, hi = (int(lo), int(hi)) if kind == "whole number" and nums else (round(lo, 4), round(hi, 4))
            elif kind == "date" and filled:
                lo, hi = min(filled), max(filled)
            key = "PK" if c in pk.get(t, []) else ("FK" if c in keys and keys[c] != t else "")
            if t == "fact_asset_telemetry" and c == "date_key":
                key = "PK"
            joins = f"{keys[c]}.{'event_id' if keys[c] == 'fact_service_event' else pk[keys[c]][0]}" if key == "FK" else ""
            f_rows.append([t, name, c, bname, desc, unit, kind, key, joins, len(v) - len(filled), len(set(v)), lo, hi,
                           filled[0] if filled else "", "; ".join(used_by.get(f"{t}.{c}", [])), src, owner, cls])
    for path, about in T.RESULT_FILES.items():
        with (REPO / path).open(encoding="utf-8", newline="") as fh:
            rr = list(csv.DictReader(fh))
        for c in rr[0].keys():
            v = [r[c] for r in rr]
            filled = [x for x in v if x != ""]
            f_rows.append([path, about, c, c.replace("_", " ").capitalize(), T.RESULT_COLUMNS[c], "", "", "", "",
                           len(v) - len(filled), len(set(v)), "", "", filled[0] if filled else "", "",
                           "service-ai", "Data and AI Specialist", "Internal"])

    # Measures
    s_rows = [["Measure", "Folder", "What it shows", "Metric code", "Format", "DAX", "Measure guide"]]
    for x in sorted(ms, key=lambda x: (x["folder"], x["name"])):
        s_rows.append([x["name"], x["folder"], x["description"], T.MEASURE_METRIC.get(x["name"], ""), x["format"],
                       x["dax"], f"powerbi/docs/measure-guide.md#{anchor(x['name'])}"])

    # Tables
    t_rows = [["Table", "Business name", "Kind", "What it is", "What it is for", "One row is", "Rows", "Source system",
               "Owner", "How often", "Classification"]]
    for t in hdr:
        name, what, use, src, owner, often, cls = T.TABLES[t]
        kind = "Fact" if t.startswith("fact_") else "Bridge" if t.startswith("bridge_") else "Dimension"
        grain = T.GRAIN.get(t) or f"One {name.lower()}"
        n = len(tables[t]) if t in tables else sum(vals.pump_days.values())
        t_rows.append([t, name, kind, what, use, grain, n, src, owner, often, cls])

    r_rows = [["Kind", "Name", "What it checks or does", "Why", "Where it runs"], *[list(r) for r in T.RULES]]

    sheet_headers = {"Metrics": m_rows[0], "Fields": f_rows[0], "Measures": s_rows[0], "Tables": t_rows[0],
                     "Rules and tools": r_rows[0], **{t: hdr[t] for t in SMALL}}
    sheets = [read_me(len(T.METRICS), len(f_rows) - 1, len(ms)),
              table_sheet("Metrics", m_rows, [26, 20, 10, 32, 50, 45, 12, 16, 24, 14, 26, 26, 45, 30, 42, 32, 42, 32, 15, 16,
                                              14, 14, 14, 14, 12, 12], wrap=range(4, 20), zoom=80),
              table_sheet("Fields", f_rows, [26, 26, 22, 24, 55, 14, 13, 7, 26, 10, 10, 12, 12, 18, 30, 30, 26, 15],
                          wrap=(2, 5, 9, 15, 16, 17), zoom=80),
              table_sheet("Measures", s_rows, [42, 22, 60, 24, 14, 70, 50], wrap=(3, 6)),
              table_sheet("Tables", t_rows, [26, 28, 11, 55, 50, 42, 10, 34, 30, 24, 15], wrap=(2, 4, 5, 6, 8, 9, 10)),
              table_sheet("Rules and tools", r_rows, [14, 20, 60, 50, 38], wrap=(3, 4, 5)),
              table_sheet("Column reference", column_reference_rows(sheet_headers), [22, 26, 10, 96], wrap=(4,))]
    for t in SMALL:
        rows = [hdr[t]] + [[r[c] for c in hdr[t]] for r in tables[t]]
        sheets.append(table_sheet(t, rows, [max(12, min(40, len(c) + 4)) for c in hdr[t]], freeze="B2"))
    return sheets


def main(argv=None):
    p = argparse.ArgumentParser(description="Build Fjordvik's data dictionary workbook.")
    p.add_argument("--out", required=True, help="Path of the .xlsx file to write.")
    a = p.parse_args(argv)
    sheets = build()
    xlsx.write(a.out, sheets)
    print(f"Wrote {a.out}: " + ", ".join(f"{s['name']} ({len(s['rows']) - 1})" for s in sheets[:7]))


if __name__ == "__main__":
    main()
