"""Phase 3 inputs: the control and drift scenarios, and two planning costs.

Run with:  python -m fjordvik_data.scenarios --out <folder outside data/>

It writes, with the same seed as the tables:

- control/fact_asset_telemetry.csv: the warning rise switched off for every
  failure, in every sensor. Failures and service events are unchanged, so only
  the telemetry is written.
- drift_recalibration/fact_asset_telemetry.csv: some pumps' bearing temperature
  reads higher from a start day of their own, and stays higher.
- drift_unit_change/fact_asset_telemetry.csv: some pumps report vibration in
  inches per second from one day on, in the same column.
- drift_scenarios.csv: which pump changes, in which scenario, from which day.

The files are built on demand and never committed. Run from data/ with
`--record scenarios` to also write scenarios/manifest.json (their rows and
checksums) and scenarios/planning_inputs.json (the cost of a wasted visit and of
a missed failure, with their working). Without --record the files are checked
against the committed manifest instead.

Everything is synthetic. The settings are in config.py: the published rates are
labelled there with their sources, and every other value is Fjordvik's own.
"""

import argparse
import csv
import json
import math
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from fjordvik_data import config as c
from fjordvik_data import service
from fjordvik_data.generate import COLUMNS, GENERATOR_VERSION, rng_for, sha256, write_csv
from fjordvik_data.geonames import read_towns
from fjordvik_data.portfolio import DATA_ROOT

TABLES = DATA_ROOT / "tables"
RECORDED = DATA_ROOT / "scenarios"
TELEMETRY = "fact_asset_telemetry"
TELEMETRY_FILE = f"{TELEMETRY}.csv"
DRIFT_FILE = "drift_scenarios.csv"
DRIFT_COLUMNS = ["asset_id", "scenario", "start_date", "sensor", "change"]
DATASET = "Fjordvik Manufacturing Oy (synthetic)"
LEGS_IN_A_ROUND_TRIP = 2   # there and back


