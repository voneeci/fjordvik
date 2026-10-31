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


def lit(value):
    """A PBIR literal: text in single quotes, numbers with a type suffix, true/false bare."""
    return {"expr": {"Literal": {"Value": value}}}


def fill(hex_colour):
    return {"solid": {"color": lit(f"'{hex_colour}'")}}


def for_measure(name):
    """Colour selector for one measure on a chart with several measures."""
    return {"metadata": f"_Measures.{name}"}


def for_value(field, value):
    """Colour selector for one category or legend value, such as country = 'Finland'."""
    entity, prop, kind, _label = field
    right = f"'{value}'" if isinstance(value, str) else f"{value}L"
    return {"data": [{"scopeId": {"Comparison": {
        "ComparisonKind": 0,
        "Left": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "Right": {"Literal": {"Value": right}}}}}]}


def style(visual, title=None, colours=None, labels=False, legend=False, extra=None):
    """The design pass: a title that says what the chart shows, fixed colours, and data
    labels or a legend where they help. colours is a list of (selector or None, hex)."""
    objects = dict(visual.get("objects", {}))
    if colours:
        objects["dataPoint"] = [({"properties": {"fill": fill(c)}, "selector": s} if s
                                 else {"properties": {"fill": fill(c)}}) for s, c in colours]
    if labels:
        objects["labels"] = [{"properties": {"show": lit("true")}}]
    if legend:
        objects["legend"] = [{"properties": {"show": lit("true"), "position": lit("'Top'")}}]
    objects.update(extra or {})
    if objects:
        visual["objects"] = objects
    if title:
        visual["visualContainerObjects"] = {"title": [{"properties": {
            "show": lit("true"), "text": lit("'" + title.replace("'", "''") + "'")}}]}
    return visual


def year_filter(year):
    """A visual-level filter fixing dim_date[year], for a chart that explains one year."""
    return {"filters": [{
        "name": f"year_{year}",
        "field": field_expr(YEAR),
        "type": "Categorical",
        "filter": {"Version": 2,
                   "From": [{"Name": "d", "Entity": "dim_date", "Type": 0}],
                   "Where": [{"Condition": {"In": {
                       "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}},
                                                   "Property": "year"}}],
                       "Values": [[{"Literal": {"Value": f"{year}L"}}]]}}}]}}]}


