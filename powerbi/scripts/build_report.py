"""Write the two report folders (PBIR format) from one Python definition.

Power BI Desktop reads a report as a folder of JSON files: one page.json per
page and one visual.json per visual. Writing them by hand invites typos in
table and measure names, so the pages are defined here once and written out.
tests/test_model_files.py checks every field a visual uses exists in the model.

Two reports read the one semantic model (FjordvikEmissions.SemanticModel): an
emissions report for the sustainability team and a portfolio report for the
portfolio team (Reece's choice, 31 October 2026, after Jasila's review).

Run:  python scripts/build_report.py
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_FOLDER = "FjordvikEmissions.SemanticModel"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VISUAL_SCHEMA = f"{SCHEMA}/visualContainer/2.12.0/schema.json"
THEME = "Fjordvik.json"

CAVEAT = ("Synthetic data for a fictional company. Emission factors are illustrative, "
          "not for real reporting.")
OWNER = "Owner: Data and AI Specialist. Source: the governed dataset (data/tables)."

# The latest full year in the data: every Year slicer opens on it (Jasila's review,
# rank 1: with "All", cards add three years and prior-year comparisons break).
LATEST_YEAR = 2025
LATEST_QUARTER = 4


# ---------------------------------------------------------------------------
# Field references
# ---------------------------------------------------------------------------

def measure(name):
    return ("_Measures", name, "Measure", None)


def labelled(name, label):
    """A measure shown under a shorter heading, for tables and legends with little room."""
    return ("_Measures", name, "Measure", label)


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


def lit(value):
    """A PBIR literal: text in single quotes, numbers with a type suffix, true/false bare."""
    return {"expr": {"Literal": {"Value": value}}}


def text(value):
    return lit("'" + value.replace("'", "''") + "'")


def fill(hex_colour):
    return {"solid": {"color": lit(f"'{hex_colour}'")}}


def for_measure(name):
    """Selector for one measure on a chart with several measures."""
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
            "show": lit("true"), "text": text(title)}}]}
    return visual


# More room for long category names on bar charts (share of the chart, default 25).
WIDE_NAMES = {"categoryAxis": [{"properties": {"maxMarginFactor": lit("45L")}}]}


def label_units(units, precision=1):
    """Data labels in thousands (1000) or millions (1000000), so small bars do not read 0.0M."""
    return {"labels": [{"properties": {"show": lit("true"), "labelDisplayUnits": lit(f"{units}D"),
                                       "labelPrecision": lit(f"{precision}L")}}]}


LABELS_K = label_units(1000, 0)


def chart(kind, name, x, y, w, h, z, category, values, series=None, sort_by_value=False,
          title=None, colours=None, labels=False, legend=False, extra=None, sort_field=None):
    state = {"Category": {"projections": [projection(category, active=True)]},
             "Y": {"projections": [projection(v) for v in values]}}
    if series:
        state["Series"] = {"projections": [projection(series)]}
    sort_on = sort_field or (values[0] if sort_by_value else category)
    query = {"queryState": state,
             "sortDefinition": {"sort": [{"field": field_expr(sort_on),
                                          "direction": "Descending" if sort_by_value else "Ascending"}],
                                "isDefaultSort": True}}
    visual = style({"visualType": kind, "query": query, "drillFilterOtherVisuals": True},
                   title, colours, labels, legend, extra)
    return container(name, x, y, w, h, z, visual)


def scatter(name, x, y, w, h, z, details, x_field, y_field, size=None, title=None, colour=None):
    """One bubble per item: two measures against each other, size for a third."""
    state = {"Category": {"projections": [projection(details, active=True)]},
             "X": {"projections": [projection(x_field)]},
             "Y": {"projections": [projection(y_field)]}}
    if size:
        state["Size"] = {"projections": [projection(size)]}
    extra = {"categoryLabels": [{"properties": {"show": lit("true")}}]}
    return container(name, x, y, w, h, z, style(
        {"visualType": "scatterChart", "query": {"queryState": state}, "drillFilterOtherVisuals": True},
        title, [(None, colour or ACCENT)], extra=extra))


def table(name, x, y, w, h, z, fields, title=None, widths=None, wrap=False, sort=None, totals=True,
          compact=False):
    """widths: {field: pixels}; wrap: long text wraps instead of widening the table;
    compact: 9-point text (12 px), so ten rows and a total fit."""
    objects = {} if totals else {"total": [{"properties": {"totals": lit("false")}}]}
    if compact:
        objects["grid"] = [{"properties": {"textSize": lit("9D")}}]
    if widths:
        objects["columnWidth"] = [
            {"properties": {"value": lit(f"{px}D")}, "selector": {"metadata": f"{f[0]}.{f[1]}"}}
            for f, px in widths.items()]
    if wrap:
        objects["values"] = [{"properties": {"wordWrap": lit("true")}}]
    query = {"queryState": {"Values": {"projections": [projection(f) for f in fields]}}}
    if sort:
        field, direction = sort
        query["sortDefinition"] = {"sort": [{"field": field_expr(field), "direction": direction}],
                                   "isDefaultSort": True}
    visual = {"visualType": "tableEx", "query": query, "drillFilterOtherVisuals": True}
    if objects:
        visual["objects"] = objects
    return container(name, x, y, w, h, z, style(visual, title))


def shade(m, low="#FFFFFF", high="#7FA7CB"):
    """Cell background from white to a light blue by value; the numbers stay as the second cue."""
    return [{"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
        "Input": field_expr(measure(m)),
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
            "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                     "metadata": f"_Measures.{m}"}}]


def matrix(name, x, y, w, h, z, rows, columns, values, title=None, totals=True, shading=None,
           compact=False):
    """totals=False hides subtotals and grand totals, where a 'Total' would mislead (an average
    of scores, or two years of change pooled)."""
    objects = {"grid": [{"properties": {"textSize": lit("9D")}}]} if compact else {}
    if not totals:
        objects["subTotals"] = [{"properties": {"rowSubtotals": lit("false"),
                                                "columnSubtotals": lit("false")}}]
    if shading:
        objects["values"] = shade(shading)
    visual = {"visualType": "pivotTable",
              "query": {"queryState": {
                  "Rows": {"projections": [projection(f, active=True) for f in rows]},
                  "Columns": {"projections": [projection(f, active=True) for f in columns]},
                  "Values": {"projections": [projection(f) for f in values]}}},
              "drillFilterOtherVisuals": True}
    if objects:
        visual["objects"] = objects
    return container(name, x, y, w, h, z, style(visual, title))


def in_filter(field, value):
    entity, prop, _kind, _label = field
    literal = f"{value}L" if isinstance(value, int) else f"'{value}'"
    return {"Version": 2, "From": [{"Name": "d", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "d"}},
                                            "Property": prop}}],
                "Values": [[{"Literal": {"Value": literal}}]]}}}]}


def slicer(name, x, y, w, h, z, field, default=None):
    """A drop-down slicer. With a default it is single-select and opens on that value."""
    objects = {"data": [{"properties": {"mode": lit("'Dropdown'")}}]}
    if default is not None:
        objects["selection"] = [{"properties": {"singleSelect": lit("true"),
                                                "strictSingleSelect": lit("true")}}]
        objects["general"] = [{"properties": {"filter": {"filter": in_filter(field, default)}}}]
    return container(name, x, y, w, h, z, {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [projection(field, active=True)]}}},
        "objects": objects,
        "drillFilterOtherVisuals": True})


def textbox(name, x, y, w, h, z, lines, size="10pt", first_bold=False, first_size=None):
    paragraphs = []
    for i, line in enumerate(lines):
        text_style = {"fontSize": size}
        if i == 0 and first_bold:
            text_style = {"fontWeight": "bold", "fontSize": first_size or size}
        paragraphs.append({"textRuns": [{"value": line, "textStyle": text_style}]})
    return container(name, x, y, w, h, z, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "drillFilterOtherVisuals": True})


def section(name, x, y, w, h, z, heading, lines):
    """A text block with a heading, for the Introduction pages."""
    paragraphs = [{"textRuns": [{"value": heading,
                                 "textStyle": {"fontWeight": "bold", "fontSize": "13pt"}}]}]
    paragraphs += [{"textRuns": [{"value": line, "textStyle": {"fontSize": "10pt"}}]}
                   for line in lines]
    return container(name, x, y, w, h, z, {
        "visualType": "textbox",
        "objects": {"general": [{"properties": {"paragraphs": paragraphs}}]},
        "drillFilterOtherVisuals": True})


def kpi(name, x, y, w, h, z, m, label=None, units=None):
    """A headline number. units: 1000 or 1000000, so every card on a page uses one style."""
    entity, prop, kind, _ = measure(m)
    objects = {"labels": [{"properties": {"fontSize": lit("20D")}}]}
    if units:
        objects["labels"][0]["properties"].update({"labelDisplayUnits": lit(f"{units}D"),
                                                   "labelPrecision": lit("2L" if units == 1 else "1L")})
    visual = {"visualType": "card",
              "query": {"queryState": {"Values": {"projections": [projection((entity, prop, kind, label))]}}},
              "drillFilterOtherVisuals": True}
    if objects:
        visual["objects"] = objects
    return container(name, x, y, w, h, z, visual)


def words(name, x, y, w, h, z, m, size=10, colour="#3B3A39", bold=False):
    """A line of text from a text measure (card context, page message, footer), left-aligned
    in a multi-row card with no label and no accent bar."""
    entity, prop, kind, _ = measure(m)
    return container(name, x, y, w, h, z, {
        "visualType": "multiRowCard",
        "query": {"queryState": {"Values": {"projections": [projection((entity, prop, kind, None))]}}},
        "objects": {
            "cardTitle": [{"properties": {"fontSize": lit(f"{size}D"), "color": fill(colour),
                                          **({"fontFamily": text("Segoe UI Semibold")} if bold else {})}}],
            "dataLabels": [{"properties": {"fontSize": lit(f"{size}D"), "color": fill(colour)}}],
            "categoryLabels": [{"properties": {"show": lit("false")}}],
            "card": [{"properties": {"barShow": lit("false"), "outlineStyle": lit("0D")}}]},
        "drillFilterOtherVisuals": True})


def context_line(name, x, y, w, h, z, m):
    """The comparison under a card, centred like the card's number."""
    entity, prop, kind, _ = measure(m)
    return container(name, x, y, w, h, z, {
        "visualType": "card",
        "query": {"queryState": {"Values": {"projections": [projection((entity, prop, kind, None))]}}},
        "objects": {"labels": [{"properties": {"fontSize": lit("10D"), "color": fill("#3B3A39")}}],
                    "categoryLabels": [{"properties": {"show": lit("false")}}]},
        "drillFilterOtherVisuals": True})


