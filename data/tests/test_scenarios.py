"""Phase 3 inputs (added 11 November 2026): the control and drift scenarios and the
two planning costs. Adding them moved no existing file; the scenario files match
their committed manifest; and each scenario changes only what it says it changes."""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date

from fjordvik_data import config as c
from fjordvik_data.generate import GENERATOR_VERSION

TELEMETRY_FILE = "fact_asset_telemetry.csv"
SCENARIO_FILES = [f"control/{TELEMETRY_FILE}", f"drift_recalibration/{TELEMETRY_FILE}",
                  f"drift_unit_change/{TELEMETRY_FILE}", "drift_scenarios.csv"]
HOURS, VIBRATION, TEMPERATURE, POWER = 2, 3, 4, 5

# Checksums at commit d93fd1b, before the phase 3 inputs were added. The tables
# manifest holds the checksum of all 31 tables, and test_reproducible.py checks
# each table against it, so this one line pins every table (GUARDRAILS.md D5).
UNCHANGED = {
    "tables/manifest.json": "379e6075034a605fc5dac6806d5f6367079ea4dee4083180167bfbc34bfb5b68",
    "generator-truth/failures.csv": "b45dad987a7f59d3ff7c460ba478b3fb6a8880bd21aff143a087c6ca53dad8e1",
    "corpus/manifest.json": "94c403aa5fe73d63da2dbd57cb69b3e8b1937f3157b0677db3ee95ca952201cd",
    "corpus/manual-booster-sets.md": "5577c246ff918670e0d0195ba81bb6a59464893d4bc27dab39efe26a4d045416",
    "corpus/manual-control-panels.md": "f56f9fcb1097459f8f1865f380c5fc1815e1b39627ef5e7e9b26e6c28750ee13",
    "corpus/manual-drive-packages.md": "3ccb64cdccf784c2b2ab546636a49a8430a0d35bbd4281a70bc4016b3de18e3f",
    "corpus/manual-dry-installed-pumps.md": "ec530365761dd5a39f45cca6652f102bef4ac875373756355c86ca68d21f5383",
    "corpus/manual-end-suction-pumps.md": "e1afd5a3e76e4d9473e042594d573fff1368aff7e4cc40ce08fb7409403bddca",
    "corpus/manual-multistage-pumps.md": "03dee09db898633aef67263d69b7e6e0adfdcb0d56421edd408fb8cf956c9d1a",
    "corpus/manual-split-case-pumps.md": "500582218692dd59f4b3d43c18e36100ccb2c3b01a2c46bc28e1a78f1b2cce58",
    "corpus/manual-submersible-pumps.md": "57544fa3d6a4f2266757f0cd14a4d7c10e96e1f03bff6783d157049443b1f00e",
    "corpus/service-terms.md": "1ffcfb7ed8c5fe3437043b38520b1e3901635461e0b93dd9acc1be428cd974cb",
    "corpus/warranty-policy.md": "647c341dc9fc6bd41dc5765ad4820af8b99c2ebac7a9389e6865afa98b03093b",
}