def chart(kind, name, x, y, w, h, z, category, values, series=None, sort_by_value=False,
          title=None, colours=None, labels=False, legend=False, filter_year=None, extra=None):
    state = {"Category": {"projections": [projection(category, active=True)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if series:
        state["Series"] = {"projections": [projection(series)]}
    sort_field = values[0] if sort_by_value else category
    query = {"queryState": state,
             "sortDefinition": {"sort": [{"field": field_expr(sort_field),
                                          "direction": "Descending" if sort_by_value else "Ascending"}],
                                "isDefaultSort": True}}
    visual = style({"visualType": kind, "query": query, "drillFilterOtherVisuals": True},
                   title, colours, labels, legend, extra)
    c = container(name, x, y, w, h, z, visual)
    if filter_year:
        c["filterConfig"] = year_filter(filter_year)
    return c


def table(name, x, y, w, h, z, fields, title=None):
    return container(name, x, y, w, h, z, style({
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": [projection(f) for f in fields]}}},
        "drillFilterOtherVisuals": True}, title))


def matrix(name, x, y, w, h, z, rows, columns, values, title=None):
    return container(name, x, y, w, h, z, style({
        "visualType": "pivotTable",
        "query": {"queryState": {
            "Rows": {"projections": [projection(f, active=True) for f in rows]},
            "Columns": {"projections": [projection(f, active=True) for f in columns]},
            "Values": {"projections": [projection(f) for f in values]}}},
        "drillFilterOtherVisuals": True}, title))


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


def section(name, x, y, w, h, z, heading, lines):
    """A text block with a heading, for the Introduction page."""
    paragraphs = [{"textRuns": [{"value": heading,
                                 "textStyle": {"fontWeight": "bold", "fontSize": "13pt"}}]}]
    paragraphs += [{"textRuns": [{"value": text, "textStyle": {"fontSize": "10pt"}}]}
                   for text in lines]
    return container(name, x, y, w, h, z, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "drillFilterOtherVisuals": True})


def page_navigator(name, x, y, w, h, z):
    """Power BI's built-in page navigator: one button per page, kept in step with the pages."""
    return container(name, x, y, w, h, z, {"visualType": "pageNavigator",
                                           "drillFilterOtherVisuals": True})


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

TOTAL = "Total Emissions (tCO2e)"
SCOPES = ["Scope 1 Emissions (tCO2e)", "Scope 2 Emissions (tCO2e)", "Scope 3 Emissions (tCO2e)"]
LFL = "Emissions Change vs Prior Year (%)"
CHANGE = "Emissions Change Including New Sites (tCO2e)"
CHANGE_PCT = "Emissions Change Including New Sites (%)"
YEAR = column("dim_date", "year", "Year")
MONTH = column("dim_date", "date", "Month")
COUNTRY = column("dim_site", "country", "Country")
SITE = column("dim_site", "site_name", "Site")
SCOPE = column("dim_source", "scope", "Scope")
SOURCE = column("dim_source", "source_name", "Source")

# Fixed colours, each set checked for colour-blind separation and contrast on white
# (31 October 2026). A colour follows its scope, country or site on every page.
ACCENT = "#1F6FA8"
SCOPE_COLOURS = {1: "#1F6FA8", 2: "#C77A1A", 3: "#7A5BA6"}
COUNTRY_COLOURS = {"Finland": "#2B7A3F", "Sweden": "#5B5FC7", "Estonia": "#C4502A"}
# Three of the six site colours are below 3:1 contrast on white, so every chart that
# uses them has a site table on the same page.
SITE_COLOURS = {"Tampere Plant": "#2A78D6", "Helsinki Head Office": "#EB6834",
                "Oulu Warehouse": "#1BAF7A", "Gothenburg Plant": "#EDA100",
                "Tallinn Plant": "#E87BA4", "Tartu Warehouse": "#008300"}
ENERGY = [("Natural Gas Used (kWh)", "#2A78D6"), ("Electricity Purchased (kWh)", "#EB6834"),
          ("District Heating Purchased (kWh)", "#1BAF7A")]
ACTIVITY_CARDS = ["Energy Used (kWh)", "Vehicle Fuel Used (litres)", "Refrigerant Leakage (kg)",
                  "Business Flights (passenger-km)", "Waste to Landfill (tonnes)"]


def header(title, note, slicers=(YEAR, COUNTRY)):
    """Page title with the synthetic-data caveat, and the page's slicers top right."""
    width = 1240 - 210 * len(slicers)
    out = [textbox("title", 20, 10, width, 70, 0, [title, f"{note} {CAVEAT}".strip()])]
    for i, field in enumerate(slicers):
        out.append(slicer(f"slicer_{field[1]}", 20 + width + 20 + i * 210, 10, 190, 70,
                          100 + i, field))
    return out


def single(colour=ACCENT):
    return [(None, colour)]


def introduction():
    return [
        textbox("title", 20, 10, 1240, 70, 0, [
            "Fjordvik Manufacturing Oy: monthly emissions report",
            "A portfolio project on synthetic data. " + CAVEAT]),
        page_navigator("page_buttons", 20, 90, 1240, 50, 100),
        section("about_company", 20, 155, 600, 175, 200, "About the company", [
            "Fjordvik Manufacturing Oy is a manufacturer with three plants, two warehouses and a "
            "head office in Finland, Sweden and Estonia.",
            "Each month every site reports the energy, fuel, refrigerant, business flights and "
            "waste it used. This report turns those figures into the company's greenhouse gas "
            "emissions, from January 2023 to December 2025.",
            "Tartu Warehouse opened in July 2024, and Tampere Plant installed rooftop solar panels "
            "the same month.",
        ]),
        table("table_sites", 20, 340, 600, 210, 300, [
            SITE, COUNTRY, column("dim_site", "site_type", "Site type")], title="The six sites"),
        section("owners", 20, 560, 600, 145, 400, "Who owns the figures", [
            "Business owner: Group Sustainability Manager, who signs off the figures.",
            "Technical owner: Data and AI Specialist, who maintains the model and this report.",
            "Country managers see only their own country's sites, through row-level security.",
        ]),
        section("page_guide", 640, 155, 620, 250, 500, "What each page answers", [
            "Overview: how much does Fjordvik emit, and where?",
            "Emissions breakdown: what are the emissions made of, by scope, source and country?",
            "Intensity and growth: is Fjordvik getting cleaner as it grows?",
            "Energy and activity: how much energy, fuel and other activity did each site use?",
            "What changed: why did emissions move on the prior year?",
            "Sites: how do the six sites compare?",
            "Data quality: do the figures reconcile, and is every site reporting?",
        ]),
        section("reading_guide", 640, 415, 620, 290, 600, "How to read the figures", [
            "Scope 1: direct emissions from fuel burned on site and refrigerant leaks. Scope 2: "
            "electricity and heat bought, using each country's average factor (location-based). "
            "Scope 3: business flights and waste to landfill.",
            "tCO2e is tonnes of carbon dioxide equivalent: activity amount times emission factor, "
            "divided by 1,000.",
            "Intensity divides emissions by average full-time equivalent employees (FTE) or by "
            "revenue in millions of euros, so a growing business can see whether it is getting "
            "cleaner as well as bigger.",
            "Like-for-like change compares only site-months reported in both years, so a new "
            "site does not inflate growth. The What changed page shows both views.",
            "Most pages have Year or Country slicers at the top right: pick a value to filter "
            "that page.",
        ]),
    ]


def overview():
    cards = [TOTAL, *SCOPES, "Emissions per FTE (tCO2e)"]
    return [
        *header("Fjordvik Manufacturing Oy: emissions overview", ""),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 110, 300 + i, m) for i, m in enumerate(cards)],
        chart("lineChart", "line_total_by_month", 20, 220, 760, 480, 400, MONTH, [measure(TOTAL)],
              title="Total emissions by month (tCO2e)", colours=single()),
        chart("clusteredBarChart", "bar_total_by_site", 800, 220, 460, 480, 500,
              SITE, [measure(TOTAL)], sort_by_value=True, title="Emissions by site (tCO2e)",
              colours=single(), labels=True),
    ]


