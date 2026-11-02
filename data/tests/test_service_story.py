"""The after-sales story shows in the data: warnings before most failures and none
before some, seasons in running hours, wear with age, and the patterns the parts
forecast and the recommender are meant to find (added 2 November 2026).

The answer key in generator-truth/ says which failures were planted with a
warning; the tests check the readings carry it, from the telemetry alone."""

import csv
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta

import pytest

from fjordvik_data import config as c


@pytest.fixture(scope="module")
def answer_key(data_dir):
    with (data_dir.parent / "generator-truth" / "failures.csv").open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def mean_reading(days: dict, end: date, first: int, last: int, column: int):
    """Mean of one reading over the days `first` to `last - 1` before `end`."""
    values = [days.get(key(end - timedelta(days=i))) for i in range(first, last)]
    values = [v[column] for v in values if v and v[column] is not None]
    return statistics.mean(values) if values else None


def late_against_baseline(telemetry, answer_key, column: int):
    """For failures from April 2023 (so a baseline exists): the reading over the 3
    days before failure against the same reading 60 to 90 days before."""
    out = defaultdict(list)
    for t in answer_key:
        failed = date.fromisoformat(t["failure_date"])
        if failed < date(2023, 4, 1):
            continue
        days = telemetry.by_asset[t["asset_id"]]
        late, base = mean_reading(days, failed, 1, 4, column), mean_reading(days, failed, 60, 90, column)
        if late is not None and base is not None:
            out[(t["signal"], t["warned"])].append((late, base))
    return out


def test_answer_key_matches_the_failure_events(tables, answer_key):
    failures = {e["event_id"]: e for e in tables["fact_service_event"] if e["event_type"] == "Failure"}
    assert {t["event_id"] for t in answer_key} == set(failures)
    for t in answer_key:
        e = failures[t["event_id"]]
        assert (t["asset_id"], t["failure_date"], t["failure_mode"]) == (
            e["asset_id"], e["reported_date"], e["failure_mode"])
        if t["warned"] == "1":
            assert 0 < int(t["warning_days"]) <= c.WARNING_DAYS[1]


def test_most_failures_give_warning_and_some_none(answer_key):
    warned = sum(t["warned"] == "1" for t in answer_key) / len(answer_key)
    assert 0.60 <= warned <= 0.85, warned          # most failures warn ...
    assert 1 - warned >= 0.15                      # ... but no model can catch them all
    unwarned_modes = {t["failure_mode"] for t in answer_key if t["warned"] == "0"}
    assert "Electrical trip" in unwarned_modes and "Mechanical seal leak" in unwarned_modes


def test_vibration_rises_before_warned_vibration_faults(telemetry, answer_key):
    pairs = late_against_baseline(telemetry, answer_key, column=1)
    rising = [p for (signal, warned), v in pairs.items() if warned == "1" and "vibration" in signal
              for p in v]
    assert len(rising) >= 100
    assert sum(late > 1.3 * base for late, base in rising) / len(rising) >= 0.9
    silent = pairs[("none", "0")]
    assert len(silent) >= 50
    assert statistics.median(late / base for late, base in silent) < 1.1


def test_temperature_rises_before_warned_temperature_faults(telemetry, answer_key):
    pairs = late_against_baseline(telemetry, answer_key, column=2)
    rising = [p for (signal, warned), v in pairs.items() if warned == "1" and "temp" in signal
              for p in v]
    assert len(rising) >= 30
    assert sum(late - base > 4 for late, base in rising) / len(rising) >= 0.8
    silent = pairs[("none", "0")]
    assert statistics.median(late - base for late, base in silent) < 2


def test_stopped_pumps_report_no_running_hours(tables, telemetry):
    for e in tables["fact_service_event"]:
        if e["event_type"] != "Failure":
            continue
        days = telemetry.by_asset[e["asset_id"]]
        d = date.fromisoformat(e["reported_date"]) + timedelta(days=1)
        while d <= date.fromisoformat(e["completed_date"]):
            assert days[key(d)][0] == 0, (e["event_id"], d)
            d += timedelta(days=1)


