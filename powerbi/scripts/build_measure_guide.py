"""Write docs/measure-guide.md: every DAX measure, what it is, what it does and how it is used.

The guide is generated from the model (TMDL) and both reports (PBIR), so it can't drift
from them; tests/test_docs.py fails if the committed copy is out of date. Each measure
gets:

- what it is: its description from the model;
- what it does: its DAX, the measures it builds on and the columns it reads;
- how it is used: an example value from the live model (docs/measure-examples.json),
  the report pages and visuals that show it, and the measures that use it.

Run:  python scripts/build_measure_guide.py
      python scripts/build_measure_guide.py --capture   (Power BI Desktop open and refreshed:
                                                          refresh the example values first)
"""

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "measure-guide.md"
EXAMPLES = REPO / "docs" / "measure-examples.json"
REPORTS = {"FjordvikEmissions": "Emissions report", "FjordvikPortfolio": "Portfolio report"}

_spec = importlib.util.spec_from_file_location("build_data_dictionary",
                                               REPO / "scripts" / "build_data_dictionary.py")
dictionary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dictionary)

FOLDER_ORDER = ["Emissions", "Time comparison", "Intensity", "Activity", "Market-based scope 2",
                "Value chain", "Sales", "Budget", "Price, volume and mix", "Bridge",
                "Portfolio balance", "Product sustainability", "Scorecard", "Data quality", "Text"]

FOLDER_INTRO = {
    "Emissions": "Totals of tonnes of carbon dioxide equivalent (tCO2e), location-based, from the five emission tables.",
    "Time comparison": "The same months a year earlier, and the change on them, like for like or including new sites.",
    "Intensity": "Emissions divided by what drives them: employees and revenue.",
    "Activity": "What the sites used, in the units they report (kWh, litres, kg, passenger-km, tonnes).",
    "Market-based scope 2": "Scope 2 worked out from the energy contracts and residual mixes, shown beside the location-based figure.",
    "Value chain": "Scope 3 categories 1, 3, 4 and 9: purchases, upstream energy and freight.",
    "Sales": "Units, net sales, cost, margin and price from the cleaned ERP sales, and the prior year.",
    "Budget": "Fjordvik's plan (fact_budget) and the variance of actuals on it.",
    "Price, volume and mix": "The ACCA sales variances that explain why margin moved against the prior year.",
    "Bridge": "The pieces that draw the margin waterfall: each step's value, its invisible base, and the labels.",
    "Portfolio balance": "Shares of sales and margin, and company averages for the scatter charts.",
    "Product sustainability": "Scope 3 category 11: the lifetime electricity of the pumps sold.",
    "Scorecard": "The quarterly review's weighted score, and its change.",
    "Data quality": "Checks that the figures reconcile, and the issues found in the ERP extract.",
    "Text": "Measures that return words: page titles, the lines under each card, the footer and labels.",
}

# Where each example is read, when a year alone does not give the measure a value.
EXAMPLE_CONTEXT = {
    "Bridge Value (EUR)": {"step": "Sales prices"},
    "Bridge Base (EUR)": {"step": "Mix"},
    "Bridge Increase (EUR)": {"step": "Delivery volumes"},
    "Bridge Decrease (EUR)": {"step": "Mix"},
    "Bridge Prior Year Total (EUR)": {"step": "Prior-year margin"},
    "Bridge This Year Total (EUR)": {"step": "This year's margin"},
    "Bridge Label Position (EUR)": {"step": "Sales prices"},
    "Weighted Score Prior Quarter": {"quarter": 4},
    "Weighted Score Change vs Prior Quarter": {"quarter": 4},
    "Scorecard Message": {"quarter": 4},
    "Contract Start": {"contract": "C02", "year": None},
    "Contract End": {"contract": "C02", "year": None},
    # Every product sold in both years of 2025 against 2024, so a whole year shows no
    # not-comparable change; June 2025 in the Baltics had a quarantined booster set line.
    "Not Comparable Change (EUR)": {"year": None, "month": 20250601, "region": "BAL",
                                    "family": "Pump packages and controls"},
    "Report Footer": {"year": None},
    "Open Issues Context": {"year": None},
    "Classification Message": {"year": None},
    "Data Issues": {"year": None},
    "Open Data Issues": {"year": None},
    "Quarantined Sales (EUR)": {"year": None},
    "Sales Reconciliation Difference (EUR)": {"year": None},
}
FILTERS = {"year": ("dim_date", "year", int), "quarter": ("dim_date", "quarter", int),
           "month": ("dim_date", "date_key", int), "region": ("dim_region", "region_id", str),
           "family": ("dim_product_group", "product_family", str),
           "step": ("dim_bridge_step", "step", str), "contract": ("dim_contract", "contract_id", str)}


