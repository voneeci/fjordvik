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
MARKET = "Scope 2 Market-based Emissions (tCO2e)"
MARKET_COLOUR = "#8A5A0B"
CATEGORY = column("dim_scope3_category", "category_name", "Scope 3 category")
VALUE_CHAIN_CARDS = ["Scope 3 Emissions (tCO2e)", "Purchased Goods and Services Emissions (tCO2e)",
                     "Fuel and Energy Related Emissions (tCO2e)",
                     "Upstream Transport Emissions (tCO2e)", "Downstream Transport Emissions (tCO2e)"]
FREIGHT = [("Upstream Transport Emissions (tCO2e)", "#7A5BA6"),
           ("Downstream Transport Emissions (tCO2e)", "#3F2D63")]
FAMILY = column("dim_product_group", "product_family", "Family")
GROUP = column("dim_product_group", "product_group", "Product group")
REGION = column("dim_region", "region_name", "Region")
PRODUCT = column("dim_product", "product_name", "Product")
QUARTER = column("dim_date", "quarter", "Quarter")
FAMILY_COLOURS = {"Industrial process pumps": "#2A78D6", "Water and wastewater pumps": "#1BAF7A",
                  "Pump packages and controls": "#EB6834", "Spare parts and service": "#7A5BA6"}
