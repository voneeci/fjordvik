"""The data dictionary: every column, measure and metric is described, the values match
the Power BI reference sums, and the workbook is the same on every build.

All data is synthetic: Fjordvik Manufacturing Oy is fictional.
"""

import csv
import importlib.util
from pathlib import Path

import pytest

from fjordvik_data import dictionary as D
from fjordvik_data import dictionary_text as T
from fjordvik_data import xlsx

REPO = Path(__file__).resolve().parents[2]
COMMITTED = REPO / "docs" / "data-dictionary.xlsx"


@pytest.fixture(scope="module")
def sheets():
    return D.build()


@pytest.fixture(scope="module")
def values():
    return D.Values()


@pytest.fixture(scope="module")
def expected():
    """The independent Python sums the live Power BI tests compare every measure with."""
    path = REPO / "powerbi" / "tests" / "expected.py"
    spec = importlib.util.spec_from_file_location("powerbi_expected", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_table_and_column_is_described():
    headers = D.headers()
    assert set(headers) == set(T.TABLES), set(headers) ^ set(T.TABLES)
    missing = [f"{t}.{c}" for t, cols in headers.items() for c in cols
               if (t, c) not in T.COLUMN_OVERRIDES and c not in T.COLUMNS]
    assert not missing, missing
    assert set(T.GRAIN) == {t for t in headers if t.startswith("fact_")}


def test_every_result_file_column_is_described():
    for path in T.RESULT_FILES:
        with (REPO / path).open(encoding="utf-8", newline="") as f:
            cols = next(csv.reader(f))
        assert not [c for c in cols if c not in T.RESULT_COLUMNS], path


def test_every_power_bi_measure_has_a_description_and_links_resolve():
    ms = {m["name"]: m for m in D.measures()}
    assert len(ms) >= 130
    assert not [n for n, m in ms.items() if not m["description"]]
    assert not [n for n in T.MEASURE_METRIC if n not in ms]
    for m in T.METRICS:
        for name in filter(None, (x.strip() for x in m["measure"].split(";"))):
            assert name in ms, (m["code"], name)


def test_metric_catalogue_is_consistent():
    codes = [m["code"] for m in T.METRICS]
    assert len(codes) == len(set(codes))
    headers = D.headers()
    for m in T.METRICS:
        assert m["status"] in ("Active", "Dormant") and m["kind"] in ("Actual", "Derived"), m["code"]
        assert m["classification"] in T.CLASSES, m["code"]
        assert all(d in codes for d in m["depends"]), m["code"]
        for f in m["inputs"]:
            table, col = f.split(".")
            assert col in headers[table], (m["code"], f)
        assert m["description"] and m["use"] and m["calculation"], m["code"]


def test_dormant_metrics_have_no_values_and_active_ones_do(sheets):
    rows = {s["name"]: s["rows"] for s in sheets}["Metrics"]
    h = rows[0]
    status, y25, example = h.index("Status"), h.index("2025"), h.index("Example value")
    for r in rows[1:]:
        if r[status] == "Dormant":
            assert r[y25] == "" and r[example] == "", r[0]
        else:
            assert r[example] != "", r[0]


@pytest.mark.parametrize("year", D.YEARS)
def test_values_match_the_power_bi_reference_sums(values, expected, year):
    checks = [
        ("EM_TOTAL_TCO2E", expected.emissions(year=year), 0.001),
        ("EM_SCOPE1_TCO2E", expected.emissions(year=year, scope=1), 0.001),
        ("EM_SCOPE2_LOC_TCO2E", expected.emissions(year=year, scope=2), 0.001),
        ("EM_SCOPE3_TCO2E", expected.emissions(year=year, scope=3), 0.001),
        ("EM_CAT11_TCO2E", expected.use_phase(year=year), 0.001),
        ("EM_PER_MEUR", expected.per_million_eur(year=year), 0.001),
        ("FIN_REVENUE_EUR", expected.revenue(year=year), 0.01),
        ("FIN_FTE_AVG", expected.average_fte(year=year), 0.001),
        ("SALES_NET_EUR", expected.sales("net_sales_eur", year=year), 0.01),
        ("SALES_BUDGET_NET_EUR", expected.budget("budget_net_sales_eur", year=year), 0.01),
        ("PF_SCORE", expected.weighted_score(year=year), 0.00001),
        ("EN_ELECTRICITY_KWH", expected.activity(source="S05", year=year), 0.001),
    ]
    for code, want, tolerance in checks:
        assert abs(values.value(code, year) - want) <= tolerance, (code, year, values.value(code, year), want)


def test_reconciliations_are_zero(values):
    for year in D.YEARS:
        assert values.value("DQ_SALES_RECON_EUR", year) == 0
        assert values.value("DQ_EMISSIONS_RECON_T", year) == 0


def test_workbook_round_trips_and_is_repeatable(sheets, tmp_path):
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    xlsx.write(a, sheets)
    xlsx.write(b, sheets)
    assert a.read_bytes() == b.read_bytes()
    wb = xlsx.read(a)
    assert list(wb)[:7] == ["Read me", "Metrics", "Fields", "Measures", "Tables", "Rules and tools", "Column reference"]
    assert len(wb["Metrics"]) == len(T.METRICS) + 1
    assert len(wb["Tables"]) == len(T.TABLES) + 1
    assert sum(1 for r in wb["Fields"][1:] if not r[0].startswith("service-ai/")) == sum(len(c) for c in D.headers().values())


def test_every_sheet_column_is_in_the_column_reference(sheets):
    by_name = {s["name"]: s["rows"] for s in sheets}
    explained = {(r[0], r[1]) for r in by_name["Column reference"][1:]}
    for name, rows in by_name.items():
        if name in ("Read me", "Column reference"):
            continue
        assert not [c for c in rows[0] if (name, c) not in explained], name


def test_data_sheets_are_excel_tables_with_unique_names(sheets):
    tables = [s["table"] for s in sheets if s.get("table")]
    assert len(tables) == len(sheets) - 1 and len(set(tables)) == len(tables)


def test_committed_workbook_matches_a_fresh_build(sheets, tmp_path):
    if not COMMITTED.exists():
        pytest.skip("docs/data-dictionary.xlsx is not committed yet: it waits for its layout map entry")
    fresh = tmp_path / "fresh.xlsx"
    xlsx.write(fresh, sheets)
    assert COMMITTED.read_bytes() == fresh.read_bytes(), "rebuild: python -m fjordvik_data.dictionary --out ../docs/data-dictionary.xlsx"
