"""After-sales service tables: keys, joins, physical ranges and the reconciliation of
parts orders to fact_sales (added 2 November 2026)."""

import csv
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fjordvik_data import config as c

SALES_PRODUCTS = {"SPS-SP-100", "SPS-SK-200"}
SKILL = {m: v[4] for m, v in c.FAILURE_MODES.items()}


def fits(tables) -> set[tuple[str, str]]:
    return {(r["part_id"], r["product_group"]) for r in tables["bridge_part_compatibility"]}


def group_of_asset(tables) -> dict:
    group = {p["product_id"]: p["product_group"] for p in tables["dim_product"]}
    return {a["asset_id"]: group[a["product_id"]] for a in tables["dim_asset"]}


def test_service_keys_are_unique(tables):
    for table, key in [("dim_customer", ("customer_id",)), ("dim_customer", ("customer_name",)),
                       ("dim_asset", ("asset_id",)), ("dim_asset", ("serial_number",)),
                       ("dim_part", ("part_id",)), ("dim_technician", ("technician_id",)),
                       ("bridge_part_compatibility", ("part_id", "product_group")),
                       ("fact_service_event", ("event_id",)),
                       ("fact_parts_order", ("order_id", "order_line")),
                       ("fact_portal_event", ("event_id",)),
                       ("fact_portal_event", ("session_id", "part_id"))]:
        keys = Counter(tuple(r[k] for k in key) for r in tables[table])
        assert max(keys.values()) == 1, (table, key)


def test_service_rows_join_to_their_dimensions(tables):
    customers = {r["customer_id"] for r in tables["dim_customer"]}
    products = {r["product_id"]: r["product_group"] for r in tables["dim_product"]}
    parts = {r["part_id"] for r in tables["dim_part"]}
    assets = {r["asset_id"] for r in tables["dim_asset"]}
    events = {r["event_id"] for r in tables["fact_service_event"]}
    technicians = {r["technician_id"] for r in tables["dim_technician"]}
    groups = {r["product_group"] for r in tables["dim_product_group"]}
    sites = {r["site_id"] for r in tables["dim_site"]}
    regions = {r["region_id"] for r in tables["dim_region"]}
    for r in tables["dim_customer"]:
        assert r["region_id"] in regions
    for r in tables["dim_asset"]:
        assert r["customer_id"] in customers and products[r["product_id"]] in c.PUMP_GROUPS
    for r in tables["dim_part"]:
        assert r["sales_product_id"] in SALES_PRODUCTS
    for r in tables["bridge_part_compatibility"]:
        assert r["part_id"] in parts and r["product_group"] in groups
    for r in tables["dim_technician"]:
        assert r["home_site_id"] in sites
    for r in tables["fact_service_event"]:
        assert r["asset_id"] in assets and r["technician_id"] in technicians
    for r in tables["fact_parts_order"]:
        assert r["customer_id"] in customers and r["part_id"] in parts
        assert r["site_id"] in {"FI03", "EE02"} and r["region_id"] in regions
        assert r["service_event_id"] in events | {""} and r["asset_id"] in assets | {""}
    for r in tables["fact_portal_event"]:
        assert r["customer_id"] in customers and r["product_id"] in products
        assert r["part_id"] in parts


def test_customers_and_pumps_sit_in_the_service_area(tables, data_dir):
    with (data_dir.parent / "reference" / "geonames_towns.csv").open(encoding="utf-8") as f:
        towns = {r["name"]: r for r in csv.DictReader(f)}
    names = {v: k for k, v in c.COUNTRY_NAME.items()}
    for r in tables["dim_customer"]:
        cc = names[r["country"]]
        assert r["region_id"] == c.COUNTRY_REGION[cc]
        town = towns[r["town"]]
        assert town["country_code"] == cc
        assert (r["latitude"], r["longitude"]) == (f"{float(town['latitude']):.5f}",
                                                   f"{float(town['longitude']):.5f}")
    customer = {r["customer_id"]: r for r in tables["dim_customer"]}
    for r in tables["dim_asset"]:
        owner = customer[r["customer_id"]]
        assert owner["segment"] != "Distributor"
        assert (r["country"], r["town"]) == (owner["country"], owner["town"])
        assert abs(float(r["latitude"]) - float(owner["latitude"])) < 0.25
    assert len(tables["dim_asset"]) == c.FLEET_SIZE