SALES_CARDS = ["Units Sold", "Net Sales (EUR)", "Average Price (EUR)", "Margin (EUR)", "Margin (%)"]
EFFECTS = ["Price Effect (EUR)", "Mix Effect (EUR)", "Quantity Effect (EUR)", "Cost Effect (EUR)",
           "Not Comparable Change (EUR)"]
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
            "A portfolio project. " + CAVEAT]),
        page_navigator("page_buttons", 20, 90, 1240, 50, 100),
        section("about_company", 20, 155, 600, 175, 200, "About the company", [
            "Fjordvik Manufacturing Oy makes electric pumps and pump systems for water utilities, "
            "industry and buildings: process pumps in Tampere, water and wastewater pumps in "
            "Gothenburg, pump packages and controls in Tallinn, with warehouses in Oulu and Tartu "
            "and a head office in Helsinki.",
            "Each month the sites report the energy, fuel, refrigerant, flights and waste they "
            "used; purchasing, logistics, energy contracts and the ERP sales extract add the value "
            "chain and the product portfolio, January 2023 to December 2025.",
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
        section("page_guide", 640, 155, 620, 270, 500, "What each page answers", [
            "Emissions: Overview, Emissions breakdown, Value chain (scope 3), Scope 2 methods, "
            "Intensity and growth, Energy and activity, What changed, Sites and Data quality: how "
            "much Fjordvik emits, where, why it moved, and whether the figures reconcile.",
            "Portfolio: Portfolio overview, Price, volume and mix, Portfolio balance, Product "
            "sustainability, Quarterly scorecard, and Classification and data quality: what sells, "
            "what earns, why margin moved, how products score, and what the ERP data got wrong.",
            "Country managers see their own sites; sales region managers see their own region's "
            "sales and blank site figures.",
        ]),
        section("reading_guide", 640, 435, 620, 270, 600, "How to read the figures", [
            "Scope 1: fuel burned on site and refrigerant leaks. Scope 2: electricity and heat "
            "bought, at each country's average factor (location-based); market-based is shown "
            "beside it. Scope 3: purchases, upstream fuel and grid losses, freight, flights and "
            "landfill waste. Totals are location-based.",
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


def value_chain():
    return [
        *header("Value chain (scope 3)",
                "The scope 3 categories counted, and why the others are not. Category 11, use of "
                "sold products, is likely the largest and needs product data."),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 100, 300 + i, m)
          for i, m in enumerate(VALUE_CHAIN_CARDS)],
        # Scope 3 measure, not the total: scope 1 and 2 sources have no category, so the
        # total would add a blank bar holding scopes 1 and 2.
        chart("clusteredBarChart", "bar_by_scope3_category", 20, 210, 400, 250, 400, CATEGORY,
              [measure("Scope 3 Emissions (tCO2e)")], sort_by_value=True, title="Scope 3 emissions by category (tCO2e)",
              colours=single("#7A5BA6"), labels=True),
        chart("clusteredBarChart", "bar_purchases_by_spend_category", 440, 210, 400, 250, 500,
              column("fact_purchases", "spend_category", "Spend category"),
              [measure("Purchased Goods and Services Emissions (tCO2e)")], sort_by_value=True,
              title="Purchased goods and services by spend category (tCO2e)",
              colours=single("#7A5BA6"), labels=True),
        chart("clusteredColumnChart", "column_freight_by_mode", 860, 210, 400, 250, 600,
              column("fact_freight", "mode", "Mode"), [measure(m) for m, _c in FREIGHT],
              title="Freight by mode: paid by Fjordvik (category 4) and customers (9) (tCO2e)",
              colours=[(for_measure(m), c) for m, c in FREIGHT], legend=True),
        table("table_scope3_categories", 20, 475, 1240, 235, 700, [
            column("dim_scope3_category", "scope3_category", "No."), CATEGORY,
            column("dim_scope3_category", "status", "Status"),
            column("dim_scope3_category", "reason", "What it covers, or why not")],
            title="All 15 scope 3 categories (the Greenhouse Gas Protocol requires a reason for "
                  "each one left out)"),
    ]


def scope2_methods():
    cards = ["Scope 2 Emissions (tCO2e)", MARKET, TOTAL, "Total Emissions Market-based (tCO2e)",
             "Electricity with Guarantees of Origin (%)"]
    methods = [("Scope 2 Emissions (tCO2e)", SCOPE_COLOURS[2]), (MARKET, MARKET_COLOUR)]
    return [
        *header("Scope 2: location-based and market-based",
                "Market-based uses the guarantees of origin Fjordvik buys and each country's "
                "residual mix for the rest. It is shown beside the total, never added to it."),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 100, 300 + i, m) for i, m in enumerate(cards)],
        chart("clusteredColumnChart", "column_methods_by_year", 20, 210, 620, 250, 400, YEAR,
              [measure(m) for m, _c in methods],
              title="Scope 2 by method and year: location-based and market-based (tCO2e)",
              colours=[(for_measure(m), c) for m, c in methods], labels=True, legend=True),
        chart("clusteredBarChart", "bar_methods_by_site", 660, 210, 600, 250, 500, SITE,
              [measure(m) for m, _c in methods],
              title="Scope 2 by method and site (tCO2e)",
              colours=[(for_measure(m), c) for m, c in methods], legend=True),
        table("table_contracts", 20, 475, 620, 235, 600, [
            column("dim_contract", "site_id", "Site"),
            column("dim_contract", "supplier_name", "Supplier"),
            column("dim_contract", "instrument", "Instrument"),
            column("dim_contract", "covered_share", "Share of kWh covered"),
            column("dim_contract", "start_date_key", "From"),
            column("dim_contract", "end_date_key", "To")],
            title="Electricity contracts with guarantees of origin"),
        matrix("matrix_market_by_instrument", 660, 475, 600, 235, 700,
               [column("fact_scope2_market", "instrument", "Instrument")], [YEAR],
               [measure(MARKET)], title="Market-based scope 2 by instrument and year (tCO2e)"),
    ]


def portfolio_overview():
    return [
        *header("Portfolio overview",
                "Volume, sales, price and margin from the cleaned ERP sales (the extract is simulated).",
                slicers=(YEAR, REGION)),
        *[card(f"card_{i}", 20 + i * 250, 95, 240, 100, 300 + i, m) for i, m in enumerate(SALES_CARDS)],
        chart("columnChart", "column_sales_by_month", 20, 210, 760, 260, 400, MONTH,
              [measure("Net Sales (EUR)")], series=FAMILY, title="Net sales by month and family (EUR)",
              colours=[(for_value(FAMILY, f), c) for f, c in FAMILY_COLOURS.items()], legend=True),
        chart("clusteredBarChart", "bar_margin_pct_by_group", 800, 210, 460, 260, 500, GROUP,
              [measure("Margin (%)")], sort_by_value=True, title="Margin by product group (%)",
              colours=single(), labels=True),
        table("table_by_family", 20, 485, 1240, 225, 600, [
            FAMILY, GROUP, measure("Units Sold"), measure("Net Sales (EUR)"),
            measure("Average Price (EUR)"), measure("Margin (EUR)"), measure("Margin (%)")],
            title="Sales and margin by family and product group"),
    ]


