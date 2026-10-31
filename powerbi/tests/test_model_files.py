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
REPORT = REPO / "FjordvikEmissions.Report" / "definition"

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
}

# Numbers allowed in DAX, each a unit conversion or a key, never a rate or factor.
ALLOWED_NUMBERS = {
    "1", "2", "3",   # scope numbers, and ROUND to 3 decimals (0.001 t = 1 kg)
    "1000",          # kilograms per tonne
    "1000000",       # euros per million euros
    "10000",         # one year in a yyyymmdd date key (20250301 - 10000 = 20240301)
}
# Measures named for a count or headcount carry no unit in brackets.
UNITLESS = {"Average FTE", "Emission Rows", "Sites Reporting"}


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
    assert m["props"].get("formatString"), "no formatString"
    assert m["props"].get("displayFolder"), "no displayFolder"


@pytest.mark.parametrize("name", sorted(MEASURES))
def test_measure_name_carries_its_unit(name):
    if name in UNITLESS:
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


def test_three_country_roles_filter_dim_site():
    countries = {"Finland", "Sweden", "Estonia"}
    found = {}
    for path in (MODEL / "roles").glob("*.tmdl"):
        text = path.read_text(encoding="utf-8")
        m = re.search(r'tablePermission dim_site = dim_site\[country\] = "(\w+)"', text)
        assert m, path.name
        assert "modelPermission: read" in text
        found[path.stem] = m.group(1)
    assert found == {c: c for c in countries}


def test_model_files_are_utf8_without_bom():
    for path in list(MODEL.rglob("*.tmdl")) + list(REPORT.rglob("*.json")):
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), path


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

NAME = re.compile(r"^[\w-]{1,50}$")


def visuals():
    for path in REPORT.glob("pages/*/visuals/*/visual.json"):
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


def test_names_match_folders_and_follow_the_rules():
    pages = json.loads((REPORT / "pages" / "pages.json").read_text(encoding="utf-8"))
    folders = sorted(p.name for p in (REPORT / "pages").iterdir() if p.is_dir())
    assert sorted(pages["pageOrder"]) == folders
    for folder in folders:
        page = json.loads((REPORT / "pages" / folder / "page.json").read_text(encoding="utf-8"))
        assert page["name"] == folder and NAME.match(folder)
    for path, v in visuals():
        assert v["name"] == path.parent.name and NAME.match(v["name"]), path


def test_query_refs_are_unique_within_each_visual():
    for path, v in visuals():
        refs = [p["queryRef"] for role in v["visual"].get("query", {}).get("queryState", {}).values()
                for p in role["projections"]]
        assert len(refs) == len(set(refs)), path


def test_every_page_states_the_data_is_synthetic():
    for page in (REPORT / "pages").iterdir():
        if page.is_dir():
            text = (page / "visuals" / "title" / "visual.json").read_text(encoding="utf-8")
            assert "illustrative" in text and "Synthetic" in text, page.name


# Desktop rewrites this on every save to remember the last page open; it is
# viewer state, not report content, so the rebuild check leaves it out.
DESKTOP_VIEW_STATE = {"pages.json": {"activePageName"}}


def test_report_is_rebuilt_from_the_script(tmp_path, monkeypatch):
    """The committed report files hold the same content scripts/build_report.py writes.

    Compared as parsed JSON, not bytes: Power BI Desktop formats JSON its own way
    (line endings, no final newline), and a Desktop save must not fail this test
    when nothing in the report changed (decision 16 October 2026)."""
    import importlib.util
    import shutil
    copy = tmp_path / "FjordvikEmissions.Report"
    shutil.copytree(REPORT.parent, copy)
    spec = importlib.util.spec_from_file_location("build_report", REPO / "scripts" / "build_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPORT", copy)
    module.main()
    for original in REPORT.rglob("*.json"):
        rebuilt = copy / "definition" / original.relative_to(REPORT)
        want = json.loads(rebuilt.read_text(encoding="utf-8-sig"))
        have = json.loads(original.read_text(encoding="utf-8-sig"))
        for key in DESKTOP_VIEW_STATE.get(original.name, set()):
            want.pop(key, None)
            have.pop(key, None)
        assert have == want, original