def page_navigator(name, x, y, w, h, z):
    """Power BI's built-in page navigator: one button per page, kept in step with the pages."""
    return container(name, x, y, w, h, z, {
        "visualType": "pageNavigator",
        "objects": {"text": [{"properties": {"fontSize": lit("8D")}, "selector": {"id": "default"}}]},
        "drillFilterOtherVisuals": True})


# ---------------------------------------------------------------------------
# Fields, colours and the page frame
# ---------------------------------------------------------------------------

TOTAL = "Total Emissions (tCO2e)"
SCOPES = ["Scope 1 Emissions (tCO2e)", "Scope 2 Emissions (tCO2e)", "Scope 3 Emissions (tCO2e)"]
LFL = "Emissions Change vs Prior Year (%)"
CHANGE = "Emissions Change Including New Sites (tCO2e)"
CHANGE_PCT = "Emissions Change Including New Sites (%)"
OPERATIONAL = "Operational Emissions (tCO2e)"
YEAR = column("dim_date", "year", "Year")
MONTH = column("dim_date", "date", "Month")
QUARTER = column("dim_date", "quarter", "Quarter")
COUNTRY = column("dim_site", "country", "Country")
SITE = column("dim_site", "site_name", "Site")
SCOPE = column("dim_source", "scope", "Scope")
SOURCE = column("dim_source", "source_name", "Source")
CATEGORY = column("dim_scope3_category", "category_name", "Scope 3 category")
FAMILY = column("dim_product_group", "product_family", "Family")
GROUP = column("dim_product_group", "product_group", "Product group")
REGION = column("dim_region", "region_name", "Region")
PRODUCT = column("dim_product", "product_name", "Product")
STEP = column("dim_bridge_step", "step", "Step")

# One colour system (Jasila's review, rank 5): each set means one thing everywhere.
# Scopes, countries and sites keep their colours; families, energy carriers and
# effects have their own; previous periods are grey, actuals dark; a variance is
# green or red and always carries a sign as the second cue.
ACCENT = "#1F6FA8"
PREVIOUS = "#A6A6A6"
INCREASE, DECREASE = "#2B7A3F", "#B4232A"
SCOPE_COLOURS = {1: "#1F6FA8", 2: "#C77A1A", 3: "#7A5BA6"}
COUNTRY_COLOURS = {"Finland": "#2B7A3F", "Sweden": "#5B5FC7", "Estonia": "#C4502A"}
SITE_COLOURS = {"Tampere Plant": "#2A78D6", "Helsinki Head Office": "#EB6834",
                "Oulu Warehouse": "#1BAF7A", "Gothenburg Plant": "#EDA100",
                "Tallinn Plant": "#E87BA4", "Tartu Warehouse": "#008300"}
ENERGY = [("Natural Gas Used (kWh)", "#2F4B7C"), ("Electricity Purchased (kWh)", "#B5651D"),
          ("District Heating Purchased (kWh)", "#3D8C8C")]
FAMILY_COLOURS = {"Industrial process pumps": "#264E70", "Water and wastewater pumps": "#4A8C9E",
                  "Pump packages and controls": "#8C6D46", "Spare parts and service": "#6E6E6E"}
MARKET = "Scope 2 Market-based Emissions (tCO2e)"
LOCATION_COLOUR, MARKET_COLOUR = "#C77A1A", "#8A5A0B"
FREIGHT = [("Upstream Transport Emissions (tCO2e)", "#7A5BA6"),
           ("Downstream Transport Emissions (tCO2e)", "#3F2D63")]
ACTIVITY_CARDS = [("Energy Used (kWh)", "Energy Used Context", 1000000),
                  ("Vehicle Fuel Used (litres)", "Vehicle Fuel Context", 1000),
                  ("Refrigerant Leakage (kg)", "Refrigerant Context", None),
                  ("Business Flights (passenger-km)", "Business Flights Context", 1000000),
                  ("Waste to Landfill (tonnes)", "Waste Context", None)]

