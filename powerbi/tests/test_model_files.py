"""Offline checks on the model (TMDL) and report (PBIR) files. No Power BI needed.

They enforce docs/naming-conventions.md and catch the mistakes Power BI Desktop
would only show as a broken visual: a misspelt measure, a page missing from the
page order, a folder name that doesn't match its object.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MODEL = REPO / "FjordvikEmissions.SemanticModel" / "definition"
# Two reports on the one model since 31 October 2026: emissions and portfolio.
REPORTS = [REPO / f"{name}.Report" / "definition" for name in ("FjordvikEmissions", "FjordvikPortfolio")]

SHARED_SCHEMA = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_site": ["site_id", "site_name", "country", "site_type"],
    # scope3_category and method, and the seven value-chain tables, added 31 October 2026
    "dim_source": ["source_id", "source_name", "scope", "category", "scope3_category", "method"],
    "fact_emissions": ["date_key", "site_id", "source_id", "activity_amount", "unit",
                       "emission_factor", "tco2e"],
    "fact_site_metrics": ["date_key", "site_id", "revenue_eur", "fte"],
    "dim_scope3_category": ["scope3_category", "category_name", "status", "reason"],
    "dim_contract": ["contract_id", "site_id", "source_id", "supplier_name", "instrument",
                     "start_date_key", "end_date_key", "covered_share"],
    "fact_scope2_market": ["date_key", "site_id", "source_id", "contract_id", "instrument",
                           "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_energy_upstream": ["date_key", "site_id", "source_id", "based_on_source_id",
                             "activity_amount", "unit", "emission_factor", "tco2e"],
    "dim_supplier": ["supplier_id", "supplier_name", "country", "spend_category"],
    "fact_purchases": ["date_key", "site_id", "source_id", "supplier_id", "spend_category",
                       "method", "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_freight": ["date_key", "site_id", "source_id", "direction", "mode", "paid_by",
                     "tonnes", "distance_km", "activity_amount", "unit", "emission_factor",
                     "tco2e"],
    # Product portfolio and sales, added for phase 2 (31 October 2026)
    "dim_product_group": ["product_group", "product_family"],
    "dim_product": ["product_id", "product_name", "product_group", "product_family",
                    "made_at_site_id", "rated_kw", "kwh_per_year", "lifetime_years",
                    "list_price_eur", "standard_cost_eur"],
    "dim_region": ["region_id", "region_name"],
    "dim_score_criterion": ["criterion_id", "criterion_name", "weight", "source"],
    "fact_product_rating": ["date_key", "product_group", "criterion_id", "rating"],
    "dim_product_code": ["business_unit", "local_item_number", "product_id"],
    "fact_sales": ["date_key", "site_id", "product_id", "region_id", "units", "net_sales_eur",
                   "cost_of_sales_eur", "margin_eur"],
    "fact_data_issue": ["issue_id", "date_key", "site_id", "business_unit", "issue_type",
                        "detail", "line_count", "amount_eur", "status", "action"],
    "fact_use_phase": ["date_key", "site_id", "source_id", "product_id", "region_id", "units",
                       "net_sales_eur", "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_budget": ["date_key", "site_id", "product_group", "region_id", "budget_units",
                    "budget_net_sales_eur", "budget_margin_eur"],
}

# Numbers allowed in DAX, each a unit conversion or a key, never a rate or factor.
ALLOWED_NUMBERS = {
    "1", "2", "3",   # scope numbers, and ROUND to 3 decimals (0.001 t = 1 kg)
    "1000",          # kilograms per tonne
    "1000000",       # euros per million euros
    "10000",         # one year in a yyyymmdd date key (20250301 - 10000 = 20240301)
    "100",           # the month digits of a yyyymmdd key (contract dates shown as months)
    "0",             # zero, for signs (a rise or a fall) and for counting none as 0
}
# Measures named for a count or headcount carry no unit in brackets.
# Units Sold, Units Sold Prior Year, Data Issues and Weighted Score added for phase 2
# (31 October 2026): counts and a 1 to 10 score have no unit to bracket.
UNITLESS = {"Average FTE", "Emission Rows", "Sites Reporting", "Units Sold",
            "Units Sold Prior Year", "Data Issues", "Weighted Score",
            # Added with the report redesign (31 October 2026): planned units, open issues and
            # scorecard points are counts or scores, with no unit to bracket.
            "Budget Units", "Open Data Issues", "Weighted Score Prior Quarter",
            "Weighted Score Change vs Prior Quarter", "Company Weighted Score"}
# Text measures (display folder "Text") build the words on the report: card context lines,
# page titles and the footer. They return text, so they carry no unit and no number format
# (report redesign, 31 October 2026).
TEXT_FOLDER = "Text"


def parse_tables():
    """table name -> {"columns": [...], "measures": {name: {...}}}"""
    tables = {}
    for path in (MODEL / "tables").glob("*.tmdl"):
        lines = path.read_text(encoding="utf-8").split("\n")
        name = next(l.split(" ", 1)[1] for l in lines if l.startswith("table "))
        columns, measures = [], {}
        current = None
        for i, line in enumerate(lines):
            if line.startswith("\tcolumn "):
                columns.append(line.split(" ", 1)[1].strip().strip("'"))
                current = None
            elif line.startswith("\tmeasure "):
                m = re.match(r"\tmeasure '(.+?)' =(.*)$", line)
                current = {"description": lines[i - 1].startswith("\t///"),
                           "dax": m.group(2), "props": {}}
                measures[m.group(1)] = current
            elif current is not None and line.startswith("\t\t\t"):
                current["dax"] += "\n" + line.strip()
            elif current is not None and line.startswith("\t\tformatStringDefinition ="):
                current["props"]["formatStringDefinition"] = line.split("=", 1)[1].strip()
            elif current is not None and line.startswith("\t\t") and ":" in line:
                key, value = line.strip().split(":", 1)
                current["props"][key] = value.strip()
            elif line.startswith("\t") and not line.startswith("\t\t"):
                current = None
        tables[name] = {"columns": columns, "measures": measures}
    return tables


TABLES = parse_tables()
MEASURES = TABLES["_Measures"]["measures"]


def test_shared_schema_tables_and_columns_are_exact():
    for table, columns in SHARED_SCHEMA.items():
        assert TABLES[table]["columns"] == columns, table


def test_every_table_file_is_referenced_in_the_model():
    model = (MODEL / "model.tmdl").read_text(encoding="utf-8")
    for table in TABLES:
        assert f"ref table {table}\n" in model, table


def test_all_measures_live_in_the_measures_table():
    for table, info in TABLES.items():
        if table != "_Measures":
            assert not info["measures"], f"{table} holds measures"
    assert len(MEASURES) >= 10


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_measure_has_description_format_and_folder(name):
    m = MEASURES[name]
    assert m["description"], "no /// description"
    assert m["props"].get("displayFolder"), "no displayFolder"
    if m["props"]["displayFolder"] != TEXT_FOLDER:
        # A dynamic format string (formatStringDefinition) is a format too: the waterfall's
        # label position shows each step's value through one (31 October 2026).
        assert m["props"].get("formatString") or m["props"].get("formatStringDefinition"), \
            "no formatString"


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_measure_name_carries_its_unit(name):
    if name in UNITLESS or MEASURES[name]["props"].get("displayFolder") == TEXT_FOLDER:
        return
    # Activity units added 31 October 2026 with the Activity measures (Energy Used (kWh) and
    # others): each is the unit the sites report that source in, so the rule is unchanged.
    # tonne-km added the same day for Freight Transport (tonne-km), the unit of fact_freight.
    assert re.search(r"\((tCO2e|EUR|%|kWh|litres|kg|passenger-km|tonnes|tonne-km)\)$", name), \
        "unit missing from the name"


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_no_typed_in_rates_or_factors(name):
    dax = re.sub(r'"[^"]*"', "", MEASURES[name]["dax"])     # ignore text in quotes
    dax = re.sub(r"\[[^\]]*\]", "", dax)                    # ignore [names]
    dax = re.sub(r"\b\w+\[\w+\]", "", dax)                  # ignore table[column]
    numbers = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", dax))
    assert numbers <= ALLOWED_NUMBERS, f"unexpected numbers {numbers - ALLOWED_NUMBERS}"


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_measures_divide_with_divide_not_slash(name):
    dax = MEASURES[name]["dax"]
    assert not re.search(r"\]\s*/\s*\[", dax), "use DIVIDE() between measures"


COUNTRY_ROLES = {"Finland", "Sweden", "Estonia"}
# Region roles added for phase 2 (31 October 2026). They filter dim_region and deny the
# site emission and finance tables: the documented exception in naming-conventions.md.
REGION_ROLES = {"Nordics": "NOR", "Baltics": "BAL", "Western Europe": "WEU", "Rest of world": "ROW"}
DENIED_TO_REGIONS = {"fact_emissions", "fact_energy_upstream", "fact_purchases", "fact_freight",
                     "fact_scope2_market", "fact_site_metrics", "fact_data_issue"}


def test_three_country_roles_filter_dim_site():
    found = {}
    for path in (MODEL / "roles").glob("*.tmdl"):
        if path.stem in REGION_ROLES:
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r'tablePermission dim_site = dim_site\[country\] = "(\w+)"', text)
        assert m, path.name
        assert "modelPermission: read" in text
        found[path.stem] = m.group(1)
    assert found == {c: c for c in COUNTRY_ROLES}


def test_four_region_roles_filter_dim_region_and_deny_site_figures():
    found = {}
    for name, region_id in REGION_ROLES.items():
        text = (MODEL / "roles" / f"{name}.tmdl").read_text(encoding="utf-8")
        assert "modelPermission: read" in text
        assert f'tablePermission dim_region = dim_region[region_id] = "{region_id}"' in text
        found[name] = set(re.findall(r"tablePermission (\w+) = FALSE\(\)", text))
    assert all(denied == DENIED_TO_REGIONS for denied in found.values())


def test_model_files_are_utf8_without_bom():
    for path in list(MODEL.rglob("*.tmdl")) + [f for r in REPORTS for f in r.parent.rglob("*.json")]:
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

NAME = re.compile(r"^[\w-]{1,50}$")


def visuals():
    for path in (f for r in REPORTS for f in r.glob("pages/*/visuals/*/visual.json")):
        yield path, json.loads(path.read_text(encoding="utf-8"))


def fields(node, aliases=None):
    """Every {"Measure"|"Column": {... Entity ..., Property}} inside a visual. A filter
    query names its tables once in "From" and refers to them by alias ("Source"), so
    aliases are resolved to their table and those fields are checked too."""
    aliases = dict(aliases or {})
    if isinstance(node, dict):
        for item in node.get("From", []):
            aliases[item["Name"]] = item["Entity"]
        for kind in ("Measure", "Column"):
            if kind in node and "Property" in node[kind]:
                ref = node[kind]["Expression"]["SourceRef"]
                entity = ref["Entity"] if "Entity" in ref else aliases[ref["Source"]]
                yield kind, entity, node[kind]["Property"]
        for value in node.values():
            yield from fields(value, aliases)
    elif isinstance(node, list):
        for value in node:
            yield from fields(value, aliases)


def test_every_visual_field_exists_in_the_model():
    for path, v in visuals():
        for kind, entity, prop in fields(v):
            assert entity in TABLES, f"{path}: unknown table {entity}"
            pool = TABLES[entity]["measures"] if kind == "Measure" else TABLES[entity]["columns"]
            assert prop in pool, f"{path}: unknown {kind.lower()} {entity}[{prop}]"


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.parent.name)
def test_names_match_folders_and_follow_the_rules(report):
    pages = json.loads((report / "pages" / "pages.json").read_text(encoding="utf-8"))
    folders = sorted(p.name for p in (report / "pages").iterdir() if p.is_dir())
    assert sorted(pages["pageOrder"]) == folders
    for folder in folders:
        page = json.loads((report / "pages" / folder / "page.json").read_text(encoding="utf-8"))
        assert page["name"] == folder and NAME.match(folder)
        visual_names = {v.name for v in (report / "pages" / folder / "visuals").iterdir()}
        for link in page.get("visualInteractions", []):
            assert {link["source"], link["target"]} <= visual_names, (folder, link)
    for path, v in visuals():
        assert v["name"] == path.parent.name and NAME.match(v["name"]), path


def test_query_refs_are_unique_within_each_visual():
    for path, v in visuals():
        refs = [p["queryRef"] for role in v["visual"].get("query", {}).get("queryState", {}).values()
                for p in role["projections"]]
        assert len(refs) == len(set(refs)), path


def test_every_page_states_the_data_is_synthetic():
    """Since the redesign (31 October 2026) the caveat sits in every page's footer."""
    for report in REPORTS:
        for page in (report / "pages").iterdir():
            if page.is_dir():
                text = (page / "visuals" / "footer_note" / "visual.json").read_text(encoding="utf-8")
                assert "illustrative" in text and "Synthetic" in text, page.name