def measures():
    table = dictionary.read_table(REPO / "FjordvikEmissions.SemanticModel" / "definition" / "tables" / "_Measures.tmdl")
    return table["measures"]


def context_of(name):
    ctx = {"year": 2025}
    ctx.update(EXAMPLE_CONTEXT.get(name, {}))
    return {k: v for k, v in ctx.items() if v is not None}


def describe_context(ctx):
    parts = []
    if "year" in ctx:
        parts.append(f"year {ctx['year']}")
    if "quarter" in ctx:
        parts.append(f"quarter {ctx['quarter']}")
    if "month" in ctx:
        parts.append(f"month {str(ctx['month'])[:4]}-{str(ctx['month'])[4:6]}")
    if "region" in ctx:
        parts.append(f"region {ctx['region']}")
    if "family" in ctx:
        parts.append(f"family {ctx['family']}")
    if "step" in ctx:
        parts.append(f"bridge step \"{ctx['step']}\"")
    if "contract" in ctx:
        parts.append(f"contract {ctx['contract']}")
    return ", ".join(parts) if parts else "all data, no filter"


def query(name, ctx):
    filters = []
    for key, value in ctx.items():
        table, column, kind = FILTERS[key]
        literal = f'"{value}"' if kind is str else str(value)
        filters.append(f"{table}[{column}] = {literal}")
    inner = f"[{name}]"
    if filters:
        inner = f"CALCULATE({inner}, {', '.join(filters)})"
    return f'EVALUATE ROW("value", {inner})'