TOP, CONTENT, FOOTER = 4, 104, 694


def frame(title, message, slicers=(), defaults=None):
    """Every page: page buttons along the top, the page name and its message (a sentence
    worked out from the data), slicers top right, and a footer with the caveat, owner and
    the data's period and refresh time (Jasila's review, ranks 6 and 9)."""
    defaults = defaults or {}
    width = 1240 - 160 * len(slicers)
    out = [page_navigator("page_buttons", 20, TOP, 1240, 30, 0),
           textbox("title", 20, 38, width, 26, 1, [title], size="12pt", first_bold=True),
           words("message", 20, 62, width, 36, 2, message, size=13, colour="#252423", bold=True),
           textbox("footer_note", 20, FOOTER, 820, 24, 900, [f"{CAVEAT} {OWNER}"], size="8pt"),
           words("footer_data", 850, FOOTER, 410, 24, 901, "Report Footer", size=8)]
    for i, field in enumerate(slicers):
        out.append(slicer(f"slicer_{field[1]}", 20 + width + 20 + i * 160, 38, 140, 58,
                          100 + i, field, defaults.get(field[1])))
    return out


YEAR_ONLY = {"year": LATEST_YEAR}


def cards(specs, y=CONTENT, x0=20, total_width=1240, budget=False):
    """A row of headline cards, each with its comparison line under it (rank 3).
    specs: (measure, label, context measure, display units, budget context measure or None)."""
    gap = 20
    w = (total_width - gap * (len(specs) - 1)) // len(specs)
    out = []
    for i, (m, label, ctx, units, plan) in enumerate(specs):
        x = x0 + i * (w + gap)
        out.append(kpi(f"card_{i}", x, y, w, 64, 300 + i, m, label, units))
        if ctx:
            out.append(context_line(f"context_{i}", x, y + 62, w, 26, 320 + i, ctx))
        if plan:
            out.append(context_line(f"budget_{i}", x, y + 86, w, 26, 340 + i, plan))
    return out


def single(colour=ACCENT):
    return [(None, colour)]


# ---------------------------------------------------------------------------
# Emissions report
# ---------------------------------------------------------------------------

def emissions_introduction():
    return [
        page_navigator("page_buttons", 20, TOP, 1240, 30, 0),
        textbox("title", 20, 40, 1240, 60, 1, [
            "Fjordvik Manufacturing Oy: emissions report",
            "A portfolio project. Product portfolio pages are in the Fjordvik portfolio report "
            "(FjordvikPortfolio.pbip), on the same model."], first_bold=True, first_size="16pt"),
        section("about_company", 20, 110, 600, 190, 200, "About the company", [
            "Fjordvik Manufacturing Oy makes electric pumps and pump systems for water utilities, "
            "industry and buildings: process pumps in Tampere, water and wastewater pumps in "
            "Gothenburg, pump packages and controls in Tallinn, with warehouses in Oulu and Tartu "
            "and a head office in Helsinki.",
            "Each month the sites report the energy, fuel, refrigerant, flights and waste they "
            "used; purchasing, logistics, energy contracts and the ERP sales extract add the value "
            "chain, January 2023 to December 2025.",
            "Tartu Warehouse opened in July 2024, and Tampere Plant installed rooftop solar panels "
            "the same month.",
        ]),
        table("table_sites", 20, 310, 600, 200, 300, [
            SITE, COUNTRY, column("dim_site", "site_type", "Site type")], title="The six sites"),
        section("owners", 20, 520, 600, 160, 400, "Who owns the figures", [
            "Business owner: Group Sustainability Manager, who signs off the figures.",
            "Technical owner: Data and AI Specialist, who maintains the model and this report.",
            "Country managers see only their own country's sites, through row-level security.",
        ]),
        section("page_guide", 640, 110, 620, 250, 500, "What each page answers", [
            "Overview: how much Fjordvik emits and where. Emissions breakdown: by scope, source "
            "and country. Value chain: the 15 scope 3 categories. Scope 2 methods: location-based "
            "beside market-based.",
            "Intensity and growth: is Fjordvik getting cleaner as it grows? Energy and activity: "
            "what the sites used. What changed: the change on the prior year. Sites: each site's "
            "figures. Data quality: do the stored figures reconcile?",
            "Each page title is a sentence worked out from the data, so it never goes stale.",
        ]),
        section("reading_guide", 640, 370, 620, 310, 600, "How to read the figures", [
            "Each page opens on the latest full year (2025). Pick another year in the Year slicer; "
            "charts by month or year always show all three years.",
            "Under each headline number: the same months a year earlier and the change on them.",
            "Scope 1: fuel burned on site and refrigerant leaks. Scope 2: electricity and heat "
            "bought, at each country's average factor (location-based); market-based is shown "
            "beside it. Scope 3: purchases, upstream fuel and grid losses, freight, flights, "
            "landfill waste and the lifetime electricity of the pumps sold. Totals are "
            "location-based.",
            "tCO2e is tonnes of carbon dioxide equivalent. K means thousands, M millions.",
            "Like-for-like change compares only site-months reported in both years, so a new "
            "site does not inflate growth.",
        ]),
        textbox("footer_note", 20, FOOTER, 820, 24, 900, [f"{CAVEAT} {OWNER}"], size="8pt"),
        words("footer_data", 850, FOOTER, 410, 24, 901, "Report Footer", size=8),
    ]


def overview():
    return [
        *frame("Emissions overview", "Overview Message", (YEAR, COUNTRY), YEAR_ONLY),
        *cards([(TOTAL, "Total emissions (tCO2e)", "Total Emissions Context", 1000, None),
                (SCOPES[0], "Scope 1 (tCO2e)", "Scope 1 Emissions Context", 1000, None),
                (SCOPES[1], "Scope 2 (tCO2e)", "Scope 2 Emissions Context", 1000, None),
                (SCOPES[2], "Scope 3 (tCO2e)", "Scope 3 Emissions Context", 1000, None),
                ("Emissions per FTE (tCO2e)", "Per FTE (tCO2e)", "Emissions per FTE Context", None, None)]),
        chart("lineChart", "line_total_by_month", 20, 200, 760, 484, 400, MONTH, [measure(TOTAL)],
              title="Total emissions by month, all three years (tCO2e)", colours=single()),
        chart("clusteredBarChart", "bar_total_by_site", 800, 200, 460, 236, 500,
              SITE, [measure(TOTAL)], sort_by_value=True,
              title="Emissions by site, including use of the products each plant made (tCO2e)",
              colours=single(), extra={**LABELS_K, **WIDE_NAMES}),
        chart("clusteredBarChart", "bar_operational_by_site", 800, 448, 460, 236, 600,
              SITE, [measure(OPERATIONAL)], sort_by_value=True,
              title="Operational emissions by site: scopes 1 and 2 (tCO2e)",
              colours=single(), extra={**label_units(1000, 1), **WIDE_NAMES}),
    ]