def test_running_hours_follow_the_seasons(tables, telemetry):
    profile = {a[0]: a[3] for apps in c.APPLICATIONS.values() for a in apps}
    hours = defaultdict(list)
    for a in tables["dim_asset"]:
        p = profile[a["application"]]
        for day, reading in telemetry.by_asset[a["asset_id"]].items():
            hours[(p, day // 100 % 100)].append(reading[0])
    mean = {k: statistics.mean(v) for k, v in hours.items()}
    # spring melt for wastewater; heating in winter; the July shutdown for process plants
    assert (mean[("wastewater", 4)] + mean[("wastewater", 5)]) > 1.25 * (
        mean[("wastewater", 1)] + mean[("wastewater", 2)])
    assert mean[("heating", 1)] > 2 * mean[("heating", 7)]
    assert mean[("process", 7)] < 0.6 * mean[("process", 6)]


def test_older_pumps_fail_more_often(tables, answer_key):
    failures = Counter(t["asset_id"] for t in answer_key)
    rate = defaultdict(lambda: [0, 0])
    for a in tables["dim_asset"]:
        installed = date.fromisoformat(a["install_date"])
        if installed >= c.SERVICE_FIRST_DAY:
            continue
        age = (date(2024, 7, 1) - installed).days / 365.25
        band = "young" if age < 5 else "old" if age >= 10 else "middle"
        rate[band][0] += failures[a["asset_id"]]
        rate[band][1] += 3        # three years of readings each
    assert rate["old"][0] / rate["old"][1] > rate["young"][0] / rate["young"][1]


def test_bearings_and_impellers_follow_the_fleet_running_hours(tables, telemetry):
    """The phase 2 drivers: in Oulu's Nordic stock orders, the share of bearings and
    impellers moves with the Nordic fleet's running hours (monthly correlation)."""
    family = {p["part_id"]: p["part_family"] for p in tables["dim_part"]}
    units = defaultdict(Counter)
    for r in tables["fact_parts_order"]:
        if r["site_id"] == "FI03" and r["region_id"] == "NOR" and not r["service_event_id"]:
            units[int(r["date_key"])][family[r["part_id"]]] += int(r["quantity"])
    nordic = {a["asset_id"] for a in tables["dim_asset"] if a["country"] in {"Finland", "Sweden"}}
    hours, days = defaultdict(float), defaultdict(set)
    for asset in nordic:
        for day, reading in telemetry.by_asset[asset].items():
            hours[day // 100 * 100 + 1] += reading[0]
            days[day // 100 * 100 + 1].add(day)
    months = sorted(units)
    per_day = [hours[m] / len(days[m]) for m in months]
    for fam in ("Bearings", "Impellers"):
        share = [units[m][fam] / sum(units[m].values()) for m in months]
        assert statistics.correlation(per_day, share) > 0.2, fam


def test_customers_with_a_bearing_job_also_buy_grease(tables):
    baskets = defaultdict(set)
    for r in tables["fact_parts_order"]:
        baskets[r["order_id"]].add(r["part_id"])
    grease = sum("CN-GR-01" in b for b in baskets.values()) / len(baskets)
    bearing = [b for b in baskets.values() if any(p.startswith("BR-") for p in b)]
    assert sum("CN-GR-01" in b for b in bearing) / len(bearing) > 2 * grease


def test_portal_clicks_go_to_parts_the_customer_then_orders(tables):
    ordered = defaultdict(list)
    for r in tables["fact_parts_order"]:
        ordered[(r["customer_id"], r["part_id"])].append(date.fromisoformat(r["order_date"]))
    clicks = defaultdict(lambda: [0, 0])
    for r in tables["fact_portal_event"]:
        d = date.fromisoformat(r["event_date"])
        soon = any(d <= when <= d + timedelta(days=30) for when in ordered[(r["customer_id"], r["part_id"])])
        clicks[soon][0] += int(r["clicked"])
        clicks[soon][1] += 1
    assert clicks[True][0] / clicks[True][1] > 3 * clicks[False][0] / clicks[False][1]
