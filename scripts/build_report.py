"""Write the report pages (PBIR format) from one Python definition.

Power BI Desktop reads the report as a folder of JSON files: one page.json per
page and one visual.json per visual. Writing them by hand invites typos in
table and measure names, so the pages are defined here once and written out.
tests/test_model_files.py checks every field a visual uses exists in the model.

Run:  python scripts/build_report.py
"""

import json
import shutil
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "FjordvikEmissions.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VISUAL_SCHEMA = f"{SCHEMA}/visualContainer/2.12.0/schema.json"

CAVEAT = ("Synthetic data for a fictional company. Emission factors are illustrative, "
          "not for real reporting.")


# ---------------------------------------------------------------------------
# Field references
# ---------------------------------------------------------------------------

def measure(name):
    return ("_Measures", name, "Measure", None)


def column(table, name, label=None):
    return (table, name, "Column", label)


def projection(field, active=False):
    entity, prop, kind, label = field
    p = {"field": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if label:
        p["displayName"] = label  # header shown in the visual; the model name stays the same
    if active:
        p["active"] = True
    return p


def field_expr(field):
    entity, prop, kind, _label = field
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------

def container(name, x, y, w, h, z, visual):
    return {"$schema": VISUAL_SCHEMA, "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
            "visual": visual}


def card(name, x, y, w, h, z, m):
    return container(name, x, y, w, h, z, {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [projection(measure(m))]}}},
        "drillFilterOtherVisuals": True})


def chart(kind, name, x, y, w, h, z, category, values, series=None, sort_by_value=False):
    state = {"Category": {"projections": [projection(category, active=True)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if series:
        state["Series"] = {"projections": [projection(series)]}
    sort_field = values[0] if sort_by_value else category
    query = {"queryState": state,
             "sortDefinition": {"sort": [{"field": field_expr(sort_field),
                                          "direction": "Descending" if sort_by_value else "Ascending"}],
                                "isDefaultSort": True}}
    return container(name, x, y, w, h, z, {"visualType": kind, "query": query,
                                           "drillFilterOtherVisuals": True})


def table(name, x, y, w, h, z, fields):
    return container(name, x, y, w, h, z, {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": [projection(f) for f in fields]}}},
        "drillFilterOtherVisuals": True})


def slicer(name, x, y, w, h, z, field):
    return container(name, x, y, w, h, z, {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [projection(field, active=True)]}}},
        "objects": {"data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}]},
        "drillFilterOtherVisuals": True})


def textbox(name, x, y, w, h, z, lines):
    paragraphs = []
    for i, text in enumerate(lines):
        style = {"fontWeight": "bold", "fontSize": "16pt"} if i == 0 else {"fontSize": "10pt"}
        paragraphs.append({"textRuns": [{"value": text, "textStyle": style}]})
    return container(name, x, y, w, h, z, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "drillFilterOtherVisuals": True})


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

TOTAL = "Total Emissions (tCO2e)"
YEAR = column("dim_date", "year", "Year")
COUNTRY = column("dim_site", "country", "Country")
SITE = column("dim_site", "site_name", "Site")


def overview():
    cards = [TOTAL, "Scope 1 Emissions (tCO2e)", "Scope 2 Emissions (tCO2e)",
             "Scope 3 Emissions (tCO2e)", "Emissions per FTE (tCO2e)"]
    return [
        textbox("title", 20, 10, 820, 70, 0, ["Fjordvik Manufacturing Oy: emissions overview", CAVEAT]),
        slicer("slicer_year", 860, 10, 190, 70, 100, YEAR),
        slicer("slicer_country", 1070, 10, 190, 70, 200, COUNTRY),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 110, 300 + i, m) for i, m in enumerate(cards)],
        chart("lineChart", "line_total_by_month", 20, 220, 760, 480, 400,
              column("dim_date", "date", "Month"), [measure(TOTAL)]),
        chart("clusteredBarChart", "bar_total_by_site", 800, 220, 460, 480, 500,
              SITE, [measure(TOTAL)], sort_by_value=True),
    ]


def sites():
    return [
        textbox("title", 20, 10, 820, 70, 0, ["Sites: emissions and intensity", CAVEAT]),
        slicer("slicer_year", 860, 10, 190, 70, 100, YEAR),
        table("table_sites", 20, 95, 1240, 290, 200, [
            SITE, COUNTRY, column("dim_site", "site_type", "Site type"),
            measure(TOTAL), measure("Emissions per FTE (tCO2e)"),
            measure("Emissions per Million EUR (tCO2e)"),
            measure("Emissions Change vs Prior Year (%)")]),
        chart("lineChart", "line_scope2_by_site", 20, 400, 1240, 300, 300,
              column("dim_date", "date", "Month"), [measure("Scope 2 Emissions (tCO2e)")], series=SITE),
    ]


def data_quality():
    return [
        textbox("title", 20, 10, 1240, 70, 0, [
            "Data quality and reconciliation",
            "Stored tCO2e against activity times factor, row counts and reporting sites. " + CAVEAT]),
        card("card_difference", 20, 95, 300, 110, 100, "Reconciliation Difference (tCO2e)"),
        card("card_rows", 340, 95, 300, 110, 101, "Emission Rows"),
        card("card_sites", 660, 95, 300, 110, 102, "Sites Reporting"),
        table("table_by_year", 20, 220, 1240, 200, 200, [
            YEAR, measure("Emission Rows"), measure("Sites Reporting"), measure(TOTAL),
            measure("Recalculated Emissions (tCO2e)"), measure("Reconciliation Difference (tCO2e)")]),
    ]


PAGES = [("overview", "Overview", overview), ("sites", "Sites", sites),
         ("data_quality", "Data quality", data_quality)]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))  # UTF-8, no BOM


def main():
    definition = REPORT / "definition"
    if definition.exists():
        shutil.rmtree(definition)  # regenerated in full from this file
    write_json(definition / "version.json",
               {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    # Two report settings Power BI Desktop saved on 13 October 2026, kept so the
    # generated files and Desktop's saved files agree: Filters pane collapsed,
    # enhanced tooltips off.
    write_json(definition / "report.json",
               {"$schema": f"{SCHEMA}/report/3.3.0/schema.json", "themeCollection": {},
                "objects": {"outspacePane": [{"properties": {"expanded": {
                    "expr": {"Literal": {"Value": "false"}}}}}]},
                "settings": {"useEnhancedTooltips": False}})
    write_json(definition / "pages" / "pages.json",
               {"$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
                "pageOrder": [p[0] for p in PAGES], "activePageName": PAGES[0][0]})
    for name, display, build in PAGES:
        page = definition / "pages" / name
        write_json(page / "page.json",
                   {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": name,
                    "displayName": display, "displayOption": "FitToPage",
                    "height": 720, "width": 1280})
        for v in build():
            write_json(page / "visuals" / v["name"] / "visual.json", v)
    count = sum(1 for _ in definition.rglob("visual.json"))
    print(f"Wrote {len(PAGES)} pages and {count} visuals to {definition}")


if __name__ == "__main__":
    main()