def breakdown():
    scope12 = SCOPES[:2]
    return [
        *frame("Emissions breakdown", "Breakdown Message", (YEAR, SCOPE), YEAR_ONLY),
        # Tall enough for all 13 sources, so it never scrolls.
        chart("clusteredBarChart", "bar_by_source", 20, CONTENT, 420, 580, 300, SOURCE,
              [measure(TOTAL)], sort_by_value=True, title="Emissions by source (tCO2e)",
              colours=single(), extra={**label_units(1000, 1), **WIDE_NAMES}),
        chart("clusteredBarChart", "bar_by_scope", 460, CONTENT, 380, 190, 400, SCOPE,
              [measure(TOTAL)], sort_by_value=True, title="Emissions by scope (tCO2e)",
              colours=[(for_value(SCOPE, s), c) for s, c in SCOPE_COLOURS.items()], extra=LABELS_K),
        chart("clusteredBarChart", "bar_by_country", 860, CONTENT, 400, 190, 500, COUNTRY,
              [measure(TOTAL)], sort_by_value=True, title="Emissions by country (tCO2e)",
              colours=[(for_value(COUNTRY, k), c) for k, c in COUNTRY_COLOURS.items()], extra=LABELS_K),
        chart("columnChart", "column_scope_by_month", 460, 304, 800, 186, 600, MONTH,
              [measure(m) for m in SCOPES], title="All scopes by month, all three years (tCO2e)",
              colours=[(for_measure(m), SCOPE_COLOURS[i + 1]) for i, m in enumerate(SCOPES)],
              legend=True),
        chart("columnChart", "column_scope12_by_month", 460, 498, 800, 186, 700, MONTH,
              [measure(m) for m in scope12],
              title="Scopes 1 and 2 by month, on their own scale (tCO2e)",
              colours=[(for_measure(m), SCOPE_COLOURS[i + 1]) for i, m in enumerate(scope12)],
              legend=True),
    ]


def value_chain():
    reason = column("dim_scope3_category", "reason", "What it covers, or why not")
    number = column("dim_scope3_category", "scope3_category", "No.")
    status = column("dim_scope3_category", "status", "Status")
    return [
        *frame("Value chain (scope 3)", "Value Chain Message", (YEAR, COUNTRY), YEAR_ONLY),
        *cards([("Scope 3 Emissions (tCO2e)", "Scope 3 (tCO2e)", "Scope 3 Emissions Context", 1000, None),
                ("Purchased Goods and Services Emissions (tCO2e)", "Purchased goods (tCO2e)",
                 "Purchased Goods Context", 1000, None),
                ("Fuel and Energy Related Emissions (tCO2e)", "Fuel and energy (tCO2e)",
                 "Fuel and Energy Context", 1000, None),
                ("Upstream Transport Emissions (tCO2e)", "Freight, category 4 (tCO2e)",
                 "Upstream Transport Context", 1000, None),
                ("Downstream Transport Emissions (tCO2e)", "Freight, category 9 (tCO2e)",
                 "Downstream Transport Context", 1000, None)]),
        # Scope 3 measure, not the total: scope 1 and 2 sources have no category.
        chart("clusteredBarChart", "bar_by_scope3_category", 20, 200, 520, 230, 400, CATEGORY,
              [measure("Scope 3 Emissions (tCO2e)")], sort_by_value=True,
              title="Scope 3 emissions by category (tCO2e)",
              colours=single(SCOPE_COLOURS[3]), extra={**LABELS_K, **WIDE_NAMES}),
        chart("clusteredBarChart", "bar_purchases_by_spend_category", 556, 200, 340, 230, 500,
              column("fact_purchases", "spend_category", "Spend category"),
              [measure("Purchased Goods and Services Emissions (tCO2e)")], sort_by_value=True,
              title="Purchased goods by spend category (tCO2e)",
              colours=single(SCOPE_COLOURS[3]), extra={**LABELS_K, **WIDE_NAMES}),
        chart("clusteredBarChart", "bar_freight_by_mode", 912, 200, 348, 230, 600,
              column("fact_freight", "mode", "Mode"),
              [labelled(m, label) for (m, _c), label in zip(FREIGHT, ["Category 4", "Category 9"])],
              title="Freight by mode and payer (tCO2e)",
              colours=[(for_measure(m), c) for m, c in FREIGHT], legend=True, extra=label_units(1000, 1)),
        table("table_scope3_categories", 20, 440, 1240, 244, 700,
              [number, CATEGORY, status, reason],
              title="All 15 scope 3 categories (the Greenhouse Gas Protocol requires a reason for "
                    "each one left out)",
              widths={number: 40, CATEGORY: 250, status: 140, reason: 760}, wrap=True),
    ]


def scope2_methods():
    methods = [labelled("Scope 2 Emissions (tCO2e)", "Location-based"), labelled(MARKET, "Market-based")]
    colours = [(for_measure("Scope 2 Emissions (tCO2e)"), LOCATION_COLOUR), (for_measure(MARKET), MARKET_COLOUR)]
    return [
        *frame("Scope 2: location-based and market-based", "Scope 2 Message", (YEAR, COUNTRY), YEAR_ONLY),
        *cards([("Scope 2 Emissions (tCO2e)", "Location-based (tCO2e)", "Scope 2 Emissions Context", 1000, None),
                (MARKET, "Market-based (tCO2e)", "Scope 2 Market-based Context", 1000, None),
                ("Scope 2 Market minus Location (tCO2e)", "Market minus location (tCO2e)", None, 1000, None),
                ("Electricity with Guarantees of Origin (%)", "Covered by guarantees (%)",
                 "Guarantees of Origin Context", None, None)]),
        chart("clusteredColumnChart", "column_methods_by_year", 20, 200, 620, 250, 400, YEAR,
              methods, title="Scope 2 by method, all three years (tCO2e)", colours=colours,
              legend=True, extra=label_units(1000, 1)),
        chart("clusteredBarChart", "bar_methods_by_site", 660, 200, 600, 250, 500, SITE,
              methods, title="Scope 2 by method and site (tCO2e)", colours=colours, legend=True,
              extra={**label_units(1000, 1), **WIDE_NAMES}),
        table("table_contracts", 20, 462, 700, 222, 600, [
            column("dim_contract", "site_id", "Site"),
            column("dim_contract", "supplier_name", "Supplier"),
            column("dim_contract", "instrument", "Instrument"),
            column("dim_contract", "covered_share", "Share covered"),
            labelled("Contract Start", "From"), labelled("Contract End", "To")],
            title="Electricity contracts with guarantees of origin", totals=False,
            widths={column("dim_contract", "site_id"): 45, column("dim_contract", "supplier_name"): 215,
                    column("dim_contract", "instrument"): 185, column("dim_contract", "covered_share"): 100,
                    labelled("Contract Start", ""): 75, labelled("Contract End", ""): 75}),
        matrix("matrix_market_by_instrument", 740, 462, 520, 222, 700,
               [column("fact_scope2_market", "instrument", "Instrument")], [YEAR],
               [measure(MARKET)], title="Market-based scope 2 by instrument, all three years (tCO2e)"),
    ]