def test_telemetry_has_one_row_per_pump_and_day(tables, telemetry):
    assert telemetry.strictly_ordered
    last = c.SERVICE_LAST_DAY
    for a in tables["dim_asset"]:
        start = date.fromisoformat(a["telemetry_from_date"])
        assert start == max(date.fromisoformat(a["install_date"]), c.SERVICE_FIRST_DAY)
        days = telemetry.by_asset[a["asset_id"]]
        assert len(days) == (last - start).days + 1, a["asset_id"]
        assert min(days) == start.year * 10000 + start.month * 100 + start.day
    assert telemetry.rows == sum(len(d) for d in telemetry.by_asset.values())


def test_telemetry_values_are_physical(tables, telemetry):
    """Running hours 0 to 24; vibration and temperature blank exactly when the pump
    did not run; power within the motor's rating."""
    kw = {p["product_id"]: float(p["rated_kw"]) for p in tables["dim_product"]}
    asset_kw = {a["asset_id"]: kw[a["product_id"]] for a in tables["dim_asset"]}
    for asset, days in telemetry.by_asset.items():
        for hours, vibration, temperature, power in days.values():
            assert 0 <= hours <= 24
            if hours == 0:
                assert vibration is None and temperature is None and power == 0
            else:
                assert 0.3 < vibration < 25 and -5 < temperature < 120
                assert 0 < power <= asset_kw[asset] * 1.5


def test_pumps_installed_in_the_period_came_out_of_units_sold(tables):
    sold = Counter()
    for s in tables["fact_sales"]:
        sold[(s["product_id"], s["region_id"], s["date_key"])] += int(s["units"])
    region = {r["customer_id"]: r["region_id"] for r in tables["dim_customer"]}
    installed = Counter()
    for a in tables["dim_asset"]:
        d = date.fromisoformat(a["install_date"])
        if d >= c.SERVICE_FIRST_DAY:
            installed[(a["product_id"], region[a["customer_id"]], f"{d.year}{d.month:02d}01")] += 1
    assert installed, "some pumps are installed during the period"
    for key, n in installed.items():
        assert n <= sold[key], key


def test_parts_fit_the_pumps_they_serve(tables):
    fit = fits(tables)
    group = group_of_asset(tables)
    for e in tables["fact_service_event"]:
        for item in filter(None, e["parts_used"].split(";")):
            assert (item.split(":")[0], group[e["asset_id"]]) in fit, e["event_id"]
    for r in tables["fact_parts_order"]:
        if r["asset_id"]:
            assert (r["part_id"], group[r["asset_id"]]) in fit
    product_group = {p["product_id"]: p["product_group"] for p in tables["dim_product"]}
    for r in tables["fact_portal_event"]:
        assert (r["part_id"], product_group[r["product_id"]]) in fit


def test_service_parts_appear_as_order_lines(tables):
    ordered = defaultdict(dict)
    for r in tables["fact_parts_order"]:
        if r["service_event_id"]:
            ordered[r["service_event_id"]][r["part_id"]] = int(r["quantity"])
            assert r["channel"] == "Service technician"
    used = {e["event_id"]: dict((p, int(q)) for p, q in (x.split(":") for x in e["parts_used"].split(";")))
            for e in tables["fact_service_event"] if e["parts_used"]}
    assert used == ordered