def price_volume_mix():
    return [
        *header("Price, volume and mix",
                "How margin moved against the same months a year earlier (ACCA, prior year as "
                "standard). Pick one family: across pumps and spare parts, mix and quantity mislead.",
                slicers=(YEAR, FAMILY)),
        card("card_prior", 20, 95, 300, 100, 300, "Margin Prior Year (EUR)"),
        card("card_change", 340, 95, 300, 100, 301, "Margin Change vs Prior Year (EUR)"),
        card("card_margin", 660, 95, 300, 100, 302, "Margin (EUR)"),
        card("card_volume", 980, 95, 280, 100, 303, "Volume Effect (EUR)"),
        chart("clusteredBarChart", "bar_effects", 20, 210, 620, 290, 400, YEAR,
              [measure(m) for m in EFFECTS],
              title="What moved margin: price, mix, quantity, cost and not comparable (EUR)",
              colours=[(for_measure(m), c) for m, c in zip(EFFECTS, ["#1F6FA8", "#C77A1A", "#7A5BA6",
                                                                    "#C4502A", "#6B6B6B"])],
              labels=True, legend=True),
        matrix("matrix_effects_by_family", 660, 210, 600, 290, 500, [FAMILY], [YEAR],
               [measure("Price Effect (EUR)"), measure("Volume Effect (EUR)"), measure("Cost Effect (EUR)")],
               title="Price, volume and cost effect by family and year (EUR)"),
        table("table_effects_by_group", 20, 515, 1240, 195, 600, [
            GROUP, measure("Margin Prior Year (EUR)"), *[measure(m) for m in EFFECTS],
            measure("Margin (EUR)")], title="Bridge by product group (EUR)"),
    ]


def portfolio_balance():
    return [
        *header("Portfolio balance", "Where sales and margin come from, by family and region.",
                slicers=(YEAR,)),
        chart("donutChart", "donut_share_by_family", 20, 95, 400, 300, 300, FAMILY,
              [measure("Net Sales (EUR)")], sort_by_value=True, title="Share of net sales by family",
              colours=[(for_value(FAMILY, f), c) for f, c in FAMILY_COLOURS.items()],
              labels=True, legend=True),
        matrix("matrix_share_family_region", 440, 95, 820, 300, 400, [FAMILY], [REGION],
               [measure("Share of Net Sales (%)")], title="Share of net sales by family and region (%)"),
        chart("clusteredBarChart", "bar_share_margin_by_group", 20, 410, 620, 300, 500, GROUP,
              [measure("Share of Margin (%)")], sort_by_value=True, title="Share of margin by product group (%)",
              colours=single(), labels=True),
        chart("clusteredColumnChart", "column_sales_by_region", 660, 410, 600, 300, 600, REGION,
              [measure("Net Sales (EUR)")], sort_by_value=True, title="Net sales by region (EUR)",
              colours=single(), labels=True),
    ]


def product_sustainability():
    cards = ["Use-phase Emissions (tCO2e)", "Use-phase Emissions per Unit (tCO2e)",
             "Use-phase Emissions per Thousand EUR (tCO2e)"]
    return [
        *header("Product sustainability",
                "Scope 3 category 11: the lifetime electricity of the pumps sold, at the grid factor of "
                "the region of use. Rest of world is not calculated (no factor source).",
                slicers=(YEAR, REGION)),
        *[card(f"card_{i}", 20 + i * 420, 95, 400, 100, 300 + i, m) for i, m in enumerate(cards)],
        chart("clusteredBarChart", "bar_per_unit_by_group", 20, 210, 620, 260, 400, GROUP,
              [measure("Use-phase Emissions per Unit (tCO2e)")], sort_by_value=True,
              title="Use-phase emissions per unit sold, by product group (tCO2e)", colours=single("#7A5BA6"),
              labels=True),
        chart("clusteredColumnChart", "column_use_phase_by_region", 660, 210, 600, 260, 500, REGION,
              [measure("Use-phase Emissions (tCO2e)")], sort_by_value=True,
              title="Use-phase emissions by region of use (tCO2e)", colours=single("#7A5BA6"), labels=True),
        table("table_products", 20, 485, 1240, 225, 600, [
            PRODUCT, column("dim_product", "kwh_per_year", "kWh a year"),
            column("dim_product", "lifetime_years", "Lifetime (years)"),
            measure("Units Sold"), measure("Use-phase Emissions per Unit (tCO2e)"),
            measure("Use-phase Emissions per Thousand EUR (tCO2e)")],
            title="Each product: specification and use-phase emissions"),
    ]