def intensity():
    return [
        *frame("Intensity and growth", "Intensity Message", (YEAR, COUNTRY), YEAR_ONLY),
        *cards([("Emissions per FTE (tCO2e)", "Per FTE, all scopes (tCO2e)", "Emissions per FTE Context", None, None),
                ("Emissions per Million EUR (tCO2e)", "Per million EUR of revenue (tCO2e)",
                 "Emissions per Million EUR Context", None, None),
                ("Operational Emissions per FTE (tCO2e)", "Per FTE, scopes 1 and 2 (tCO2e)",
                 "Operational Emissions per FTE Context", None, None)]),
        chart("lineChart", "line_per_meur_by_month", 20, 200, 620, 240, 300, MONTH,
              [measure("Emissions per Million EUR (tCO2e)")],
              title="Emissions per million euros of revenue by month, all three years (tCO2e)",
              colours=single()),
        chart("lineChart", "line_per_fte_by_month", 660, 200, 600, 240, 400, MONTH,
              [measure("Emissions per FTE (tCO2e)")],
              title="Emissions per FTE by month, all three years (tCO2e)", colours=single()),
        chart("clusteredColumnChart", "column_revenue_by_month", 20, 450, 400, 234, 500, MONTH,
              [measure("Revenue (EUR)")], title="Revenue by month (EUR)", colours=single()),
        chart("lineChart", "line_fte_by_month", 440, 450, 400, 234, 600, MONTH,
              [measure("Average FTE")], title="Headcount by month (FTE)", colours=single()),
        chart("clusteredBarChart", "bar_lfl_change_by_site", 860, 450, 400, 234, 700, SITE,
              [measure(LFL)], sort_by_value=True,
              title="Like-for-like change on the prior year, by site (%)", colours=single(),
              labels=True, extra=WIDE_NAMES),
    ]


def energy():
    others = {s: PREVIOUS for s in SITE_COLOURS}
    others["Tampere Plant"] = ACCENT
    return [
        *frame("Energy and activity", "Energy Message", (YEAR, COUNTRY), YEAR_ONLY),
        *cards([(m, None, ctx, units, None) for m, ctx, units in ACTIVITY_CARDS]),
        chart("columnChart", "column_energy_by_month", 20, 200, 620, 250, 400, MONTH,
              [measure(m) for m, _c in ENERGY], title="Energy used by month, all three years (kWh)",
              colours=[(for_measure(m), c) for m, c in ENERGY], legend=True),
        chart("lineChart", "line_electricity_by_site", 660, 200, 600, 250, 500, MONTH,
              [measure("Electricity Purchased (kWh)")], series=SITE,
              title="Electricity bought by site and month: Tampere (solar from July 2024) in blue (kWh)",
              colours=[(for_value(SITE, s), c) for s, c in others.items()], legend=True),
        table("table_activity_by_site", 20, 462, 1240, 222, 600, [
            SITE, COUNTRY,
            *[labelled(m, label) for (m, _c, _u), label in zip(ACTIVITY_CARDS, [
                "Energy (kWh)", "Vehicle fuel (litres)", "Refrigerant (kg)", "Flights (passenger-km)",
                "Landfill (tonnes)"])],
            *[labelled(m, label) for (m, _c), label in zip(ENERGY, [
                "Gas (kWh)", "Electricity (kWh)", "Heat (kWh)"])]],
            title="Activity by site, in the sites' own units"),
    ]


def changed():
    return [
        *frame("What changed on the prior year", "What Changed Message", (YEAR, COUNTRY), YEAR_ONLY),
        chart("clusteredColumnChart", "column_change_pct_by_year", 20, CONTENT, 400, 290, 300, YEAR,
              [labelled(LFL, "Like for like"), labelled(CHANGE_PCT, "Including new sites")],
              title="Change on the prior year, each year (%)",
              colours=[(for_measure(LFL), ACCENT), (for_measure(CHANGE_PCT), PREVIOUS)],
              labels=True, legend=True),
        chart("waterfallChart", "waterfall_by_site", 440, CONTENT, 820, 290, 400, SITE,
              [measure(CHANGE)], sort_by_value=True,
              title="What moved emissions: change by site on the prior year (tCO2e)",
              extra={**label_units(1000, 1), "sentimentColors": [{"properties": {
                  "increaseFill": fill(DECREASE), "decreaseFill": fill(INCREASE),
                  "totalFill": fill(ACCENT)}}]}),
        chart("clusteredBarChart", "bar_change_by_site_and_year", 20, 404, 620, 280, 500, SITE,
              [measure(CHANGE)], series=YEAR, title="Change on the prior year by site, 2024 and 2025 (tCO2e)",
              colours=[(for_value(YEAR, 2024), PREVIOUS), (for_value(YEAR, 2025), ACCENT)],
              legend=True, extra=WIDE_NAMES),
        # One measure and no total column: a "Total" here would be two years of change pooled.
        matrix("matrix_change_by_site_year", 660, 404, 600, 280, 600, [SITE], [YEAR],
               [measure(LFL)], title="Like-for-like change by site, each year (%)", totals=False),
    ]


def sites():
    return [
        *frame("Sites", "Sites Message", (YEAR,), YEAR_ONLY),
        table("table_sites", 20, CONTENT, 1240, 270, 200, [
            SITE, COUNTRY, column("dim_site", "site_type", "Site type"),
            labelled(TOTAL, "Total (tCO2e)"), labelled(OPERATIONAL, "Scopes 1, 2 (tCO2e)"),
            labelled("Emissions per FTE (tCO2e)", "Per FTE, all (tCO2e)"),
            labelled("Operational Emissions per FTE (tCO2e)", "Per FTE, scopes 1, 2 (tCO2e)"),
            labelled("Emissions per Million EUR (tCO2e)", "Per EUR million (tCO2e)"),
            labelled(LFL, "Change (%)")],
            title="Emissions and intensity by site: 'all' includes use of the products a plant made"),
        chart("clusteredBarChart", "bar_operational_by_site_year", 20, 386, 1240, 298, 300, SITE,
              [measure(OPERATIONAL)], series=YEAR,
              title="Operational emissions (scopes 1 and 2) by site, all three years (tCO2e)",
              colours=[(for_value(YEAR, 2023), "#D0D0D0"), (for_value(YEAR, 2024), PREVIOUS),
                       (for_value(YEAR, 2025), ACCENT)],
              legend=True, extra={**label_units(1000, 1), **WIDE_NAMES}),
    ]


def data_quality():
    return [
        *frame("Data quality and reconciliation", "Data Quality Message", (YEAR,), YEAR_ONLY),
        *cards([("Reconciliation Difference (tCO2e)", "Stored minus recalculated (tCO2e)", None, None, None),
                ("Emission Rows", "Site emission rows", None, None, None),
                ("Sites Reporting", "Sites reporting", None, None, None),
                ("Market-based Reconciliation Difference (tCO2e)", "Market-based check (tCO2e)", None, None, None)]),
        table("table_by_year", 20, 180, 1240, 160, 200, [
            YEAR, measure("Emission Rows"), measure("Sites Reporting"), measure(TOTAL),
            measure("Recalculated Emissions (tCO2e)"), measure("Reconciliation Difference (tCO2e)")],
            title="Reconciliation, all three years"),
        matrix("matrix_rows_by_site_year", 20, 352, 1240, 332, 300, [SITE], [YEAR],
               [measure("Emission Rows")], title="Site emission rows by site and year: every "
               "site reports every source each month from its first month", totals=False),
    ]


# ---------------------------------------------------------------------------
# Portfolio report
# ---------------------------------------------------------------------------