def breakdown():
    return [
        *header("Emissions breakdown", "What the emissions are made of: scope, source and country."),
        chart("columnChart", "column_scope_by_month", 20, 95, 760, 300, 300, MONTH,
              [measure(m) for m in SCOPES], title="Emissions by scope and month (tCO2e)",
              colours=[(for_measure(m), SCOPE_COLOURS[i + 1]) for i, m in enumerate(SCOPES)],
              legend=True),
        chart("donutChart", "donut_scope_share", 800, 95, 460, 300, 400, SCOPE, [measure(TOTAL)],
              sort_by_value=True, title="Share of emissions by scope",
              colours=[(for_value(SCOPE, s), c) for s, c in SCOPE_COLOURS.items()],
              labels=True, legend=True),
        chart("clusteredBarChart", "bar_by_source", 20, 410, 620, 300, 500, SOURCE,
              [measure(TOTAL)], sort_by_value=True, title="Emissions by source (tCO2e)",
              colours=single(), labels=True),
        chart("clusteredColumnChart", "column_by_country", 660, 410, 600, 300, 600, COUNTRY,
              [measure(TOTAL)], sort_by_value=True, title="Emissions by country (tCO2e)",
              colours=[(for_value(COUNTRY, k), c) for k, c in COUNTRY_COLOURS.items()],
              labels=True),
    ]


def intensity():
    return [
        *header("Intensity and growth",
                "Is Fjordvik getting cleaner as it grows? Emissions per employee and per million euros."),
        chart("lineChart", "line_per_fte_by_month", 20, 95, 620, 290, 300, MONTH,
              [measure("Emissions per FTE (tCO2e)")], title="Emissions per FTE by month (tCO2e)",
              colours=single()),
        chart("lineChart", "line_per_meur_by_month", 660, 95, 600, 290, 400, MONTH,
              [measure("Emissions per Million EUR (tCO2e)")],
              title="Emissions per million euros of revenue by month (tCO2e)", colours=single()),
        chart("clusteredColumnChart", "column_revenue_by_month", 20, 400, 400, 300, 500, MONTH,
              [measure("Revenue (EUR)")], title="Revenue by month (EUR)",
              colours=single("#7A5BA6")),
        chart("lineChart", "line_fte_by_month", 440, 400, 400, 300, 600, MONTH,
              [measure("Average FTE")], title="Headcount by month (FTE)", colours=single("#7A5BA6")),
        chart("clusteredBarChart", "bar_lfl_change_by_site", 860, 400, 400, 300, 700, SITE,
              [measure(LFL)], sort_by_value=True,
              title="Like-for-like change on the prior year, by site (%)", colours=single(),
              labels=True),
    ]