def scorecard():
    return [
        *header("Quarterly portfolio scorecard",
                "Each quarter's review rates every product group 1 to 10 on six criteria; weights are "
                "Fjordvik's own choice. The figures beside the score inform the next review.",
                slicers=(YEAR, FAMILY)),
        matrix("matrix_score_by_quarter", 20, 95, 760, 330, 300, [GROUP], [YEAR, QUARTER],
               [measure("Weighted Score")], title="Weighted score by product group and quarter"),
        table("table_criteria", 800, 95, 460, 330, 400, [
            column("dim_score_criterion", "criterion_name", "Criterion"),
            column("dim_score_criterion", "weight", "Weight")],
            title="Criteria (Cooper and Edgett) and Fjordvik's weights"),
        table("table_score_and_kpis", 20, 440, 1240, 270, 500, [
            GROUP, measure("Weighted Score"), measure("Net Sales (EUR)"), measure("Margin (%)"),
            measure("Share of Net Sales (%)"), measure("Price Effect (EUR)"),
            measure("Use-phase Emissions per Unit (tCO2e)")],
            title="Score beside the figures: sales, margin, share, price effect, use-phase emissions"),
    ]


def classification():
    return [
        textbox("title", 20, 10, 1240, 70, 0, [
            "Classification and data quality",
            "What the SQL found in the simulated ERP extract, for the data owner. " + CAVEAT]),
        card("card_issues", 20, 95, 300, 100, 100, "Data Issues"),
        card("card_quarantined", 340, 95, 300, 100, 101, "Quarantined Sales (EUR)"),
        card("card_recon", 660, 95, 300, 100, 102, "Sales Reconciliation Difference (EUR)"),
        table("table_issues", 20, 210, 1240, 250, 200, [
            column("dim_date", "date", "Month"), SITE,
            column("fact_data_issue", "issue_type", "Issue"),
            column("fact_data_issue", "detail", "Detail"),
            column("fact_data_issue", "line_count", "Lines"),
            column("fact_data_issue", "amount_eur", "Amount (EUR)"),
            column("fact_data_issue", "status", "Status"),
            column("fact_data_issue", "action", "Action for the data owner")],
            title="Issues found in the extract"),
        table("table_codes", 20, 475, 1240, 235, 300, [
            column("dim_product_code", "business_unit", "Business unit"),
            column("dim_product_code", "local_item_number", "Local item number"),
            column("dim_product", "product_id", "Global product"), PRODUCT, FAMILY],
            title="The global product classification: local item numbers by business unit"),
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
        card("card_market_difference", 980, 95, 280, 110, 103,
             "Market-based Reconciliation Difference (tCO2e)"),
        table("table_by_year", 20, 220, 1240, 200, 200, [
            YEAR, measure("Emission Rows"), measure("Sites Reporting"), measure(TOTAL),
            measure("Recalculated Emissions (tCO2e)"), measure("Reconciliation Difference (tCO2e)")],
            title="Reconciliation by year"),
    ]


PAGES = [("introduction", "Introduction", introduction), ("overview", "Overview", overview),
         ("breakdown", "Emissions breakdown", breakdown),
         ("value_chain", "Value chain (scope 3)", value_chain),
         ("scope2_methods", "Scope 2 methods", scope2_methods),
         ("intensity", "Intensity and growth", intensity), ("energy", "Energy and activity", energy),
         ("changed", "What changed", changed), ("sites", "Sites", sites),
         ("data_quality", "Data quality", data_quality),
         ("portfolio_overview", "Portfolio overview", portfolio_overview),
         ("price_volume_mix", "Price, volume and mix", price_volume_mix),
         ("portfolio_balance", "Portfolio balance", portfolio_balance),
         ("product_sustainability", "Product sustainability", product_sustainability),
         ("scorecard", "Quarterly scorecard", scorecard),
         ("classification", "Classification and data quality", classification)]


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