def read_table(name: str) -> list[dict]:
    with (TABLES / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def with_coordinates(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["latitude"], r["longitude"] = float(r["latitude"]), float(r["longitude"])
    return rows


def tables_manifest() -> dict:
    return json.loads((TABLES / "manifest.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The scenarios
# ---------------------------------------------------------------------------

def base_and_control() -> tuple[list[tuple], list[tuple]]:
    """The base telemetry, rebuilt from the committed dimensions and checked against
    the committed table, and the control: the same fleet with no warning rise."""
    customers = read_table("dim_customer")
    assets = with_coordinates(read_table("dim_asset"))
    technicians = with_coordinates(read_table("dim_technician"))
    base = service.build_fleet(assets, customers, technicians, rng_for)[0]
    control = service.build_fleet(assets, customers, technicians, rng_for, warning_rise=False)[0]
    committed = tables_manifest()["tables"][TELEMETRY]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / TELEMETRY_FILE
        write_csv(path, COLUMNS[TELEMETRY], base)
        if sha256(path) != committed["sha256"]:
            raise ValueError("the rebuilt base telemetry does not match tables/manifest.json: "
                             "regenerate the tables before building the scenarios")
    if not base or len(control) != len(base):
        raise ValueError("the control must have the base telemetry's rows")
    return base, control


def drift_pumps() -> list[dict]:
    """Which pumps drift, and from when. Each scenario has its own random stream."""
    eligible = sorted(a["asset_id"] for a in read_table("dim_asset")
                      if date.fromisoformat(a["telemetry_from_date"]) <= c.SCENARIO_TELEMETRY_FROM)
    rows = []
    s = c.DRIFT_RECALIBRATION
    rng = rng_for("scenario", "drift_recalibration")
    days = (s["last_start"] - s["first_start"]).days
    for asset in sorted(rng.sample(eligible, s["pumps"])):
        start = s["first_start"] + timedelta(days=rng.randint(0, days))
        rows.append({"asset_id": asset, "scenario": "drift_recalibration",
                     "start_date": start.isoformat(), "sensor": s["sensor"],
                     "change": f"reads {s['step']} C higher"})
    s = c.DRIFT_UNIT_CHANGE
    rng = rng_for("scenario", "drift_unit_change")
    for asset in sorted(rng.sample(eligible, s["pumps"])):
        rows.append({"asset_id": asset, "scenario": "drift_unit_change",
                     "start_date": s["start"].isoformat(), "sensor": s["sensor"],
                     "change": f"reported in inches per second (mm/s divided by {c.MM_PER_INCH})"})
    if len(rows) != c.DRIFT_RECALIBRATION["pumps"] + c.DRIFT_UNIT_CHANGE["pumps"]:
        raise ValueError("wrong number of drift pumps")
    return rows


def with_drift(base: list[tuple], drift: list[dict], scenario: str, change) -> list[tuple]:
    """The base telemetry with `change` applied to one sensor of the scenario's pumps
    from each pump's start day. A blank reading stays blank."""
    picked = [d for d in drift if d["scenario"] == scenario]
    start = {d["asset_id"]: service.day_key(date.fromisoformat(d["start_date"])) for d in picked}
    column = COLUMNS[TELEMETRY].index(picked[0]["sensor"])
    rows = []
    for row in base:
        first = start.get(row[1])
        if first is not None and row[0] >= first and row[column] is not None:
            row = row[:column] + (change(row[column]),) + row[column + 1:]
        rows.append(row)
    return rows


def write_scenarios(out_dir: Path) -> dict:
    """Write the scenario files to out_dir and return their manifest."""
    out_dir = out_dir.resolve()
    if out_dir == DATA_ROOT or DATA_ROOT in out_dir.parents:
        raise ValueError("write the scenario files outside data/: they are never committed")
    base, control = base_and_control()
    drift = drift_pumps()
    step = c.DRIFT_RECALIBRATION["step"]
    scenarios = {
        "control": control,
        "drift_recalibration": with_drift(base, drift, "drift_recalibration", lambda v: v + step),
        "drift_unit_change": with_drift(base, drift, "drift_unit_change",
                                        lambda v: v / c.MM_PER_INCH),
    }
    manifest = {
        "dataset": DATASET,
        "generator_version": GENERATOR_VERSION,
        "seed": c.SEED,
        "base": {"file": f"tables/{TELEMETRY_FILE}", "rows": len(base),
                 "sha256": tables_manifest()["tables"][TELEMETRY]["sha256"]},
        "files": {},
    }
    for name, rows in scenarios.items():
        if len(rows) != len(base):
            raise ValueError(f"{name} must have the base telemetry's rows")
        (out_dir / name).mkdir(parents=True, exist_ok=True)
        path = out_dir / name / TELEMETRY_FILE
        write_csv(path, COLUMNS[TELEMETRY], rows)
        manifest["files"][f"{name}/{TELEMETRY_FILE}"] = {"rows": len(rows), "sha256": sha256(path)}
    path = out_dir / DRIFT_FILE
    write_csv(path, DRIFT_COLUMNS, drift)
    manifest["files"][DRIFT_FILE] = {"rows": len(drift), "sha256": sha256(path)}
    return manifest


# ---------------------------------------------------------------------------
# The two planning costs
# ---------------------------------------------------------------------------

def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("no rows to average")
    return math.fsum(values) / len(values)


def technician_country() -> dict:
    """Each technician's country code: the country of their home town."""
    towns = read_towns()
    return {t[0]: towns[t[3]]["country_code"] for t in c.TECHNICIANS}


def planning_inputs() -> dict:
    """The cost of a wasted visit and of a missed failure, in euros per event, from
    the committed tables times the published rates, with the working."""
    assets = with_coordinates(read_table("dim_asset"))
    technicians = with_coordinates(read_table("dim_technician"))
    events = read_table("fact_service_event")
    by_id = {t["technician_id"]: t for t in technicians}
    country = technician_country()
    rate = c.LABOUR_COST_EUR_PER_HOUR
    group = service.group_of()

    # Wasted visit: labour for the round trip and the time on site, plus the van.
    on_site = [float(e["labour_hours"]) for e in events if e["event_type"] == "Inspection"]
    on_site_hours = mean(on_site)
    visits, by_country = [], defaultdict(list)
    for a in assets:
        needs = {c.VISIT_SKILL}
        if group[a["product_id"]] in c.WASTEWATER_GROUPS:
            needs.add("wastewater")
        t = by_id[service.nearest_technician(a, needs, technicians)]
        straight = service.km(t["latitude"], t["longitude"], a["latitude"], a["longitude"])
        road = LEGS_IN_A_ROUND_TRIP * straight * c.ROAD_DISTANCE_FACTOR
        hours = road / c.TRAVEL_SPEED_KM_PER_HOUR
        cc = country[t["technician_id"]]
        cost = rate[cc] * (hours + on_site_hours) + c.VAN_RUNNING_COST_EUR_PER_KM * road
        visits.append((straight, road, hours, cost))
        by_country[cc].append(cost)

    # Missed failure: the extra cost of the same repair unplanned.
    price = {p["part_id"]: float(p["list_price_eur"]) for p in read_table("dim_part")}
    labour, parts = [], []
    for e in events:
        if e["event_type"] != "Failure":
            continue
        labour.append(float(e["labour_hours"]) * rate[country[e["technician_id"]]])
        used = [line.split(":") for line in e["parts_used"].split(";")]
        parts.append(math.fsum(price[p] * int(q) for p, q in used))
    planned = mean([l + p for l, p in zip(labour, parts)])
    ratio = c.UNPLANNED_TO_PLANNED_COST_RATIO

    return {
        "dataset": DATASET,
        "note": ("Synthetic data. Two planning costs for the failure prediction work, worked "
                 "out from Fjordvik's own synthetic tables times published rates. They are "
                 "not real-world costs."),
        "generator_version": GENERATOR_VERSION,
        "seed": c.SEED,
        "tables_manifest_sha256": sha256(TABLES / "manifest.json"),
        "wasted_visit": {
            "cost_eur_per_event": round(mean([v[3] for v in visits]), 2),
            "formula": ("labour cost per hour x (round-trip travel hours + on-site hours) + "
                        "van running cost per km x round-trip road km, for each pump, "
                        "averaged over the fleet"),
            "working": {
                "pumps": len(visits),
                "distance": ("straight-line km from the base of the nearest qualified "
                             "technician to the pump, from dim_technician and dim_asset; "
                             "road km = straight-line km x the road-distance factor; "
                             "travel hours = road km / travel speed"),
                "mean_straight_line_km_one_way": round(mean([v[0] for v in visits]), 2),
                "mean_road_km_round_trip": round(mean([v[1] for v in visits]), 2),
                "mean_travel_hours_round_trip": round(mean([v[2] for v in visits]), 4),
                "on_site_hours": round(on_site_hours, 4),
                "on_site_hours_from": ("mean labour_hours of the Inspection events in "
                                       "fact_service_event"),
                "inspection_events": len(on_site),
                "by_technician_country": {
                    cc: {"pumps": len(costs), "labour_cost_eur_per_hour": rate[cc],
                         "mean_cost_eur": round(mean(costs), 2)}
                    for cc, costs in sorted(by_country.items())},
            },
        },
        "missed_failure": {
            "cost_eur_per_event": {k: round((r - 1) * planned, 2) for k, r in ratio.items()},
            "formula": ("(ratio - 1) x planned repair cost, averaged over the Failure events; "
                        "planned repair cost = labour_hours x labour cost per hour + the list "
                        "price of parts_used"),
            "covers": "Fjordvik's repair cost only",
            "working": {
                "failure_events": len(labour),
                "mean_planned_repair_cost_eur": round(planned, 2),
                "mean_labour_cost_eur": round(mean(labour), 2),
                "mean_parts_list_price_eur": round(mean(parts), 2),
                "ratio": ratio,
            },
        },
        "left_out": {"items": c.COSTS_LEFT_OUT,
                     "reason": "no published figure was found for either"},
        "price_basis": ("Labour at 2026 cost, the van at 2026 prices, parts at Fjordvik's "
                        "2023 list price."),
        "fjordvik_planning_inputs": {
            "travel_speed_km_per_hour": c.TRAVEL_SPEED_KM_PER_HOUR,
            "road_distance_factor": c.ROAD_DISTANCE_FACTOR,
            "labour_rate_country": c.LABOUR_RATE_COUNTRY,
            "set_by": "Fjordvik's own planning inputs, not published figures",
        },
        "published_rates": c.PUBLISHED_RATES,
    }


# ---------------------------------------------------------------------------
# Writing and checking
# ---------------------------------------------------------------------------

def write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n")


def record(folder: Path, manifest: dict) -> None:
    """Write the manifest and the planning inputs: the two files git holds."""
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "manifest.json", manifest)
    write_json(folder / "planning_inputs.json", planning_inputs())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Fjordvik phase 3 scenarios.")
    parser.add_argument("--out", required=True, type=Path,
                        help="folder outside data/ to write the scenario files to")
    parser.add_argument("--record", type=Path,
                        help="also write manifest.json and planning_inputs.json to this "
                             "folder (scenarios, from data/)")
    args = parser.parse_args()
    manifest = write_scenarios(args.out)
    for name, info in manifest["files"].items():
        print(f"{name:<44} {info['rows']:>7} rows")
    print(f"Written to {args.out.resolve()}")
    if args.record:
        record(args.record, manifest)
        print(f"Manifest and planning inputs written to {args.record.resolve()}")
    elif not (RECORDED / "manifest.json").exists():
        print("No committed manifest to check against.")
    elif json.loads((RECORDED / "manifest.json").read_text(encoding="utf-8")) != manifest:
        raise SystemExit("The scenario files do not match data/scenarios/manifest.json.")
    else:
        print("The scenario files match data/scenarios/manifest.json.")


if __name__ == "__main__":
    main()