def portfolio_introduction():
    return [
        page_navigator("page_buttons", 20, TOP, 1240, 30, 0),
        textbox("title", 20, 40, 1240, 60, 1, [
            "Fjordvik Manufacturing Oy: product portfolio report",
            "A portfolio project. Emission pages are in the Fjordvik emissions report "
            "(FjordvikEmissions.pbip), on the same model."], first_bold=True, first_size="16pt"),
        section("about_portfolio", 20, 110, 600, 230, 200, "The portfolio", [
            "Three plants make three pump families: industrial process pumps (Tampere), water and "
            "wastewater pumps (Gothenburg), pump packages and controls (Tallinn). Oulu and Tartu "
            "ship spare parts and service kits. 4 families, 10 product groups, 24 models, sold in "
            "four regions.",
            "Sales come from the ERP extract (simulated), cleaned and reconciled to finance by SQL "
            "before the report reads them. The budget is Fjordvik's own plan by month, site, "
            "product group and region.",
        ]),
        section("owners", 20, 350, 600, 330, 400, "Who owns the figures", [
            "Business owner: Head of Portfolio, who chairs the quarterly portfolio review.",
            "Data owners: regional controllers for sales, the Group Financial Controller for the "
            "budget, portfolio governance for the product classification.",
            "Technical owner: Data and AI Specialist, who maintains the model and this report.",
            "Sales region managers see only their own region's sales and budget, through "
            "row-level security.",
        ]),
        section("page_guide", 640, 110, 620, 250, 500, "What each page answers", [
            "Portfolio overview: what sells and earns, against last year and budget. Price, volume "
            "and mix: why margin moved. Portfolio balance: where sales and margin come from, and "
            "which groups grow. Quarterly scorecard: how the review rates each group, beside its "
            "figures. Product sustainability: the lifetime emissions of the pumps sold. "
            "Classification and data quality: what the ERP data got wrong.",
            "Each page title is a sentence worked out from the data, so it never goes stale.",
        ]),
        section("reading_guide", 640, 370, 620, 310, 600, "How to read the figures", [
            "Each page opens on the latest full year (2025); the scorecard on its latest quarter. "
            "Charts by month or quarter always show all three years.",
            "Under each headline number: the same months a year earlier and the change, then the "
            "budget and the variance on it. A rate (margin %) moves in percentage points (pts).",
            "The margin bridge follows the ACCA sales variances with the prior year as standard: "
            "sales prices, mix, delivery volumes (quantity) and variable costs (cost per unit). "
            "Products sold in only one of the two years are shown apart as not comparable.",
            "K means thousands, M millions.",
        ]),
        textbox("footer_note", 20, FOOTER, 820, 24, 900, [f"{CAVEAT} {OWNER}"], size="8pt"),
        words("footer_data", 850, FOOTER, 410, 24, 901, "Report Footer", size=8),
    ]


SALES_CARDS = [("Net Sales (EUR)", "Net sales (EUR)", "Net Sales Context", 1000000, "Net Sales Budget Context"),
               ("Margin (EUR)", "Margin (EUR)", "Margin Context", 1000000, "Margin Budget Context"),
               ("Margin (%)", "Margin (%)", "Margin Percent Context", None, "Margin Percent Budget Context"),
               ("Units Sold", "Units sold", "Units Sold Context", 1000, "Units Sold Budget Context")]


def portfolio_overview():
    return [
        *frame("Portfolio overview", "Portfolio Overview Message", (YEAR, REGION), YEAR_ONLY),
        *cards(SALES_CARDS),
        chart("lineChart", "line_sales_by_month", 20, 224, 780, 190, 400, MONTH,
              [measure("Net Sales (EUR)")], series=FAMILY,
              title="Net sales by month and family, all three years (EUR)",
              colours=[(for_value(FAMILY, f), c) for f, c in FAMILY_COLOURS.items()], legend=True),
        chart("clusteredBarChart", "bar_sales_vs_budget_by_family", 820, 224, 440, 190, 500, FAMILY,
              [labelled("Net Sales vs Budget (%)", "Against budget")], sort_by_value=True,
              title="Net sales against budget by family (%)",
              colours=[(None, ACCENT)], labels=True, extra=WIDE_NAMES),
        table("table_by_group", 20, 420, 1240, 268, 600, [
            FAMILY, GROUP, labelled("Net Sales Prior Year (EUR)", "Net sales, prior year"),
            labelled("Net Sales (EUR)", "Net sales"), labelled("Sales Growth vs Prior Year (%)", "Growth"),
            labelled("Budget Net Sales (EUR)", "Budget"), labelled("Net Sales vs Budget (%)", "Against budget"),
            labelled("Margin (EUR)", "Margin"), labelled("Margin (%)", "Margin %"),
            labelled("Margin vs Budget (EUR)", "Margin against budget")],
            title="Sales and margin by family and product group: prior year, this year, budget",
            compact=True),
    ]


# Fills light enough for dark labels (4.3:1 or more) and dark enough to see on white (3:1).
BRIDGE = [("Bridge Base (EUR)", "#FFFFFF"), ("Bridge Prior Year Total (EUR)", PREVIOUS),
          ("Bridge Increase (EUR)", "#4C9A50"), ("Bridge Decrease (EUR)", "#D0555B"),
          ("Bridge This Year Total (EUR)", "#5B8DB8")]


def price_volume_mix():
    hide_base = [{"properties": {"show": lit("false")}, "selector": for_measure("Bridge Base (EUR)")}]
    return [
        *frame("Price, volume and mix", "Price Volume Mix Message", (YEAR, FAMILY), YEAR_ONLY),
        *cards([("Margin Prior Year (EUR)", "Prior-year margin (EUR)", None, 1000000, None),
                ("Margin (EUR)", "Margin (EUR)", None, 1000000, None),
                ("Margin Change vs Prior Year (EUR)", "Change (EUR)", "Margin Change Context", 1000000, None),
                ("Margin vs Budget (EUR)", "Against budget (EUR)", "Margin Budget Context", 1000000, None)]),
        # A waterfall drawn as stacked columns: an invisible base lifts each step to where the
        # running total stands, so the bars run from prior-year margin to this year's margin.
        chart("columnChart", "waterfall_margin", 20, 198, 700, 194, 400, STEP,
              [measure(m) for m, _c in BRIDGE],
              title="Margin bridge: prior year to this year (EUR)",
              colours=[(for_measure(m), c) for m, c in BRIDGE], sort_field=column("dim_bridge_step", "step_order"),
              extra={"labels": [{"properties": {"show": lit("true"), "labelDisplayUnits": lit("1000000D"),
                                                "labelPrecision": lit("1L"), "labelOverflow": lit("true"),
                                                "color": fill(TEXT_DARK)}}] + hide_base,
                     "legend": [{"properties": {"show": lit("false")}}]}),
        table("table_effects_by_family", 740, 198, 520, 194, 500, [
            FAMILY, labelled("Price Effect (EUR)", "Prices"),
            labelled("Mix Effect by Group (EUR)", "Mix"),
            labelled("Quantity Effect by Group (EUR)", "Volumes"),
            labelled("Cost Effect (EUR)", "Costs"),
            labelled("Margin Change vs Prior Year (EUR)", "Change")],
            title="Bridge by family (EUR)", sort=(measure("Margin Change vs Prior Year (EUR)"), "Descending"),
            compact=True, widths={FAMILY: 165, labelled("Price Effect (EUR)", ""): 66,
                                  labelled("Mix Effect by Group (EUR)", ""): 62,
                                  labelled("Quantity Effect by Group (EUR)", ""): 66,
                                  labelled("Cost Effect (EUR)", ""): 70,
                                  labelled("Margin Change vs Prior Year (EUR)", ""): 72}),
        table("table_effects_by_group", 20, 398, 1240, 266, 600, [
            GROUP, labelled("Margin Prior Year (EUR)", "Prior-year margin"),
            labelled("Price Effect (EUR)", "Sales prices"), labelled("Mix Effect by Group (EUR)", "Mix"),
            labelled("Quantity Effect by Group (EUR)", "Delivery volumes"),
            labelled("Cost Effect (EUR)", "Variable costs"),
            labelled("Not Comparable Change (EUR)", "Not comparable"), labelled("Margin (EUR)", "Margin")],
            title="Bridge by product group (EUR): each row and each column adds up",
            sort=(measure("Margin Change vs Prior Year (EUR)"), "Descending"), compact=True),
        words("note_between_groups", 20, 664, 1240, 26, 700, "Mix Between Groups Note", size=9),
    ]