def digest(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(day: str) -> int:
    return int(day.replace("-", ""))


def rows_of(path):
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        yield from reader


def changed_rows(data_dir, scenario_folder):
    """Each (base row, scenario row) pair that differs. The two files must have the
    same pump and day on every line, and the same running hours."""
    pairs = zip(rows_of(data_dir / TELEMETRY_FILE), rows_of(scenario_folder / TELEMETRY_FILE),
                strict=True)
    for base, other in pairs:
        assert base[:HOURS + 1] == other[:HOURS + 1]
        if base != other:
            yield base, other


def drift(scenario_files, scenario: str) -> dict:
    with (scenario_files[0] / "drift_scenarios.csv").open(encoding="utf-8", newline="") as f:
        return {r["asset_id"]: r for r in csv.DictReader(f) if r["scenario"] == scenario}


def test_phase3_inputs_left_every_existing_file_unchanged(data_dir):
    """The tables, their manifest, the manuals and the answer key are byte for byte
    what they were at commit d93fd1b: nothing phase 2 pinned has moved."""
    root = data_dir.parent
    for name, before in UNCHANGED.items():
        assert digest(root / name) == before, name
    for folder in ("corpus", "generator-truth"):
        found = {p.relative_to(root).as_posix() for p in (root / folder).rglob("*") if p.is_file()}
        assert found == {name for name in UNCHANGED if name.startswith(folder)}, folder
    assert GENERATOR_VERSION == "1.4.0"


def test_scenario_files_match_the_committed_manifest(scenario_files, data_dir):
    manifest = json.loads((data_dir.parent / "scenarios" / "manifest.json").read_text(encoding="utf-8"))
    tables = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == c.SEED == tables["seed"]
    assert manifest["generator_version"] == GENERATOR_VERSION == tables["generator_version"]
    assert manifest["base"]["sha256"] == tables["tables"]["fact_asset_telemetry"]["sha256"]
    assert manifest["base"]["rows"] == tables["tables"]["fact_asset_telemetry"]["rows"]
    assert list(manifest["files"]) == SCENARIO_FILES
    for name, info in manifest["files"].items():
        path = scenario_files[0] / name
        assert digest(path) == info["sha256"], name
        assert sum(1 for _ in rows_of(path)) == info["rows"], name


def test_manifest_and_planning_inputs_rebuild_byte_identical(scenario_files, data_dir):
    """The two committed files are exactly what the module writes (GUARDRAILS.md D3)."""
    committed = data_dir.parent / "scenarios"
    assert sorted(p.name for p in committed.iterdir()) == ["manifest.json", "planning_inputs.json"]
    for name in ("manifest.json", "planning_inputs.json"):
        assert (scenario_files[1] / name).read_bytes() == (committed / name).read_bytes(), name


def test_control_differs_from_the_base_only_inside_warning_windows(scenario_files, data_dir):
    """Phase rule E2: with the warning rise off, the readings change on the days a
    warning was building and nowhere else, and they do change before every warned
    failure. Running hours, and so the days a pump was down, never change."""
    with (data_dir.parent / "generator-truth" / "failures.csv").open(encoding="utf-8") as f:
        truth = list(csv.DictReader(f))
    windows = defaultdict(list)
    for t in truth:
        if t["warned"] == "1":
            windows[t["asset_id"]].append(
                (key(t["warning_start_date"]), key(t["failure_date"]), t["event_id"]))
    warned = {w[2] for found in windows.values() for w in found}
    assert warned and len(warned) < len(truth)
    differ = set()
    for base, _control in changed_rows(data_dir, scenario_files[0] / "control"):
        inside = [w[2] for w in windows[base[1]] if w[0] <= int(base[0]) <= w[1]]
        assert inside, f"{base[1]} differs on {base[0]}, outside any warning window"
        differ.update(inside)
    assert differ == warned


def test_recalibration_changes_only_the_named_pumps_from_their_start(scenario_files, data_dir):
    """Phase rule M5: bearing temperature reads the step higher at the named pumps on
    every running day from each pump's own start day, and nothing else changes."""
    setting = c.DRIFT_RECALIBRATION
    named = drift(scenario_files, "drift_recalibration")
    start = {a: key(r["start_date"]) for a, r in named.items()}
    changed = Counter()
    for base, other in changed_rows(data_dir, scenario_files[0] / "drift_recalibration"):
        day, asset = int(base[0]), base[1]
        assert asset in start and day >= start[asset], (asset, day)
        assert (base[VIBRATION], base[POWER]) == (other[VIBRATION], other[POWER])
        assert float(other[TEMPERATURE]) == round(float(base[TEMPERATURE]) + setting["step"], 1)
        changed[asset] += 1
    running = Counter(r[1] for r in rows_of(data_dir / TELEMETRY_FILE)
                      if r[1] in start and int(r[0]) >= start[r[1]] and r[TEMPERATURE])
    assert changed == running and len(changed) == setting["pumps"]


def test_unit_change_changes_only_the_named_pumps_from_its_start(scenario_files, data_dir):
    """Phase rule M5: vibration is in inches per second at the named pumps on every
    running day from the start day, in the same column, and nothing else changes."""
    setting = c.DRIFT_UNIT_CHANGE
    named = drift(scenario_files, "drift_unit_change")
    first = key(setting["start"].isoformat())
    changed = Counter()
    for base, other in changed_rows(data_dir, scenario_files[0] / "drift_unit_change"):
        assert base[1] in named and int(base[0]) >= first, (base[1], base[0])
        assert (base[TEMPERATURE], base[POWER]) == (other[TEMPERATURE], other[POWER])
        assert float(other[VIBRATION]) == round(float(base[VIBRATION]) / c.MM_PER_INCH, 2)
        changed[base[1]] += 1
    running = Counter(r[1] for r in rows_of(data_dir / TELEMETRY_FILE)
                      if r[1] in named and int(r[0]) >= first and r[VIBRATION])
    assert changed == running and len(changed) == setting["pumps"]


def test_drift_scenarios_list_pumps_that_have_reported_long_enough(scenario_files, tables):
    reporting_from = {a["asset_id"]: date.fromisoformat(a["telemetry_from_date"])
                      for a in tables["dim_asset"]}
    with (scenario_files[0] / "drift_scenarios.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["asset_id", "scenario", "start_date", "sensor", "change"]
        listed = list(reader)
    assert len({(r["asset_id"], r["scenario"]) for r in listed}) == len(listed)
    for r in listed:
        assert reporting_from[r["asset_id"]] <= c.SCENARIO_TELEMETRY_FROM
    recalibrated = drift(scenario_files, "drift_recalibration")
    setting = c.DRIFT_RECALIBRATION
    assert len(recalibrated) == setting["pumps"]
    for r in recalibrated.values():
        assert setting["first_start"] <= date.fromisoformat(r["start_date"]) <= setting["last_start"]
        assert r["sensor"] == setting["sensor"] == "bearing_temp_c"
    assert len({r["start_date"] for r in recalibrated.values()}) > 1   # each pump its own day
    converted = drift(scenario_files, "drift_unit_change")
    setting = c.DRIFT_UNIT_CHANGE
    assert len(converted) == setting["pumps"]
    for r in converted.values():
        assert r["start_date"] == setting["start"].isoformat()
        assert r["sensor"] == setting["sensor"] == "vibration_mm_s"


def test_planning_costs_match_an_independent_recomputation(tables, data_dir):
    """The two costs, worked out again here from the committed tables: its own
    distance formula, and each technician's country looked up by home town name."""
    inputs = json.loads((data_dir.parent / "scenarios" / "planning_inputs.json")
                        .read_text(encoding="utf-8"))
    rate, van = c.LABOUR_COST_EUR_PER_HOUR, c.VAN_RUNNING_COST_EUR_PER_KM
    with (data_dir.parent / "reference" / "geonames_towns.csv").open(encoding="utf-8") as f:
        town_country = {t["name"]: t["country_code"] for t in csv.DictReader(f)}
    technicians = tables["dim_technician"]
    country = {t["technician_id"]: town_country[t["home_town"]] for t in technicians}
    assert set(country.values()) == set(rate)   # a rate for each country, and each one used
    code = {name: cc for cc, name in c.COUNTRY_NAME.items()}
    group = {p["product_id"]: p["product_group"] for p in tables["dim_product"]}

    def distance(a, b) -> float:
        lat1, lon1, lat2, lon2 = (math.radians(float(x)) for x in (
            a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
        # spherical law of cosines, Earth radius 6,371 km
        return 6371.0 * math.acos(min(1.0, math.sin(lat1) * math.sin(lat2)
                                      + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)))

    inspections = [float(e["labour_hours"]) for e in tables["fact_service_event"]
                   if e["event_type"] == "Inspection"]
    on_site = sum(inspections) / len(inspections)
    costs = []
    for a in tables["dim_asset"]:
        skills = {"mechanical", "wastewater"} if group[a["product_id"]] == "Submersible pumps" \
            else {"mechanical"}
        able = [t for t in technicians if code[a["country"]] in t["countries_served"].split(";")
                and skills <= set(t["skills"].split(";"))]
        nearest = min(able, key=lambda t: (distance(t, a), t["technician_id"]))
        road = 2 * distance(nearest, a) * c.ROAD_DISTANCE_FACTOR
        costs.append(rate[country[nearest["technician_id"]]]
                     * (road / c.TRAVEL_SPEED_KM_PER_HOUR + on_site) + van * road)
    wasted = inputs["wasted_visit"]
    assert abs(wasted["cost_eur_per_event"] - sum(costs) / len(costs)) < 0.01
    assert wasted["working"]["pumps"] == len(costs) == c.FLEET_SIZE
    assert wasted["working"]["inspection_events"] == len(inspections)

    price = {p["part_id"]: float(p["list_price_eur"]) for p in tables["dim_part"]}
    planned = []
    for e in tables["fact_service_event"]:
        if e["event_type"] == "Failure":
            parts = sum(price[p] * int(q) for p, q in
                        (line.split(":") for line in e["parts_used"].split(";")))
            planned.append(float(e["labour_hours"]) * rate[country[e["technician_id"]]] + parts)
    mean_planned = sum(planned) / len(planned)
    missed = inputs["missed_failure"]
    assert missed["working"]["failure_events"] == len(planned)
    assert set(missed["cost_eur_per_event"]) == {"low", "central", "high"}
    for level, ratio in c.UNPLANNED_TO_PLANNED_COST_RATIO.items():
        assert abs(missed["cost_eur_per_event"][level] - (ratio - 1) * mean_planned) < 0.01
    low, central, high = (missed["cost_eur_per_event"][k] for k in ("low", "central", "high"))
    assert 0 < low < central < high


def test_planning_inputs_say_where_every_figure_comes_from(data_dir):
    """Every rate is either a published one with its source and dates, or one of
    Fjordvik's own planning inputs, and the file says what the costs leave out."""
    inputs = json.loads((data_dir.parent / "scenarios" / "planning_inputs.json")
                        .read_text(encoding="utf-8"))
    assert "synthetic" in inputs["dataset"].lower() and "Synthetic" in inputs["note"]
    assert inputs["published_rates"] == json.loads(json.dumps(c.PUBLISHED_RATES))
    for name, published in inputs["published_rates"].items():
        assert published["unit"] and published["read"] == "2026-11-11", name
        assert published["sources"], name
        for source in published["sources"]:
            assert source["description"].startswith("Published ") and source["published"], name
    own = inputs["fjordvik_planning_inputs"]
    assert own["travel_speed_km_per_hour"] == c.TRAVEL_SPEED_KM_PER_HOUR
    assert own["road_distance_factor"] == c.ROAD_DISTANCE_FACTOR
    assert "not published" in own["set_by"]
    assert inputs["left_out"]["items"] == c.COSTS_LEFT_OUT == [
        "the customer's downtime cost", "expedited parts"]
    assert inputs["missed_failure"]["covers"] == "Fjordvik's repair cost only"
    assert inputs["tables_manifest_sha256"] == digest(data_dir / "manifest.json")


def test_every_scenario_file_is_under_50_mb(scenario_files):
    for name in SCENARIO_FILES:
        assert (scenario_files[0] / name).stat().st_size < 50 * 1024 * 1024, name