def capture():
    """Ask the open model for every example value and save them (Desktop open, refreshed)."""
    items = [{"id": m["name"], "query": query(m["name"], context_of(m["name"])), "role": None}
             for m in measures()]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "queries.json"
        path.write_text(json.dumps(items), encoding="utf-8")
        out = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                              str(REPO / "scripts" / "run_dax.ps1"), "-QueryFile", str(path)],
                             capture_output=True, text=True, timeout=600)
    if out.returncode:
        sys.exit(out.stderr)
    results = {r["id"]: r for r in json.loads(out.stdout)}
    examples = {}
    for m in measures():
        r = results[m["name"]]
        if r["error"]:
            sys.exit(f"{m['name']}: {r['error']}")
        value = r["value"]
        if isinstance(value, float):
            value = round(value, 6)  # no binary noise (0.95000000001) in the stored file
        if m["name"] == "Report Footer" and isinstance(value, str):
            value = value.split(" Refreshed")[0] + " Refreshed (time of the last refresh)."
        examples[m["name"]] = {"context": describe_context(context_of(m["name"])), "value": value}
    EXAMPLES.write_text(json.dumps(examples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                        newline="\n")
    print(f"Captured {len(examples)} example values to {EXAMPLES}")


def show(value, fmt):
    """An example value written the way the measure's format string shows it."""
    if value is None:
        return "blank"
    if isinstance(value, str):
        return f'"{value}"'
    fmt = (fmt or "").split(";")[0]
    if "%" in fmt:
        decimals = len(fmt.split(".")[1].rstrip("%")) if "." in fmt else 0
        return f"{value:.{decimals}%}"
    decimals = len(re.sub(r"[^0]", "", fmt.split(".")[1])) if "." in fmt else 0
    sign = "+" if fmt.startswith("+") and value > 0 else ""
    return f"{sign}{value:,.{decimals}f}" if "," in fmt or "#" in fmt else f"{sign}{value:.{decimals}f}"


def visual_label(v):
    """A short name for a visual: its title, or for a card the label it shows."""
    vis = v["visual"]
    title = vis.get("visualContainerObjects", {}).get("title", [{}])[0].get("properties", {}).get("text")
    kind = {"card": "card", "multiRowCard": "text line", "tableEx": "table", "pivotTable": "matrix",
            "scatterChart": "scatter chart", "lineChart": "line chart", "slicer": "slicer",
            "waterfallChart": "waterfall", "lineStackedColumnComboChart": "waterfall"}.get(
        vis["visualType"], "chart")
    if title:
        return f"{kind} \"{title['expr']['Literal']['Value'].strip(chr(39)).replace(chr(39) * 2, chr(39))}\""
    if v["name"] == "message":
        return "page title sentence"
    if v["name"].startswith("footer"):
        return "footer"
    if v["name"].startswith("context") or v["name"].startswith("budget"):
        return "line under a card"
    labels = [p.get("displayName") for role in vis.get("query", {}).get("queryState", {}).values()
              for p in role["projections"] if p.get("displayName")]
    return f"{kind} \"{labels[0]}\"" if labels else kind


def measure_names_in(node):
    if isinstance(node, dict):
        if "Measure" in node and "Property" in node["Measure"]:
            yield node["Measure"]["Property"]
        for value in node.values():
            yield from measure_names_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from measure_names_in(value)


def report_usage():
    """measure -> sorted list of 'Report > Page: visual' lines."""
    usage = defaultdict(set)
    for folder, report in REPORTS.items():
        pages = REPO / f"{folder}.Report" / "definition" / "pages"
        order = json.loads((pages / "pages.json").read_text(encoding="utf-8"))["pageOrder"]
        for page_name in order:
            display = json.loads((pages / page_name / "page.json").read_text(encoding="utf-8"))["displayName"]
            for path in sorted((pages / page_name / "visuals").glob("*/visual.json")):
                v = json.loads(path.read_text(encoding="utf-8"))
                for name in set(measure_names_in(v)):
                    usage[name].add((report, order.index(page_name), display, visual_label(v)))
    return {name: [f"{r} > {d}: {label}" for r, _i, d, label in sorted(items)] for name, items in usage.items()}


def references(dax, names):
    """Measures a DAX expression calls ([Name] not after a table name) and columns it reads."""
    called = [n for n in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", dax) if n in names]
    columns = re.findall(r"\b([a-z_]+\[[a-z_0-9]+\])", dax)
    return list(dict.fromkeys(called)), list(dict.fromkeys(columns))


def anchor(name):
    """GitHub's heading anchor for a measure name."""
    return re.sub(r"[^\w\- ]", "", name.lower()).replace(" ", "-")


def main():
    all_measures = measures()
    names = {m["name"] for m in all_measures}
    examples = json.loads(EXAMPLES.read_text(encoding="utf-8")) if EXAMPLES.exists() else {}
    usage = report_usage()
    calls = {m["name"]: references(m["dax"], names) for m in all_measures}
    used_by = defaultdict(list)
    for name, (called, _cols) in calls.items():
        for c in called:
            used_by[c].append(name)
    by_folder = defaultdict(list)
    for m in all_measures:
        by_folder[m["displayFolder"]].append(m)
    folders = [f for f in FOLDER_ORDER if f in by_folder] + sorted(set(by_folder) - set(FOLDER_ORDER))

    lines = [
        "# Every DAX measure in the Fjordvik model",
        "",
        f"All {len(all_measures)} Data Analysis Expressions (DAX) measures in the Fjordvik semantic model "
        "(`FjordvikEmissions.SemanticModel`), grouped by display folder. For each: **what it is** (its "
        "description in the model), **what it does** (its DAX, the measures it builds on and the columns "
        "it reads), and **how it is used** (an example value from the model, where the reports show it, "
        "and which measures use it).",
        "",
        "Generated by `scripts/build_measure_guide.py` from the model and both reports; never edited by "
        "hand. Example values come from the model with Power BI Desktop open "
        "(`python scripts/build_measure_guide.py --capture`) and are for the year 2025 unless the example "
        "says otherwise. The column-by-column reference is the [data dictionary](data-dictionary.md).",
        "",
        "> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company. Emission factors are "
        "illustrative, not for real reporting.",
        "",
        "| Folder | Measures | What they cover |",
        "| --- | --- | --- |",
    ]
    for f in folders:
        lines.append(f"| [{f}](#{anchor(f)}) | {len(by_folder[f])} | {FOLDER_INTRO.get(f, '')} |")
    for f in folders:
        lines += ["", f"## {f}", "", FOLDER_INTRO.get(f, ""), ""]
        for m in by_folder[f]:
            name = m["name"]
            called, columns = calls[name]
            example = examples.get(name)
            lines += [f"### {name}", "", f"**What it is.** {m['description'] or 'No description.'}", "",
                      "**What it does.**", "", "```dax", m["dax"], "```", ""]
            facts = []
            if called:
                facts.append("Builds on " + ", ".join(f"[{c}](#{anchor(c)})" for c in called) + ".")
            if columns:
                facts.append("Reads " + ", ".join(f"`{c}`" for c in columns) + ".")
            if m.get("formatString"):
                facts.append(f"Format `{m['formatString']}`.")
            elif f == "Text":
                facts.append("Returns text.")
            if facts:
                lines += [" ".join(facts), ""]
            lines += ["**How it is used.**", ""]
            if example:
                lines.append(f"- Example ({example['context']}): {show(example['value'], m.get('formatString'))}")
            for where in usage.get(name, []):
                lines.append(f"- Shown in {where}")
            if used_by.get(name):
                lines.append("- Used by " + ", ".join(f"[{u}](#{anchor(u)})" for u in used_by[name]))
            if not usage.get(name) and not used_by.get(name):
                lines.append("- Not shown on a page or used by another measure: kept for analysts, the "
                             "Claude connector's checks and the live tests.")
            lines.append("")
    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUT} ({len(all_measures)} measures)")


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture()
    main()