def portfolio_balance():
    return [
        *frame("Portfolio balance", "Portfolio Balance Message", (YEAR,), YEAR_ONLY),
        chart("clusteredBarChart", "bar_share_sales_margin_by_group", 20, CONTENT, 560, 580, 300, GROUP,
              [labelled("Share of Net Sales (%)", "Share of net sales"),
               labelled("Share of Margin (%)", "Share of margin")], sort_by_value=True,
              title="Share of net sales and of margin by product group (%)",
              colours=[(for_measure("Share of Net Sales (%)"), PREVIOUS),
                       (for_measure("Share of Margin (%)"), ACCENT)],
              labels=True, legend=True, extra=WIDE_NAMES),
        scatter("scatter_growth_margin", 600, CONTENT, 660, 330, 400, GROUP,
                labelled("Sales Growth vs Prior Year (%)", "Sales growth on the prior year"),
                labelled("Margin (%)", "Margin"), size=measure("Net Sales (EUR)"),
                title="Growth against margin by product group (bubble size: net sales)"),
        matrix("matrix_share_family_region", 600, 444, 660, 240, 500, [FAMILY], [REGION],
               [measure("Share of Net Sales (%)")], title="Share of net sales by family and region (%)",
               shading="Share of Net Sales (%)"),
    ]


def scorecard():
    return [
        *frame("Quarterly portfolio scorecard", "Scorecard Message", (YEAR, QUARTER, FAMILY),
               {"year": LATEST_YEAR, "quarter": LATEST_QUARTER}),
        matrix("matrix_score_by_quarter", 20, CONTENT, 760, 270, 300, [GROUP], [YEAR, QUARTER],
               [measure("Weighted Score")], title="Weighted score by product group, every quarter",
               totals=False, shading="Weighted Score", compact=True),
        table("table_score_and_kpis", 20, 384, 760, 300, 500, [
            GROUP, labelled("Weighted Score", "Score"),
            labelled("Weighted Score Change vs Prior Quarter", "Change"),
            labelled("Net Sales (EUR)", "Net sales"), labelled("Margin (%)", "Margin"),
            labelled("Share of Net Sales (%)", "Share"), labelled("Price Effect (EUR)", "Prices effect"),
            labelled("Use-phase Emissions per Unit (tCO2e)", "tCO2e per unit")],
            title="Score beside the figures, for the selected quarter", sort=(measure("Weighted Score"), "Descending"),
            compact=True),
        table("table_criteria", 800, CONTENT, 460, 190, 400, [
            column("dim_score_criterion", "criterion_name", "Criterion"),
            column("dim_score_criterion", "weight", "Weight (of 100)")],
            title="Criteria (Cooper and Edgett) and Fjordvik's weights",
            sort=(column("dim_score_criterion", "weight"), "Descending")),
        scatter("scatter_score_margin", 800, 304, 460, 380, 600, GROUP,
                labelled("Weighted Score", "Score"), labelled("Margin (%)", "Margin"),
                title="Score against margin: a high score with a weak margin stands out"),
    ]


def product_sustainability():
    return [
        *frame("Product sustainability", "Product Sustainability Message", (YEAR, REGION), YEAR_ONLY),
        *cards([("Use-phase Emissions (tCO2e)", "Use-phase emissions (tCO2e)", "Use-phase Emissions Context", 1000, None),
                ("Use-phase Emissions per Unit (tCO2e)", "Per unit sold (tCO2e)", "Use-phase per Unit Context", None, None),
                ("Use-phase Emissions per Thousand EUR (tCO2e)", "Per EUR 1,000 of net sales (tCO2e)",
                 "Use-phase per Thousand EUR Context", None, None)]),
        chart("clusteredBarChart", "bar_per_unit_by_group", 20, 200, 400, 264, 400, GROUP,
              [measure("Use-phase Emissions per Unit (tCO2e)")], sort_by_value=True,
              title="Per unit sold, by product group (tCO2e)",
              colours=single(SCOPE_COLOURS[3]), labels=True, extra=WIDE_NAMES),
        scatter("scatter_margin_emissions", 440, 200, 420, 264, 500, GROUP,
                labelled("Margin (%)", "Margin"),
                labelled("Use-phase Emissions per Thousand EUR (tCO2e)", "Use-phase per EUR 1,000"),
                title="Margin against tCO2e per EUR 1,000 of sales",
                colour=SCOPE_COLOURS[3]),
        chart("clusteredBarChart", "bar_use_phase_by_region", 880, 200, 380, 264, 600, REGION,
              [measure("Use-phase Emissions (tCO2e)")], sort_by_value=True,
              title="By region of use; Rest of world not calculated (tCO2e)",
              colours=single(SCOPE_COLOURS[3]), extra={**label_units(1000, 1), **WIDE_NAMES}),
        table("table_products", 20, 474, 1240, 210, 700, [
            PRODUCT, column("dim_product", "kwh_per_year", "kWh a year"),
            column("dim_product", "lifetime_years", "Lifetime (years)"),
            measure("Units Sold"), labelled("Use-phase Emissions per Unit (tCO2e)", "Per unit (tCO2e)"),
            labelled("Use-phase Emissions per Thousand EUR (tCO2e)", "Per EUR 1,000 of net sales (tCO2e)")],
            title="Each product: specification and use-phase emissions"),
    ]


