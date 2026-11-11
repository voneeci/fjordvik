"""After-sales service: customers, connected pumps, daily telemetry, failures, service
events, parts orders and parts portal events.

The fleet is simulated pump by pump, each on its own random stream:
1. a planned day of running hours (duty, season, weekends);
2. failures drawn from a hazard that rises with age, running hours and wear since
   the last overhaul, with preventive visits and inspections in between;
3. the sensor readings, with a warning rise before most failures and none before
   some, so no model can be perfect.

Parts orders are then built by splitting each fact_sales row for spare parts and
service kits into order lines, so they reconcile to it in units and to the cent:
first the parts the service events used, then stock orders from the wider
installed base, whose mix follows the fleet's running hours and age. Nothing in
fact_sales changes. An answer key of every failure's warning goes outside tables/,
for evaluation only.
"""

import math
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fjordvik_data import config as c
from fjordvik_data.geonames import read_towns
from fjordvik_data.portfolio import cents

SALES_PRODUCTS = ("SPS-SP-100", "SPS-SK-200")
TRUTH_COLUMNS = ["event_id", "asset_id", "failure_date", "failure_mode", "warned",
                 "warning_start_date", "warning_days", "signal"]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def all_days() -> list[date]:
    n = (c.SERVICE_LAST_DAY - c.SERVICE_FIRST_DAY).days + 1
    return [c.SERVICE_FIRST_DAY + timedelta(days=i) for i in range(n)]


def day_key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def month_key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + 1