def energy():
    return [
        *header("Energy and activity",
                "What the sites used, in their own units. Tampere's rooftop solar panels cut its "
                "bought electricity from July 2024."),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 100, 300 + i, m)
          for i, m in enumerate(ACTIVITY_CARDS)],
        chart("columnChart", "column_energy_by_month", 20, 210, 620, 260, 400, MONTH,
              [measure(m) for m, _c in ENERGY], title="Energy used by month (kWh)",
              colours=[(for_measure(m), c) for m, c in ENERGY], legend=True),
        chart("lineChart", "line_electricity_by_site", 660, 210, 600, 260, 500, MONTH,
              [measure("Electricity Purchased (kWh)")], series=SITE,
              title="Electricity bought by site and month (kWh)",
              colours=[(for_value(SITE, s), c) for s, c in SITE_COLOURS.items()], legend=True),
        table("table_activity_by_site", 20, 485, 1240, 220, 600, [
            SITE, COUNTRY, *[measure(m) for m in ACTIVITY_CARDS],
            *[measure(m) for m, _c in ENERGY]], title="Activity by site, in the sites' own units"),
    ]


def changed():
    return [
        *header("What changed on the prior year",
                "Like for like compares only site-months reported in both years. Including new "
                "sites counts Tartu Warehouse's first year (opened July 2024) as an increase.",
                slicers=(COUNTRY,)),
        chart("clusteredColumnChart", "column_change_pct_by_year", 20, 95, 400, 300, 300, YEAR,
              [measure(LFL), measure(CHANGE_PCT)],
              title="Change on the prior year: like for like and including new sites (%)",
              colours=[(for_measure(LFL), ACCENT), (for_measure(CHANGE_PCT), "#C77A1A")],
              labels=True, legend=True),
        chart("waterfallChart", "waterfall_2025_by_site", 440, 95, 820, 300, 400, SITE,
              [measure(CHANGE)], sort_by_value=True, filter_year=2025,
              title="What moved 2025 emissions: change by site against 2024 (tCO2e)", labels=True,
              extra={"sentimentColors": [{"properties": {
                  "increaseFill": fill("#C4502A"), "decreaseFill": fill("#2B7A3F"),
                  "totalFill": fill(ACCENT)}}]}),
        chart("clusteredBarChart", "bar_change_by_site_and_year", 20, 410, 620, 300, 500, SITE,
              [measure(CHANGE)], series=YEAR, title="Change on the prior year by site (tCO2e)",
              colours=[(for_value(YEAR, 2024), "#7A5BA6"), (for_value(YEAR, 2025), ACCENT)],
              legend=True),
        matrix("matrix_change_by_site_year", 660, 410, 600, 300, 600, [SITE], [YEAR],
               [measure(CHANGE), measure(LFL)], title="Change by site and year"),
    ]


def sites():
    return [
        *header("Sites: emissions and intensity", "", slicers=(YEAR,)),
        table("table_sites", 20, 95, 1240, 290, 200, [
            SITE, COUNTRY, column("dim_site", "site_type", "Site type"),
            measure(TOTAL), measure("Emissions per FTE (tCO2e)"),
            measure("Emissions per Million EUR (tCO2e)"), measure(LFL)],
            title="Emissions and intensity by site"),
        chart("lineChart", "line_scope2_by_site", 20, 400, 1240, 300, 300, MONTH,
              [measure("Scope 2 Emissions (tCO2e)")], series=SITE,
              title="Scope 2 emissions by site and month (tCO2e)",
              colours=[(for_value(SITE, s), c) for s, c in SITE_COLOURS.items()], legend=True),
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
            measure("Recalculated Emissions (tCO2e)"), measure("Reconciliation Difference (tCO2e)")],
            title="Reconciliation by year"),
    ]


PAGES = [("introduction", "Introduction", introduction), ("overview", "Overview", overview),
         ("breakdown", "Emissions breakdown", breakdown),
         ("intensity", "Intensity and growth", intensity), ("energy", "Energy and activity", energy),
         ("changed", "What changed", changed), ("sites", "Sites", sites),
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