def classification():
    return [
        *frame("Classification and data quality", "Classification Message"),
        *cards([("Open Data Issues", "Open issues", "Open Issues Context", None, None),
                ("Quarantined Sales (EUR)", "Sales held back (EUR)", None, 1, None),
                ("Sales Reconciliation Difference (EUR)", "Sales minus finance revenue (EUR)", None, None, None)]),
        table("table_issues", 20, 200, 1240, 240, 200, [
            column("fact_data_issue", "status", "Status"), column("dim_date", "date", "Month"), SITE,
            column("fact_data_issue", "issue_type", "Issue"),
            column("fact_data_issue", "detail", "Detail"),
            column("fact_data_issue", "line_count", "Lines"),
            column("fact_data_issue", "amount_eur", "Amount (EUR)"),
            column("fact_data_issue", "action", "Action for the data owner")],
            title="Issues found in the extract (quarantined lines are open until mapped)",
            sort=(column("fact_data_issue", "status"), "Descending"), wrap=True,
            widths={column("fact_data_issue", "status"): 110, column("dim_date", "date"): 75,
                    SITE: 115, column("fact_data_issue", "issue_type"): 150,
                    column("fact_data_issue", "detail"): 400, column("fact_data_issue", "line_count"): 45,
                    column("fact_data_issue", "amount_eur"): 95, column("fact_data_issue", "action"): 220}),
        table("table_codes", 20, 450, 1240, 234, 300, [
            column("dim_product_code", "business_unit", "Business unit"),
            column("dim_product_code", "local_item_number", "Local item number"),
            column("dim_product", "product_id", "Global product"), PRODUCT, FAMILY],
            title="The global product classification: local item numbers by business unit"),
    ]


EMISSIONS_PAGES = [
    ("introduction", "Introduction", emissions_introduction), ("overview", "Overview", overview),
    ("breakdown", "Emissions breakdown", breakdown), ("value_chain", "Value chain (scope 3)", value_chain),
    ("scope2_methods", "Scope 2 methods", scope2_methods), ("intensity", "Intensity and growth", intensity),
    ("energy", "Energy and activity", energy), ("changed", "What changed", changed),
    ("sites", "Sites", sites), ("data_quality", "Data quality", data_quality)]

PORTFOLIO_PAGES = [
    ("introduction", "Introduction", portfolio_introduction),
    ("portfolio_overview", "Portfolio overview", portfolio_overview),
    ("price_volume_mix", "Price, volume and mix", price_volume_mix),
    ("portfolio_balance", "Portfolio balance", portfolio_balance),
    ("scorecard", "Quarterly scorecard", scorecard),
    ("product_sustainability", "Product sustainability", product_sustainability),
    ("classification", "Classification and data quality", classification)]

REPORTS = {"FjordvikEmissions": EMISSIONS_PAGES, "FjordvikPortfolio": PORTFOLIO_PAGES}


# ---------------------------------------------------------------------------
# Theme, interactions and files
# ---------------------------------------------------------------------------

TEXT_DARK, TEXT_MID = "#252423", "#3B3A39"   # 15.9:1 and 11.0:1 on white

# Jasila measured titles at about 1.5:1 and labels at about 2.4:1 against white with
# Power BI's defaults; every text class here is 4.5:1 or more, at 10 points (13 px) or more.
THEME_JSON = {
    "name": "Fjordvik",
    "dataColors": [ACCENT, "#C77A1A", "#7A5BA6", "#2B7A3F", "#5B5FC7", "#C4502A", "#264E70",
                   "#4A8C9E", "#8C6D46", PREVIOUS],
    "background": "#FFFFFF", "foreground": TEXT_DARK, "tableAccent": ACCENT,
    "good": INCREASE, "bad": DECREASE, "neutral": PREVIOUS,
    "textClasses": {
        "callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": TEXT_DARK},
        "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": TEXT_DARK},
        "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": TEXT_DARK},
        "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": TEXT_MID}},
    "visualStyles": {"*": {"*": {
        "title": [{"fontColor": {"solid": {"color": TEXT_DARK}}, "fontSize": 11}],
        "categoryAxis": [{"labelColor": {"solid": {"color": TEXT_MID}}, "fontSize": 10,
                          "titleColor": {"solid": {"color": TEXT_MID}}}],
        "valueAxis": [{"labelColor": {"solid": {"color": TEXT_MID}}, "fontSize": 10,
                       "titleColor": {"solid": {"color": TEXT_MID}}}],
        "legend": [{"labelColor": {"solid": {"color": TEXT_MID}}, "fontSize": 10}],
        "labels": [{"color": {"solid": {"color": TEXT_DARK}}, "fontSize": 10}],
        "categoryLabels": [{"color": {"solid": {"color": TEXT_MID}}, "fontSize": 10}]}}},
}

TIME_FIELDS = {("dim_date", "date"), ("dim_date", "year"), ("dim_date", "quarter")}


def shows_time(v):
    """Does the visual lay out months, quarters or years (a trend), so a Year slicer must not
    cut it to one year?"""
    state = v["visual"].get("query", {}).get("queryState", {})
    for role in ("Category", "Series", "Columns", "Rows", "Values"):
        for p in state.get(role, {}).get("projections", []):
            col = p["field"].get("Column")
            if col and (col["Expression"]["SourceRef"]["Entity"], col["Property"]) in TIME_FIELDS:
                return True
    return False


def interactions(visuals):
    """Trend charts ignore the time slicers, so they keep all three years (rank 1)."""
    slicers = [v["name"] for v in visuals if v["name"] in ("slicer_year", "slicer_quarter")]
    return [{"source": s, "target": v["name"], "type": "NoFilter"}
            for s in slicers for v in visuals if v["visual"]["visualType"] != "slicer" and shows_time(v)]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))  # UTF-8, no BOM


def write_report(name, pages):
    folder = ROOT / f"{name}.Report"
    definition = folder / "definition"
    for generated in (definition, folder / "StaticResources"):
        if generated.exists():
            shutil.rmtree(generated)  # regenerated in full from this file
    write_json(folder / "definition.pbir",
               {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{MODEL_FOLDER}"}}})
    write_json(ROOT / f"{name}.pbip",
               {"version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}],
                "settings": {"enableAutoRecovery": True}})
    write_json(definition / "version.json",
               {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    # Two report settings Power BI Desktop saved on 13 October 2026, kept so the generated
    # files and Desktop's saved files agree (Filters pane collapsed, enhanced tooltips off),
    # and the Fjordvik theme (31 October 2026).
    write_json(definition / "report.json", {
        "$schema": f"{SCHEMA}/report/3.3.0/schema.json",
        "themeCollection": {"customTheme": {
            "name": THEME, "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.3.0"},
            "type": "RegisteredResources"}},
        "objects": {"outspacePane": [{"properties": {"expanded": lit("false")}}]},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": THEME, "path": THEME, "type": "CustomTheme"}]}],
        "settings": {"useEnhancedTooltips": False}})
    write_json(folder / "StaticResources" / "RegisteredResources" / THEME, THEME_JSON)
    write_json(definition / "pages" / "pages.json",
               {"$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
                "pageOrder": [p[0] for p in pages], "activePageName": pages[0][0]})
    for page_name, display, build in pages:
        visuals = build()
        page = definition / "pages" / page_name
        page_json = {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": page_name,
                     "displayName": display, "displayOption": "FitToPage", "height": 720, "width": 1280}
        links = interactions(visuals)
        if links:
            page_json["visualInteractions"] = links
        write_json(page / "page.json", page_json)
        for v in visuals:
            write_json(page / "visuals" / v["name"] / "visual.json", v)
    count = sum(1 for _ in definition.rglob("visual.json"))
    print(f"Wrote {len(pages)} pages and {count} visuals to {definition}")


def main():
    for name, pages in REPORTS.items():
        write_report(name, pages)


if __name__ == "__main__":
    main()