def test_parts_orders_reconcile_to_sales_in_units_and_cents(tables):
    sales = {(s["date_key"], s["site_id"], s["region_id"], s["product_id"]):
             (int(s["units"]), Decimal(s["net_sales_eur"]))
             for s in tables["fact_sales"] if s["product_id"] in SALES_PRODUCTS}
    orders = defaultdict(lambda: [0, Decimal(0)])
    for r in tables["fact_parts_order"]:
        key = (r["date_key"], r["site_id"], r["region_id"], r["sales_product_id"])
        orders[key][0] += int(r["quantity"])
        orders[key][1] += Decimal(r["net_amount_eur"])
    assert {k: tuple(v) for k, v in orders.items()} == sales


def test_orders_ship_only_from_open_warehouses_in_their_month(tables):
    for r in tables["fact_parts_order"]:
        d = date.fromisoformat(r["order_date"])
        assert r["date_key"] == f"{d.year}{d.month:02d}01"
        if r["site_id"] == "EE02":
            assert d >= date(2024, 7, 1)
        assert int(r["quantity"]) > 0 and Decimal(r["net_amount_eur"]) > 0


def test_realised_prices_stay_close_to_list(tables):
    """Each month's lines, priced at list, come within a believable price factor of
    what was invoiced (list prices are 2023's; prices rise about 3% a year)."""
    price = {p["part_id"]: Decimal(p["list_price_eur"]) for p in tables["dim_part"]}
    cell = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for r in tables["fact_parts_order"]:
        key = (r["date_key"], r["site_id"], r["region_id"], r["sales_product_id"])
        cell[key][0] += Decimal(r["net_amount_eur"])
        cell[key][1] += price[r["part_id"]] * int(r["quantity"])
    lo, hi = c.PRICE_FACTOR_RANGE
    for key, (invoiced, listed) in cell.items():
        assert lo <= invoiced / listed <= hi, key


def test_technicians_have_the_skills_and_cover_the_country(tables):
    tech = {t["technician_id"]: t for t in tables["dim_technician"]}
    group = group_of_asset(tables)
    names = {v: k for k, v in c.COUNTRY_NAME.items()}
    asset = {a["asset_id"]: a for a in tables["dim_asset"]}
    for e in tables["fact_service_event"]:
        t = tech[e["technician_id"]]
        skills = set(t["skills"].split(";"))
        assert names[asset[e["asset_id"]]["country"]] in t["countries_served"].split(";")
        assert "mechanical" in skills
        if group[e["asset_id"]] in c.WASTEWATER_GROUPS:
            assert "wastewater" in skills
        if e["failure_mode"]:
            assert SKILL[e["failure_mode"]] in skills


def test_service_events_are_consistent(tables):
    for e in tables["fact_service_event"]:
        reported, completed = date.fromisoformat(e["reported_date"]), date.fromisoformat(e["completed_date"])
        assert e["event_type"] in {"Failure", "Preventive", "Inspection"}
        assert bool(e["failure_mode"]) == (e["event_type"] == "Failure")
        assert e["technician_note"]
        if e["event_type"] == "Failure":
            assert completed >= reported and float(e["downtime_hours"]) > 0 and e["parts_used"]
        else:
            assert completed == reported
        if e["event_type"] == "Inspection":
            assert not e["parts_used"] and float(e["downtime_hours"]) == 0


def test_portal_sessions_show_five_ranked_parts_after_launch(tables):
    sessions = defaultdict(list)
    for r in tables["fact_portal_event"]:
        assert date.fromisoformat(r["event_date"]) >= c.PORTAL_FIRST_DAY
        assert r["clicked"] in {"0", "1"}
        sessions[r["session_id"]].append(int(r["rank"]))
    assert all(sorted(ranks) == list(range(1, c.PORTAL_SHOWN + 1)) for ranks in sessions.values())
    portal_orders = {r["order_id"] for r in tables["fact_parts_order"] if r["channel"] == "Portal"}
    assert all(r["order_date"] >= "2024-01-01" for r in tables["fact_parts_order"]
               if r["channel"] == "Portal")
    assert len(sessions) > len(portal_orders)   # every portal order, plus browsing
