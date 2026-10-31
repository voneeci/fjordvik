"""Rules for the value-chain tables: market-based scope 2 and scope 3 categories 1, 3, 4, 9."""

from collections import Counter, defaultdict

from fjordvik_data import config as c

VALUE_FACTS = ["fact_scope2_market", "fact_energy_upstream", "fact_purchases", "fact_freight",
               "fact_use_phase"]
GRAIN = {
    "fact_scope2_market": ("date_key", "site_id", "source_id", "instrument"),
    "fact_energy_upstream": ("date_key", "site_id", "source_id", "based_on_source_id"),
    "fact_purchases": ("date_key", "site_id", "supplier_id"),
    "fact_freight": ("date_key", "site_id", "direction", "mode", "paid_by"),
    "fact_use_phase": ("date_key", "site_id", "product_id", "region_id"),
}
STATUSES = {"Calculated", "Calculated in part", "Not yet calculated", "Not relevant"}


def test_keys_are_unique_at_each_tables_grain(tables):
    for name, cols in GRAIN.items():
        keys = Counter(tuple(r[col] for col in cols) for r in tables[name])
        assert max(keys.values()) == 1, name


def test_every_row_joins_to_its_dimensions(tables):
    dates = {r["date_key"] for r in tables["dim_date"]}
    sites = {r["site_id"] for r in tables["dim_site"]}
    sources = {r["source_id"] for r in tables["dim_source"]}
    suppliers = {r["supplier_id"] for r in tables["dim_supplier"]}
    contracts = {r["contract_id"] for r in tables["dim_contract"]}
    for name in VALUE_FACTS:
        for r in tables[name]:
            assert r["date_key"] in dates and r["site_id"] in sites, (name, r)
            assert r["source_id"] in sources, (name, r)
    assert all(r["supplier_id"] in suppliers for r in tables["fact_purchases"])
    assert all(r["contract_id"] in contracts | {""} for r in tables["fact_scope2_market"])
    assert all(r["based_on_source_id"] in sources for r in tables["fact_energy_upstream"])


def test_tco2e_equals_activity_times_factor_over_1000(tables):
    for name in VALUE_FACTS:
        for r in tables[name]:
            expected = float(r["activity_amount"]) * float(r["emission_factor"]) / 1000
            assert abs(float(r["tco2e"]) - expected) < 1e-6, (name, r)
            assert float(r["activity_amount"]) >= 0, (name, r)


def test_market_based_uses_exactly_the_location_based_kwh(tables):
    """Scope 2 Guidance: both methods cover the same energy; only the factor differs."""
    location = {(r["date_key"], r["site_id"], r["source_id"]): float(r["activity_amount"])
                for r in tables["fact_emissions"] if r["source_id"] in ("S05", "S06")}
    market = defaultdict(float)
    for r in tables["fact_scope2_market"]:
        market[(r["date_key"], r["site_id"], r["source_id"])] += float(r["activity_amount"])
    assert set(market) == set(location)
    for key, kwh in location.items():
        assert abs(market[key] - kwh) < 0.005, key


def test_market_factors_follow_the_contract_or_the_residual_mix(tables):
    country = {r["site_id"]: r["country"] for r in tables["dim_site"]}
    contracts = {r["contract_id"]: r for r in tables["dim_contract"]}
    for r in tables["fact_scope2_market"]:
        factor = float(r["emission_factor"])
        if r["instrument"] == "Residual mix":
            assert factor == c.RESIDUAL_MIX_FACTOR[country[r["site_id"]]]
        elif r["instrument"] == "Network declared value":
            assert r["source_id"] == "S06"
            assert factor == c.HEAT_NETWORK_FACTOR[country[r["site_id"]]]
        else:
            k = contracts[r["contract_id"]]
            assert factor == c.GO_FACTOR
            assert (k["site_id"], k["source_id"]) == (r["site_id"], r["source_id"])
            assert k["start_date_key"] <= r["date_key"] <= k["end_date_key"]


def test_category_3_is_derived_from_the_reported_fuel_and_kwh(tables):
    country = {r["site_id"]: r["country"] for r in tables["dim_site"]}
    upstream = {(r["date_key"], r["site_id"], r["based_on_source_id"]): r
                for r in tables["fact_energy_upstream"]}
    parents = set(c.WTT_FACTOR) | set(c.TD_FACTOR)
    expected = {(r["date_key"], r["site_id"], r["source_id"]): r
                for r in tables["fact_emissions"] if r["source_id"] in parents}
    assert set(upstream) == set(expected)
    for key, parent in expected.items():
        row = upstream[key]
        assert row["activity_amount"] == parent["activity_amount"]
        assert row["unit"] == parent["unit"]
        src = parent["source_id"]
        if src in c.WTT_FACTOR:
            assert row["source_id"] == "S09"
            assert float(row["emission_factor"]) == c.WTT_FACTOR[src]
        else:
            assert row["source_id"] == "S10"
            assert float(row["emission_factor"]) == c.TD_FACTOR[src][country[row["site_id"]]]


def test_purchases_are_spend_based_in_euros(tables):
    category = {r["supplier_id"]: r["spend_category"] for r in tables["dim_supplier"]}
    for r in tables["fact_purchases"]:
        assert r["source_id"] == "S11" and r["unit"] == "EUR" and r["method"] == "Spend-based"
        assert r["spend_category"] == category[r["supplier_id"]]
        assert float(r["emission_factor"]) == c.SPEND_FACTOR[r["spend_category"]]


def test_freight_is_tonnes_times_distance_and_split_by_who_pays(tables):
    """Category 9 is outbound freight the customer pays for; all other freight is 4."""
    for r in tables["fact_freight"]:
        tkm = float(r["tonnes"]) * float(r["distance_km"])
        assert abs(float(r["activity_amount"]) - tkm) < 0.006, r
        assert r["unit"] == "tonne-km"
        assert float(r["emission_factor"]) == c.FREIGHT_FACTOR[r["mode"]]
        customer_paid = (r["direction"], r["paid_by"]) == ("Outbound", "Customer")
        assert r["source_id"] == ("S13" if customer_paid else "S12"), r


def test_every_scope_3_category_has_a_status_and_a_reason(tables):
    """The Scope 3 Standard requires excluded categories to be listed with a reason."""
    for r in tables["dim_scope3_category"]:
        assert r["status"] in STATUSES, r
        assert len(r["reason"]) > 20, r


def test_sources_match_the_status_of_their_category(tables):
    """Scope 1 and 2 sources have no scope 3 category; a scope 3 source sits in a
    category that is calculated (in full or in part), and every such category has
    a source with rows."""
    status = {r["scope3_category"]: r["status"] for r in tables["dim_scope3_category"]}
    with_rows = set()
    for name in ["fact_emissions", *VALUE_FACTS]:
        with_rows |= {r["source_id"] for r in tables[name]}
    calculated = set()
    for r in tables["dim_source"]:
        if r["scope"] in ("1", "2"):
            assert r["scope3_category"] == "", r
        else:
            assert status[r["scope3_category"]] in ("Calculated", "Calculated in part"), r
            assert r["source_id"] in with_rows, r
            calculated.add(r["scope3_category"])
        assert r["method"], r
    assert calculated == {n for n, s in status.items()
                          if s in ("Calculated", "Calculated in part")}