def test_every_page_has_page_buttons_a_footer_and_a_theme():
    for report in REPORTS:
        for page in (report / "pages").iterdir():
            if page.is_dir():
                names = {v.name for v in (page / "visuals").iterdir()}
                assert {"page_buttons", "footer_note", "footer_data", "title"} <= names, page
        assert (report.parent / "StaticResources" / "RegisteredResources" / "Fjordvik.json").exists()


def test_year_slicers_open_on_one_year():
    """Jasila's review, rank 1: with every year selected, cards add three years together."""
    for path, v in visuals():
        if v["name"] == "slicer_year":
            objects = v["visual"]["objects"]
            assert objects["selection"][0]["properties"]["singleSelect"]["expr"]["Literal"]["Value"] == "true"
            assert "filter" in objects["general"][0]["properties"], path


# Desktop rewrites this on every save to remember the last page open; it is
# viewer state, not report content, so the rebuild check leaves it out.
DESKTOP_VIEW_STATE = {"pages.json": {"activePageName"}}


def test_report_is_rebuilt_from_the_script(tmp_path, monkeypatch):
    """The committed report files hold the same content scripts/build_report.py writes.

    Compared as parsed JSON, not bytes: Power BI Desktop formats JSON its own way
    (line endings, no final newline), and a Desktop save must not fail this test
    when nothing in the report changed (decision 16 October 2026)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_report", REPO / "scripts" / "build_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    module.main()
    # .pbi holds Desktop's local settings and cache, git-ignored and not report content.
    originals = [f for r in REPORTS for f in r.parent.rglob("*.json") if ".pbi" not in f.parts]
    rebuilt_files = {f.relative_to(tmp_path) for f in tmp_path.rglob("*.json") if ".Report" in str(f)}
    assert rebuilt_files == {f.relative_to(REPO) for f in originals}, "report files added or missing"
    for original in originals:
        rebuilt = tmp_path / original.relative_to(REPO)
        want = json.loads(rebuilt.read_text(encoding="utf-8-sig"))
        have = json.loads(original.read_text(encoding="utf-8-sig"))
        for key in DESKTOP_VIEW_STATE.get(original.name, set()):
            want.pop(key, None)
            have.pop(key, None)
        assert have == want, original