def years_between(start: date, end: date) -> float:
    return (end - start).days / 365.25


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres (haversine, Earth radius 6,371 km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def weighted(rng: random.Random, options: dict):
    keys = list(options)
    return rng.choices(keys, [options[k] for k in keys])[0]


def warehouse_open(site: str, month: int) -> bool:
    first = next(f for s, _n, _co, _t, f in c.SITES if s == site)
    return month >= month_key(first)


def service_warehouse(region: str, month: int) -> str:
    site = c.REGION_WAREHOUSE[region]
    return site if warehouse_open(site, month) else "FI03"


def group_of() -> dict:
    return {p[0]: p[2] for p in c.PRODUCTS}


def rated_kw() -> dict:
    return {p[0]: p[4] for p in c.PRODUCTS}


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

def build_dim_customer(rng_for, towns: dict) -> list[dict]:
    rng = rng_for("customers")
    places = [gid for ids in c.SERVICE_TOWNS.values() for gid in ids]
    rows, used = [], set()
    for segment, count, contracts in c.CUSTOMER_SEGMENTS:
        # Distributors sit in the big towns; end customers spread more evenly.
        power = 1.0 if segment == "Distributor" else 0.5
        weights = [int(towns[g]["population"]) ** power for g in places]
        for _ in range(count):
            town = towns[rng.choices(places, weights)[0]]
            cc = town["country_code"]
            while True:
                name = (f"{rng.choice(c.NAME_STEMS)} {rng.choice(c.NAME_SUFFIX[segment])} "
                        f"{c.COMPANY_FORM[cc]}")
                if name not in used:
                    used.add(name)
                    break
            since = date(rng.randint(2005, 2022), rng.randint(1, 12), 1)
            rows.append({"customer_name": name, "segment": segment,
                         "country": c.COUNTRY_NAME[cc], "region_id": c.COUNTRY_REGION[cc],
                         "town": town["name"], "latitude": float(town["latitude"]),
                         "longitude": float(town["longitude"]),
                         "service_contract": weighted(rng, contracts),
                         "customer_since": since.isoformat(), "_cc": cc})
    for i, r in enumerate(rows, 1):
        r["customer_id"] = f"C{i:04d}"
    return rows


def build_dim_asset(customers: list[dict], fact_sales: list[dict], rng_for) -> list[dict]:
    """The connected fleet. Pumps installed in the period come out of the units
    fact_sales records for that product, region and month, never more."""
    rng = rng_for("assets")
    owners = [cu for cu in customers if cu["segment"] != "Distributor"]
    owner_weights = [c.SEGMENT_FLEET_WEIGHT[cu["segment"]] for cu in owners]
    models = defaultdict(dict)
    for p in c.PRODUCTS:
        if p[2] in c.PUMP_GROUPS:
            models[p[2]][p[0]] = p[9]
    capacity = defaultdict(int)
    for s in fact_sales:
        if s["product_id"] in models.get(group_of()[s["product_id"]], {}):
            capacity[(s["product_id"], s["region_id"], int(s["date_key"]))] += int(s["units"])
    rows, serials = [], set()
    for i in range(1, c.FLEET_SIZE + 1):
        cu = rng.choices(owners, owner_weights)[0]
        group = weighted(rng, c.SEGMENT_GROUPS[cu["segment"]])
        product = weighted(rng, models[group])
        apps = [a for a in c.APPLICATIONS[group]
                if c.APPLICATION_SEGMENT.get(a[0], cu["segment"]) == cu["segment"]]
        application = rng.choice(apps)[0]
        if rng.random() < c.NEW_INSTALL_SHARE:
            months = {m: n for (p, r, m), n in capacity.items()
                      if p == product and r == cu["region_id"] and n > 0}
            month = weighted(rng, months)
            capacity[(product, cu["region_id"], month)] -= 1
            first = date(month // 10000, month // 100 % 100, 1)
            installed = first + timedelta(days=rng.randint(0, 27))
        else:
            year = min(2022, c.OLDEST_INSTALL_YEAR + int(rng.triangular(0, 11, 9)))
            installed = date(year, rng.randint(1, 12), rng.randint(1, 28))
        while True:
            serial = f"FJV{installed.year % 100:02d}{rng.randint(0, 999999):06d}"
            if serial not in serials:
                serials.add(serial)
                break
        lat = cu["latitude"] + rng.gauss(0, c.ASSET_JITTER_DEGREES)
        lon = cu["longitude"] + rng.gauss(0, c.ASSET_JITTER_DEGREES) / math.cos(math.radians(lat))
        rows.append({"asset_id": f"A{i:04d}", "serial_number": serial, "product_id": product,
                     "customer_id": cu["customer_id"], "country": cu["country"],
                     "town": cu["town"], "latitude": round(lat, 5), "longitude": round(lon, 5),
                     "application": application, "install_date": installed.isoformat(),
                     "telemetry_from_date": max(installed, c.SERVICE_FIRST_DAY).isoformat()})
    return rows


def build_dim_part() -> list[dict]:
    return [{"part_id": p, "part_name": n, "part_family": fam, "sales_product_id": sp,
             "list_price_eur": price, "lead_time_days": lead}
            for p, n, fam, sp, price, lead, _fits in c.PARTS]


def build_bridge_part_compatibility() -> list[dict]:
    return [{"part_id": p[0], "product_group": g} for p in c.PARTS for g in p[6]]


def build_dim_technician(towns: dict) -> list[dict]:
    return [{"technician_id": t, "technician_name": n, "home_site_id": site,
             "home_town": towns[home]["name"], "latitude": float(towns[home]["latitude"]),
             "longitude": float(towns[home]["longitude"]), "countries_served": served,
             "skills": skills, "weekly_hours": hours}
            for t, n, site, home, served, skills, hours in c.TECHNICIANS]


# ---------------------------------------------------------------------------
# Parts that fit a job
# ---------------------------------------------------------------------------

def fitting_parts(selector: str, group: str) -> list[tuple]:
    fits = [p for p in c.PARTS if group in p[6]]
    by_family = [p for p in fits if p[2] == selector]
    return by_family or [p for p in fits if p[0].startswith(selector + "-")]


def pick_part(selector: str, group: str, kw: int | None, rng: random.Random) -> tuple | None:
    parts = fitting_parts(selector, group)
    if not parts:
        return None
    if selector == "Impellers" and len(parts) > 1:
        large = kw is not None and kw >= c.IMPELLER_LARGE_FROM_KW.get(group, 10 ** 6)
        sized = [p for p in parts if p[0].endswith("L1") == large]
        if kw is not None and sized:
            return sized[0]
    return parts[rng.randrange(len(parts))]


def job_lines(spec: list, group: str, kw: int | None, rng: random.Random,
              factor: int = 1) -> list[tuple[str, int]]:
    lines = {}
    for selector, (lo, hi) in spec:
        part = pick_part(selector, group, kw, rng)
        qty = rng.randint(lo, hi) * factor
        if part and qty:
            lines[part[0]] = lines.get(part[0], 0) + qty
    return list(lines.items())


# ---------------------------------------------------------------------------
# The fleet, pump by pump
# ---------------------------------------------------------------------------

def nearest_technician(asset: dict, needs: set, technicians: list[dict]) -> str:
    cc = next(k for k, v in c.COUNTRY_NAME.items() if v == asset["country"])
    able = [t for t in technicians
            if cc in t["countries_served"].split(";") and needs <= set(t["skills"].split(";"))]
    return min(able, key=lambda t: (km(t["latitude"], t["longitude"], asset["latitude"],
                                       asset["longitude"]), t["technician_id"]))["technician_id"]


def surroundings(group: str, d: date) -> float:
    mean, swing = c.SURROUNDINGS["submerged" if group == "Submersible pumps" else "pump room"]
    return mean - swing * math.cos(2 * math.pi * (d.timetuple().tm_yday - 15) / 365.25)


def simulate_asset(asset: dict, contract: str, technicians: list[dict], days: list[date],
                   rng_for, warning_rise: bool = True) -> tuple[list[tuple], list[dict], list[dict]]:
    """Telemetry rows, service events and answer-key rows for one pump. With
    warning_rise off (the control scenario) no sensor rises before any failure;
    every random draw is still made, so the pump's stream stays in step."""
    rng = rng_for(asset["asset_id"], "fleet")
    product = asset["product_id"]
    group, kw = group_of()[product], rated_kw()[product]
    app = next(a for a in c.APPLICATIONS[group] if a[0] == asset["application"])
    _name, hours_a_day, load, profile = app
    profile_by_month = c.SEASON_PROFILES[profile]
    installed = date.fromisoformat(asset["install_date"])
    start = date.fromisoformat(asset["telemetry_from_date"])
    span = days[(start - days[0]).days:]
    personal_hours = max(0.5, rng.gauss(1.0, 0.1))
    personal_vibration = rng.lognormvariate(0, 0.12)
    base_vibration, temp_rise = c.SENSOR_BASELINE[group]
    typical = hours_a_day * personal_hours

    # 1. Planned running hours.
    planned = []
    for d in span:
        h = typical * profile_by_month[d.month - 1] * rng.gauss(1.0, c.RUNNING_HOURS_NOISE)
        if d.weekday() >= 5:
            h *= c.WEEKEND_FACTOR.get(profile, 1.0)
        planned.append(min(24.0, max(0.0, h)))

    # 2. Visits and failures.
    visits = {}
    per_year = c.PREVENTIVE_VISITS_PER_YEAR[contract]
    if per_year:
        interval = 365.25 / per_year
        t = rng.uniform(0, interval)
        while t < len(span):
            i = min(len(span) - 1, max(0, int(t + rng.uniform(-10, 10))))
            while span[i].weekday() >= 5 and i + 1 < len(span):
                i += 1
            visits[i] = "Preventive"
            t += interval
    for i, d in enumerate(span):
        if d.weekday() < 5 and i not in visits and rng.random() < c.INSPECTIONS_PER_YEAR / 260:
            visits[i] = "Inspection"
    modes = {m: v[0] for m, v in c.FAILURE_MODES.items()
             if group in c.MODE_GROUPS.get(m, {group})}
    wear = 0.0 if installed >= c.SERVICE_FIRST_DAY else rng.uniform(0.0, 3.0)
    wear_by_day, failures, events = [], [], []
    down_until = -1
    i = 0
    while i < len(span):
        d = span[i]
        if i <= down_until:
            wear_by_day.append(0.0)
            i += 1
            continue
        if i in visits:
            kind = visits[i]
            if kind == "Preventive":
                wear *= c.PREVENTIVE_WEAR_KEPT
            events.append({"i": i, "type": kind, "labour": round(rng.uniform(*c.LABOUR_HOURS[kind]), 1)})
        age = years_between(installed, d)
        hazard = (c.FAILURE_RATE_PER_YEAR[group] / 365.25 * (1 + c.AGE_HAZARD_PER_YEAR * age)
                  * (1 + c.WEAR_HAZARD_PER_YEAR * wear) * planned[i] / typical)
        wear_by_day.append(wear)
        if rng.random() < hazard:
            mode = weighted(rng, modes)
            _share, warn_chance, signal, _mult, _skill = c.FAILURE_MODES[mode]
            warned = rng.random() < warn_chance
            lead = rng.randint(*c.WARNING_DAYS) if warned else 0
            repair_spec = c.REPAIR_PARTS[mode]
            parts = job_lines(repair_spec, group, kw, rng)
            if not parts:
                raise ValueError(f"no part fits a {mode} repair on {group}")
            main = next(p for p in c.PARTS if p[0] == parts[0][0])
            if rng.random() < c.PART_IN_STOCK_CHANCE:
                repair_days = rng.randint(*c.REPAIR_DAYS_IN_STOCK)
            else:
                repair_days = main[5] + rng.randint(0, 3)
            ran_share = rng.uniform(0.2, 0.8)
            end = min(len(span) - 1, i + repair_days)
            failures.append({"i": i, "mode": mode, "warned": warned, "lead": lead,
                             "signal": signal if warned else "none", "end": end,
                             "ran_share": ran_share})
            events.append({"i": i, "type": "Failure", "mode": mode, "parts": parts,
                           "end": end, "labour": round(rng.uniform(*c.LABOUR_HOURS["Failure"]), 1),
                           "downtime": round(24 * (end - i) + 24 * (1 - ran_share), 1)})
            down_until = end
            wear = 0.0
        wear += 1 / 365.25
        i += 1

    # 3. Sensor readings, with the warning rise before warned failures.
    rise = [None] * len(span)    # (progress 0..1, signal, vibration multiplier)
    last_end = -1
    for f in failures:
        if f["warned"]:
            first = max(last_end + 1, f["i"] - f["lead"])
            for j in range(first, f["i"] + 1):
                rise[j] = (((j - (f["i"] - f["lead"])) / f["lead"]) ** 2, f["signal"],
                           c.FAILURE_MODES[f["mode"]][3])
            f["first"] = first
        last_end = f["end"]
    status = ["run"] * len(span)
    for f in failures:
        status[f["i"]] = "failed"
        for j in range(f["i"] + 1, f["end"] + 1):
            status[j] = "down"
    visit_hours = {e["i"]: e["labour"] for e in events if e["type"] == "Preventive"}
    rows = []
    for i, d in enumerate(span):
        hours = planned[i]
        if status[i] == "down":
            hours = 0.0
        elif status[i] == "failed":
            hours *= next(f["ran_share"] for f in failures if f["i"] == i)
        hours = max(0.0, hours - visit_hours.get(i, 0.0))
        p, signal, mult = (rise[i] if warning_rise else None) or (0.0, "none", 1.0)
        age = years_between(installed, d)
        vib_noise = c.VIBRATION_NOISE * (1 + 2 * p if signal == "vibration" else 1)
        vibration = (base_vibration * personal_vibration * (1 + c.VIBRATION_AGE_GROWTH * age)
                     * (1 + 0.10 * wear_by_day[i]) * (1 + (mult - 1) * p)
                     * max(0.5, rng.gauss(1.0, vib_noise)))
        # Start-up transients on healthy days only; both numbers are drawn every day so
        # the stream stays aligned whatever the outcome.
        transient, spike = rng.random() < c.TRANSIENT_CHANCE, rng.uniform(*c.TRANSIENT_FACTOR)
        if transient and p == 0:
            vibration *= spike
        temperature = (surroundings(group, d) + temp_rise * load / 0.65
                       + c.TEMP_RISE_AT_FAILURE.get(signal, 0.0) * p
                       + rng.gauss(0, c.TEMPERATURE_NOISE))
        power = (kw * load * (1 + c.POWER_CHANGE_AT_FAILURE.get(signal, 0.0) * p)
                 * rng.gauss(1.0, c.POWER_NOISE))
        hours = round(hours, 1)
        if hours == 0:
            rows.append((day_key(d), asset["asset_id"], 0.0, None, None, 0.0))
        else:
            rows.append((day_key(d), asset["asset_id"], hours, round(vibration, 2),
                         round(temperature, 1), round(power, 1)))

    # Service events with technician, parts and note; answer-key rows.
    service, truth = [], []
    for e in sorted(events, key=lambda e: e["i"]):
        i, kind = e["i"], e["type"]
        needs = {"mechanical"}
        if group in c.WASTEWATER_GROUPS:
            needs.add("wastewater")
        if kind == "Failure":
            needs.add(c.FAILURE_MODES[e["mode"]][4])
            parts, end = e["parts"], e["end"]
        elif kind == "Preventive":
            parts, end = job_lines(c.PREVENTIVE_PARTS, group, kw, rng), i
        else:
            parts, end = [], i
        reading = next((r for r in reversed(rows[:i + 1]) if r[3] is not None), None)
        note = technician_note(kind, e.get("mode"), parts, reading, rise[i], rng)
        service.append({"asset_id": asset["asset_id"], "event_type": kind,
                        "failure_mode": e.get("mode"), "reported_date": span[i].isoformat(),
                        "completed_date": span[end].isoformat(),
                        "technician_id": nearest_technician(asset, needs, technicians),
                        "downtime_hours": e.get("downtime", e["labour"] if kind == "Preventive" else 0.0),
                        "labour_hours": e["labour"],
                        "parts_used": ";".join(f"{p}:{q}" for p, q in parts) or None,
                        "technician_note": note, "_parts": parts})
        if kind == "Failure":
            f = next(f for f in failures if f["i"] == i)
            truth.append({"asset_id": asset["asset_id"], "failure_date": span[i].isoformat(),
                          "failure_mode": f["mode"], "warned": int(f["warned"]),
                          "warning_start_date": span[f["first"]].isoformat() if f["warned"] else None,
                          "warning_days": f["i"] - f["first"] if f["warned"] else 0,
                          "signal": f["signal"], "_event": service[-1]})
    return rows, service, truth


NOTES = {
    "Bearing wear": ["Customer reported noise, then trip. Drive-end bearing worn, vib {vib} mm/s, "
                     "brg temp {temp} C before stop. Replaced {parts}, regreased, alignment checked.",
                     "Pump stopped on high bearing temp ({temp} C). Bearings rough by hand. "
                     "Fitted {parts}. Coupling ok."],
    "Mechanical seal leak": ["Leak at mech seal, water on baseplate. Replaced {parts}. No change "
                             "seen in vib before the leak.",
                             "Seal leaking, customer isolated pump. New seal and O-rings fitted ({parts})."],
    "Impeller wear": ["Flow down per customer, power {power} kW. Impeller vanes worn, wear ring "
                      "clearance high. Replaced {parts}.",
                      "Low head, vib {vib} mm/s. Worn impeller and rings, renewed {parts}."],
    "Cavitation damage": ["Crackling noise at suction, vib {vib} mm/s. Impeller pitted by cavitation. "
                          "Replaced {parts}. Asked customer to check inlet valve and suction level."],
    "Motor overload": ["Motor tripped on overload, brg temp {temp} C, power {power} kW. "
                       "Overhauled with {parts}. Check duty point with customer."],
    "Electrical trip": ["Pump stopped with no alarm before. Fault traced to {parts}, replaced, "
                        "tested ok.",
                        "Tripped, no warning in readings. Replaced {parts}. Running again."],
    "Impeller clogging": ["Impeller blocked with rags and wipes. Cleared channel, power had risen "
                          "to {power} kW. Renewed {parts}.",
                          "Clogged, pump cycling and tripping. Cleaned out, fitted {parts}."],
    "Preventive": ["Annual service done, fitted {parts}. Vib {vib} mm/s, brg temp {temp} C. "
                   "No remarks.",
                   "Service visit, kit {parts} fitted, readings normal (vib {vib} mm/s)."],
    "Preventive, rising": ["Service done, fitted {parts}. Vib {vib} mm/s, higher than last visit. "
                           "Recommend bearing check at next stop."],
    "Inspection": ["Inspection on request. Running normally, vib {vib} mm/s, brg temp {temp} C.",
                   "Checked pump at customer's request. No fault found."],
    "Inspection, rising": ["Inspection: vib {vib} mm/s and brg temp {temp} C up on normal. "
                           "Recommend planned repair soon."],
}


def technician_note(kind: str, mode: str | None, parts: list, reading, rising, rng) -> str:
    key = mode if kind == "Failure" else kind
    if kind != "Failure" and rising and rising[0] > 0.3:
        key += ", rising"
    vib, temp, power = (reading[3], reading[4], reading[5]) if reading else ("n/a", "n/a", "n/a")
    text = rng.choice(NOTES[key])
    return text.format(vib=vib, temp=temp, power=power,
                       parts=", ".join(f"{q} x {p}" for p, q in parts) or "no parts")


def build_fleet(assets: list[dict], customers: list[dict], technicians: list[dict], rng_for,
                warning_rise: bool = True):
    days = all_days()
    contract = {cu["customer_id"]: cu["service_contract"] for cu in customers}
    telemetry, events, truth = [], [], []
    for a in assets:
        rows, service, key = simulate_asset(a, contract[a["customer_id"]], technicians, days,
                                            rng_for, warning_rise)
        telemetry += rows
        events += service
        truth += key
    events.sort(key=lambda e: (e["reported_date"], e["asset_id"], e["event_type"]))
    for n, e in enumerate(events, 1):
        e["event_id"] = f"E{n:05d}"
    for t in truth:
        t["event_id"] = t.pop("_event")["event_id"]
    truth.sort(key=lambda t: t["event_id"])
    telemetry.sort(key=lambda r: (r[0], r[1]))
    return telemetry, events, truth


# ---------------------------------------------------------------------------
# Parts orders: fact_sales split into order lines
# ---------------------------------------------------------------------------

def fleet_drivers(assets: list[dict], telemetry: list[tuple]) -> dict:
    """Each region's fleet running hours per day and mean age in each month, as
    an index against the region's own average (1.0 = average)."""
    region_of_asset = {a["asset_id"]: c.COUNTRY_REGION[next(k for k, v in c.COUNTRY_NAME.items()
                                                            if v == a["country"])]
                       for a in assets}
    hours, day_count = defaultdict(float), defaultdict(set)
    for dk, asset, h, *_ in telemetry:
        key = (region_of_asset[asset], dk // 100 * 100 + 1)
        hours[key] += h
        day_count[key].add(dk)
    out = {}
    for region in ("NOR", "BAL"):
        months = sorted(m for r, m in hours if r == region)
        per_day = {m: hours[(region, m)] / len(day_count[(region, m)]) for m in months}
        ages = {}
        for m in months:
            d = date(m // 10000, m // 100 % 100, 15)
            fleet = [years_between(date.fromisoformat(a["install_date"]), d) for a in assets
                     if region_of_asset[a["asset_id"]] == region
                     and date.fromisoformat(a["install_date"]) <= d]
            ages[m] = sum(fleet) / len(fleet)
        mean_hours = sum(per_day.values()) / len(per_day)
        mean_age = sum(ages.values()) / len(ages)
        for m in months:
            out[(region, m)] = (per_day[m] / mean_hours, ages[m] / mean_age)
    return out


def build_parts_orders(fact_sales: list[dict], events: list[dict], assets: list[dict],
                       customers: list[dict], drivers: dict, rng_for) -> list[dict]:
    budget = {}
    for s in fact_sales:
        if s["product_id"] in SALES_PRODUCTS:
            budget[(int(s["date_key"]), s["site_id"], s["region_id"], s["product_id"])] = [
                int(s["units"]), cents(s["net_sales_eur"])]
    part = {p[0]: p for p in c.PARTS}
    asset_of = {a["asset_id"]: a for a in assets}
    customer_of = {cu["customer_id"]: cu for cu in customers}
    groups_of_customer = defaultdict(list)
    for a in assets:
        groups_of_customer[a["customer_id"]].append(a)
    fleet_groups = defaultdict(lambda: defaultdict(int))
    for a in assets:
        fleet_groups[customer_of[a["customer_id"]]["region_id"]][group_of()[a["product_id"]]] += 1

    # Service lines first, in the month the parts were ordered (the day reported).
    service_lines = defaultdict(list)
    for e in events:
        if not e["_parts"]:
            continue
        a = asset_of[e["asset_id"]]
        cu = customer_of[a["customer_id"]]
        d = date.fromisoformat(e["reported_date"])
        m = month_key(d)
        service_lines[(m, service_warehouse(cu["region_id"], m), cu["region_id"])].append(
            (e, cu["customer_id"], d))

    cells = sorted({(m, site, region) for m, site, region, _p in budget})
    stray = set(service_lines) - set(cells)
    if stray:
        raise ValueError(f"service parts ordered where fact_sales has no sales: {sorted(stray)}")
    out = []
    for m, site, region in cells:
        rng = rng_for("orders", str(m), site, region)
        left = {p: list(budget.get((m, site, region, p), [0, Decimal(0)])) for p in SALES_PRODUCTS}
        units = {p: left[p][0] for p in SALES_PRODUCTS}
        # The list price per unit the month's invoiced value implies, before the
        # year's price change: the stock orders steer towards it (see below).
        growth = (1 + c.ANNUAL_PRICE_CHANGE["Spare parts and service"]) ** (
            ((m // 10000 - c.FIRST_MONTH.year) * 12 + m // 100 % 100 - 1) / 12)
        target = {p: float(left[p][1]) / left[p][0] / growth if left[p][0] else 0.0
                  for p in SALES_PRODUCTS}
        listed = {p: 0.0 for p in SALES_PRODUCTS}
        orders = []
        for e, customer, d in service_lines.get((m, site, region), []):
            lines = []
            for pid, qty in e["_parts"]:
                product = part[pid][3]
                if qty > left[product][0]:
                    raise ValueError(f"service parts exceed sales for {m} {site} {region}")
                left[product][0] -= qty
                listed[product] += float(part[pid][4]) * qty
                lines.append((pid, qty))
            orders.append({"date": d, "customer": customer, "channel": "Service technician",
                           "event": e["event_id"], "asset": e["asset_id"], "lines": lines})
        hours_index, age_index = drivers.get((region, m), (1.0, 1.0))
        weights = {}
        for basket, (base, follows, _spec) in c.BASKETS.items():
            w = base * hours_index ** follows["hours"] * age_index ** follows["age"]
            if basket == "Annual service":
                w *= c.KIT_MONTH_FACTOR.get(m // 100 % 100, 1.0)
            weights[basket] = w * max(0.1, rng.gauss(1.0, c.BASKET_NOISE))
        distributors = [cu for cu in customers if cu["region_id"] == region
                        and cu["segment"] == "Distributor"]
        end_customers = [cu for cu in customers if cu["region_id"] == region
                         and cu["segment"] != "Distributor" and groups_of_customer[cu["customer_id"]]]
        groups = fleet_groups[region]
        group_weights = {**groups, "Control panels": 0.05 * sum(groups.values()),
                         "Drive packages": 0.05 * sum(groups.values())}
        first = date(m // 10000, m // 100 % 100, 1)
        days_in_month = ((first.replace(day=28) + timedelta(days=4)).replace(day=1) - first).days
        # Distributors order in bulk where the month is big enough to hold it.
        size_factor = max(1, min(c.DISTRIBUTOR_QUANTITY_FACTOR,
                                 round(units["SPS-SP-100"] / c.UNITS_PER_BULK_STEP)))
        stalled = 0
        while any(left[p][0] > 0 for p in SALES_PRODUCTS):
            is_distributor = rng.random() < c.DISTRIBUTOR_ORDER_SHARE
            if is_distributor:
                cu = rng.choice(distributors)
                group, kw, asset = weighted(rng, group_weights), None, None
                factor = size_factor
                channel = "EDI"
            else:
                cu = rng.choice(end_customers)
                a = rng.choice(groups_of_customer[cu["customer_id"]])
                group, kw, asset = group_of()[a["product_id"]], rated_kw()[a["product_id"]], a
                factor = 1
                channels = c.CHANNELS_WITH_PORTAL if first >= c.PORTAL_FIRST_DAY else c.CHANNELS_BEFORE_PORTAL
                channel = weighted(rng, channels)
            # When the month so far runs cheaper than its invoiced value implies,
            # the dearer baskets become likelier, and the other way round, so the
            # realised price stays close to list.
            tilted = {}
            for basket, w in weights.items():
                product, sign = c.BASKET_PRICE_TILT[basket]
                done = units[product] - left[product][0]
                ratio = listed[product] / done / target[product] if done and target[product] else 1.0
                tilted[basket] = w * ratio ** (-sign * c.PRICE_TILT_STRENGTH)
            basket = weighted(rng, tilted)
            lines = []
            for pid, qty in job_lines(c.BASKETS[basket][2], group, kw, rng, factor):
                product = part[pid][3]
                qty = min(qty, left[product][0])
                if qty > 0:
                    left[product][0] -= qty
                    listed[product] += float(part[pid][4]) * qty
                    lines.append((pid, qty))
            if not lines:
                stalled += 1
                if stalled > 2000:
                    raise ValueError(f"cannot fill sales for {m} {site} {region}: {left}")
                continue
            stalled = 0
            orders.append({"date": first + timedelta(days=rng.randrange(days_in_month)),
                           "customer": cu["customer_id"], "channel": channel, "event": None,
                           "asset": None, "lines": lines,
                           "product_id": asset["product_id"] if asset else None})
        out += price_cell(m, site, region, orders, budget, part, rng)

    out.sort(key=lambda r: (r["order_date"], r["site_id"], r["_seq"], r["order_line"]))
    counters = defaultdict(int)
    numbers = {}
    for r in out:
        key = (r["site_id"], r["date_key"], r["_seq"])
        if key not in numbers:
            counters[(r["site_id"], r["date_key"])] += 1
            numbers[key] = (f"SO-{r['site_id']}-{r['date_key'] // 100}-"
                            f"{counters[(r['site_id'], r['date_key'])]:05d}")
        r["order_id"] = numbers[key]
    return out


def price_cell(m: int, site: str, region: str, orders: list[dict], budget: dict, part: dict,
               rng) -> list[dict]:
    """Price each line at list price times one factor per sales product, so the
    lines add up to fact_sales to the cent; the largest line takes the rounding."""
    rows = []
    orders.sort(key=lambda o: (o["date"], o["customer"], o["event"] or ""))
    for seq, o in enumerate(orders):
        for n, (pid, qty) in enumerate(o["lines"], 1):
            rows.append({"order_line": n, "order_date": o["date"].isoformat(), "date_key": m,
                         "site_id": site, "region_id": region, "customer_id": o["customer"],
                         "part_id": pid, "sales_product_id": part[pid][3], "quantity": qty,
                         "channel": o["channel"], "service_event_id": o["event"],
                         "asset_id": o["asset"], "_seq": f"{region}{seq:05d}",
                         "_viewed": o.get("product_id")})
    for product in SALES_PRODUCTS:
        lines = [r for r in rows if r["sales_product_id"] == product]
        if not lines:
            continue
        amount = budget[(m, site, region, product)][1]
        listed = sum(Decimal(part[r["part_id"]][4]) * r["quantity"] for r in lines)
        factor = amount / listed
        lo, hi = c.PRICE_FACTOR_RANGE
        if not lo <= factor <= hi:
            raise ValueError(f"price factor {factor:.3f} for {m} {site} {region} {product}")
        for r in lines:
            r["net_amount_eur"] = cents(Decimal(part[r["part_id"]][4]) * r["quantity"] * factor)
        biggest = max(lines, key=lambda r: r["net_amount_eur"])
        biggest["net_amount_eur"] += amount - sum(r["net_amount_eur"] for r in lines)
    return rows


# ---------------------------------------------------------------------------
# Parts portal events
# ---------------------------------------------------------------------------

def build_portal_events(orders: list[dict], customers: list[dict], assets: list[dict],
                        rng_for) -> list[dict]:
    """Sessions on the portal: one per portal order, plus browsing sessions. The old
    recommender showed the five most ordered compatible parts of the previous month."""
    compatible = defaultdict(set)
    for p in c.PARTS:
        for g in p[6]:
            compatible[g].add(p[0])
    popularity = defaultdict(lambda: defaultdict(int))
    for r in orders:
        popularity[r["date_key"]][r["part_id"]] += 1
    shown_cache = {}

    def shown(month: int, group: str) -> list[str]:
        if (month, group) not in shown_cache:
            d = date(month // 10000, month // 100 % 100, 1) - timedelta(days=1)
            counts = popularity[month_key(d)]
            ranked = sorted(compatible[group], key=lambda p: (-counts.get(p, 0), p))
            shown_cache[(month, group)] = ranked[:c.PORTAL_SHOWN]
        return shown_cache[(month, group)]

    by_order = defaultdict(list)
    for r in orders:
        if r["channel"] == "Portal":
            by_order[r["order_id"]].append(r)
    future = defaultdict(list)
    for r in orders:
        future[r["customer_id"]].append((date.fromisoformat(r["order_date"]), r["part_id"]))
    sessions = []
    for order_id in sorted(by_order):
        lines = by_order[order_id]
        sessions.append((lines[0]["order_date"], lines[0]["customer_id"], lines[0]["_viewed"],
                         {r["part_id"] for r in lines}))
    owners = defaultdict(list)
    for a in assets:
        owners[a["customer_id"]].append(a["product_id"])
    end_customers = [cu["customer_id"] for cu in customers if owners[cu["customer_id"]]]
    rng = rng_for("portal")
    portal_days = [d for d in all_days() if d >= c.PORTAL_FIRST_DAY]
    for _ in range(int(len(sessions) * c.PORTAL_BROWSE_SESSIONS_PER_ORDER)):
        customer = rng.choice(end_customers)
        d = rng.choice(portal_days)
        soon = {p for when, p in future[customer] if d < when <= d + timedelta(days=30)}
        sessions.append((d.isoformat(), customer, rng.choice(owners[customer]), soon))
    sessions.sort(key=lambda s: (s[0], s[1], s[2]))
    rows = []
    for n, (day, customer, product, wanted) in enumerate(sessions, 1):
        group = group_of()[product]
        for rank, pid in enumerate(shown(month_key(date.fromisoformat(day)), group), 1):
            chance = c.PORTAL_CLICK_IF_ORDERED if pid in wanted else c.PORTAL_CLICK_OTHERWISE
            rows.append({"event_date": day, "session_id": f"PS{n:06d}", "customer_id": customer,
                         "product_id": product, "part_id": pid, "rank": rank,
                         "clicked": int(rng.random() < chance)})
    for i, r in enumerate(rows, 1):
        r["event_id"] = i
    return rows


# ---------------------------------------------------------------------------
# Everything, in order
# ---------------------------------------------------------------------------

def build_all(fact_sales: list[dict], rng_for) -> tuple[dict, list[dict]]:
    towns = read_towns()
    customers = build_dim_customer(rng_for, towns)
    assets = build_dim_asset(customers, fact_sales, rng_for)
    technicians = build_dim_technician(towns)
    telemetry, events, truth = build_fleet(assets, customers, technicians, rng_for)
    drivers = fleet_drivers(assets, telemetry)
    orders = build_parts_orders(fact_sales, events, assets, customers, drivers, rng_for)
    portal = build_portal_events(orders, customers, assets, rng_for)
    tables = {
        "dim_customer": customers,
        "dim_asset": assets,
        "dim_part": build_dim_part(),
        "bridge_part_compatibility": build_bridge_part_compatibility(),
        "dim_technician": technicians,
        "fact_asset_telemetry": telemetry,
        "fact_service_event": events,
        "fact_parts_order": orders,
        "fact_portal_event": portal,
    }
    return tables, truth
