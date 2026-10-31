"""Product portfolio and sales: the simulated Oracle extract and the SQL that cleans it.

The demonstration needs an ERP extract to clean, so this module writes one: monthly
ZIP files of sales order lines with a manifest of SHA-256 checksums, the shape
Oracle's Data Extraction tool produces (Jasila's note, 31 October 2026). The extract
carries the artefacts real extracts have: legacy item numbers, new codes not yet
mapped, a re-sent file and a month with no currency code.

run_sql() then does what a company's pipeline would: check the manifest, stage the
lines, map local item numbers to the global classification, remove duplicates,
convert Swedish kronor at the ECB monthly rate, validate, publish fact_sales and the
issue list, and reconcile to finance revenue to the cent. The SQL lives in ../../sql.
"""

import csv
import hashlib
import io
import math
import tempfile
import zipfile
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fjordvik_data import config as c

DATA_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = DATA_ROOT / "sql"
ECB_RATES = DATA_ROOT / "reference" / "ecb_eur_sek_monthly.csv"

EXTRACT_COLUMNS = ["BUSINESS_UNIT", "PERIOD_NAME", "ORDER_NUMBER", "LINE_ID", "ITEM_NUMBER",
                   "CUSTOMER_REGION", "QUANTITY", "UNIT_SELLING_PRICE", "CURRENCY_CODE",
                   "EXTENDED_AMOUNT", "EXTENDED_COST"]
CENT = Decimal("0.01")


def cents(x) -> Decimal:
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Dimensions and reference lists
# ---------------------------------------------------------------------------

def family_of() -> dict:
    return dict(c.PRODUCT_GROUPS)


def build_dim_product_group() -> list[dict]:
    return [{"product_group": g, "product_family": f} for g, f in c.PRODUCT_GROUPS]


def build_dim_product() -> list[dict]:
    fam = family_of()
    return [{"product_id": p, "product_name": n, "product_group": g, "product_family": fam[g],
             "made_at_site_id": site, "rated_kw": kw, "kwh_per_year": kwh,
             "lifetime_years": life, "list_price_eur": price, "standard_cost_eur": cost}
            for p, n, g, site, kw, kwh, life, price, cost, _w, _t in c.PRODUCTS]


def build_dim_region() -> list[dict]:
    return [{"region_id": r, "region_name": n} for r, n, _code in c.REGIONS]


def build_product_code_map() -> list[dict]:
    """The global classification: each business unit's local item number for each
    product. Gothenburg keeps its legacy numbers; the others use the global code."""
    site_bu = {site: bu for bu, site, _cur in c.BUSINESS_UNITS}
    rows = []
    for p in c.PRODUCTS:
        product_id, family = p[0], family_of()[p[2]]
        for site, fam in c.SITE_FAMILY.items():
            if fam != family:
                continue
            local = c.LEGACY_ITEM_NUMBERS.get(product_id, product_id) if site == "SE01" else product_id
            rows.append({"business_unit": site_bu[site], "local_item_number": local,
                         "product_id": product_id})
    rows.sort(key=lambda r: (r["business_unit"], r["local_item_number"]))
    return rows


def build_region_codes() -> list[dict]:
    return [{"erp_region_code": code, "region_id": r} for r, _n, code in c.REGIONS]


def build_business_units() -> list[dict]:
    return [{"business_unit": bu, "site_id": site, "ledger_currency": cur}
            for bu, site, cur in c.BUSINESS_UNITS]


def read_rates(path: Path = ECB_RATES) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        return {int(r["date_key"]): r["sek_per_eur"] for r in csv.DictReader(f)}


# ---------------------------------------------------------------------------
# Sales lines (in euros), then the extract written from them
# ---------------------------------------------------------------------------

def split_units(total: int, shares: dict) -> dict:
    """Largest-remainder split, so the parts add up to the whole."""
    raw = {k: total * v for k, v in shares.items()}
    out = {k: math.floor(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[:total - sum(out.values())]:
        out[k] += 1
    return out


def build_sales_lines(site_metrics: list[dict], months, months_between, rng_for) -> list[dict]:
    """Order lines in euros for every site-month with revenue, summing exactly to
    that site-month's revenue_eur."""
    products = defaultdict(list)
    fam = family_of()
    for p in c.PRODUCTS:
        products[fam[p[2]]].append(p)
    revenue = {(r["date_key"], r["site_id"]): cents(r["revenue_eur"]) for r in site_metrics}
    lines = []
    for site, family in c.SITE_FAMILY.items():
        rng = rng_for(site, "sales")
        for d in months():
            key = d.year * 10000 + d.month * 100 + 1
            total = revenue.get((key, site))
            if not total:
                continue
            t = months_between(c.FIRST_MONTH, d) / 12
            weights = {p[0]: max(0.01, (p[9] + p[10] * t) * rng.gauss(1, 0.03)) for p in products[family]}
            wsum = sum(weights.values())
            month_lines = []
            for p in products[family]:
                pid, price, cost = p[0], p[7], p[8]
                unit_price = price * (1 + c.ANNUAL_PRICE_CHANGE[family]) ** t * (1 + rng.gauss(0, c.PRICE_NOISE))
                unit_cost = cost * (1 + c.ANNUAL_COST_CHANGE) ** t * (1 + rng.gauss(0, 0.01))
                units = max(len(c.REGION_SPLIT[site]), round(float(total) * weights[pid] / wsum / unit_price))
                for region, n in split_units(units, c.REGION_SPLIT[site]).items():
                    if n:
                        month_lines.append({"date_key": key, "site_id": site, "product_id": pid,
                                            "region_id": region, "units": n,
                                            "amount": cents(n * unit_price), "cost": cents(n * unit_cost)})
            # The largest line absorbs the rounding, so the month equals finance revenue.
            biggest = max(month_lines, key=lambda l: l["amount"])
            biggest["amount"] += total - sum(l["amount"] for l in month_lines)
            lines += month_lines
    return lines


def to_ledger(eur: Decimal, rate: str) -> Decimal:
    """A kronor amount that converts back to exactly `eur` at `rate`, rounded to the
    cent, and is never near a rounding tie, so any correct conversion agrees."""
    r = float(rate)
    sek = cents(float(eur) * r)
    for step in range(200):
        for candidate in (sek + CENT * step, sek - CENT * step):
            back = float(candidate) / r * 100
            if cents(float(candidate) / r) == eur and abs(back - math.floor(back) - 0.5) > 0.1:
                return candidate
    raise ValueError(f"no kronor amount converts back to {eur}")


def extract_rows(lines: list[dict], rates: dict) -> dict:
    """Extract rows by (month, business unit), as the ERP would export them."""
    site_bu = {site: (bu, cur) for bu, site, cur in c.BUSINESS_UNITS}
    region_code = {r: code for r, _n, code in c.REGIONS}
    local = {(m["business_unit"], m["product_id"]): m["local_item_number"]
             for m in build_product_code_map()}
    unmapped = {(date_key_of(d), bu, pid, region): code for d, bu, code, pid, region in c.UNMAPPED_CODES}
    missing = (date_key_of(c.MISSING_CURRENCY[0]), c.MISSING_CURRENCY[1])
    out = defaultdict(list)
    counter = defaultdict(int)
    for l in sorted(lines, key=lambda l: (l["date_key"], l["site_id"], l["product_id"], l["region_id"])):
        bu, cur = site_bu[l["site_id"]]
        counter[bu] += 1
        amount, cost = l["amount"], l["cost"]
        if cur != "EUR":
            amount, cost = to_ledger(amount, rates[l["date_key"]]), to_ledger(cost, rates[l["date_key"]])
        key = l["date_key"]
        out[(key, bu)].append({
            "BUSINESS_UNIT": bu,
            "PERIOD_NAME": f"{key // 10000}-{key // 100 % 100:02d}",
            "ORDER_NUMBER": f"{bu.split()[2][:3].upper()}-SO-{key // 100}-{counter[bu]:05d}",
            "LINE_ID": f"{bu.split()[2][:3].upper()}{counter[bu]:07d}",
            "ITEM_NUMBER": unmapped.get((key, bu, l["product_id"], l["region_id"]),
                                        local[(bu, l["product_id"])]),
            "CUSTOMER_REGION": region_code[l["region_id"]],
            "QUANTITY": l["units"],
            "UNIT_SELLING_PRICE": (amount / l["units"]).quantize(Decimal("0.0001")),
            "CURRENCY_CODE": "" if (key, bu) == missing else cur,
            "EXTENDED_AMOUNT": amount,
            "EXTENDED_COST": cost,
        })
    return out


def date_key_of(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXTRACT_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def zip_bytes(name: str, data: bytes) -> bytes:
    """A ZIP with a fixed timestamp and no compression, so it is byte-identical on
    every run (compressed output can differ between zlib versions)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        z.writestr(info, data)
    return buf.getvalue()


def write_extract(out_dir: Path, rows_by_month_bu: dict) -> None:
    """One folder per month: a ZIP per business unit and a manifest of checksums,
    '<file>;<document id>;<sha-256>' per line, as Oracle's tool writes it."""
    by_month = defaultdict(dict)
    for (key, bu), rows in rows_by_month_bu.items():
        by_month[key][bu] = rows
    sent_in, resent_bu, resent_for = (date_key_of(d) if isinstance(d, date) else d
                                      for d in c.RESENT_EXTRACT)
    for key in sorted(by_month):
        folder = out_dir / f"{key // 10000}-{key // 100 % 100:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        files = [(f"SalesOrderLines_{bu.split()[2]}_{key // 100}.zip", rows)
                 for bu, rows in sorted(by_month[key].items())]
        if key == sent_in:  # last month's file for one business unit arrives again
            files.append((f"SalesOrderLines_{resent_bu.split()[2]}_{resent_for // 100}_resent.zip",
                          by_month[resent_for][resent_bu]))
        manifest = []
        for i, (name, rows) in enumerate(files, 1):
            data = zip_bytes("SalesOrderLines.csv", csv_bytes(rows))
            (folder / name).write_bytes(data)
            manifest.append(f"{name};FJV-EXT-{key // 100}-{i:02d};{hashlib.sha256(data).hexdigest()}")
        (folder / "manifest.mf").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# The pipeline: manifest check in Python, everything else in DuckDB SQL
# ---------------------------------------------------------------------------

class ExtractError(ValueError):
    """The extract failed a check; nothing is published."""


def unpack(extract_dir: Path, staging: Path) -> int:
    """Check every ZIP against its manifest, then unpack its CSV for staging."""
    n = 0
    for manifest in sorted(extract_dir.glob("*/manifest.mf")):
        listed = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            name, _doc, digest = line.split(";")
            listed[name] = digest
        present = {p.name for p in manifest.parent.glob("*.zip")}
        if present != set(listed):
            raise ExtractError(f"{manifest.parent.name}: files {sorted(present ^ set(listed))} "
                               "are not both in the folder and in the manifest")
        for name, digest in sorted(listed.items()):
            data = (manifest.parent / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ExtractError(f"{manifest.parent.name}/{name}: checksum does not match the manifest")
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                n += 1
                (staging / f"{manifest.parent.name}__{name[:-4]}.csv").write_bytes(z.read("SalesOrderLines.csv"))
    return n


def run_sql(extract_dir: Path, reference_dir: Path, tables_dir: Path,
            rates: Path = ECB_RATES) -> dict:
    """Run sql/*.sql in order. Returns the published tables as lists of dicts."""
    import duckdb

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        if unpack(extract_dir, staging) == 0:
            raise ExtractError("no extract files found")
        con = duckdb.connect(":memory:")
        paths = {"staging": (staging / "*.csv").as_posix(),
                 "code_map": (reference_dir / "product_code_map.csv").as_posix(),
                 "region_codes": (reference_dir / "region_codes.csv").as_posix(),
                 "business_units": (reference_dir / "business_units.csv").as_posix(),
                 "rates": rates.as_posix(),
                 "regions": (tables_dir / "dim_region.csv").as_posix(),
                 "products": (tables_dir / "dim_product.csv").as_posix(),
                 "finance": (tables_dir / "fact_site_metrics.csv").as_posix()}
        for script in sorted(SQL_DIR.glob("*.sql")):
            con.execute(script.read_text(encoding="utf-8").format(**paths))
        failed = con.execute("SELECT * FROM check_results WHERE NOT passed ORDER BY check_name").fetchall()
        if failed:
            raise ExtractError("checks failed: " + "; ".join(f"{r[0]} ({r[2]})" for r in failed))
        out = {}
        for table in ("fact_sales", "fact_data_issue", "dim_product_code", "check_results"):
            cur = con.execute(f"SELECT * FROM {table}")
            names = [d[0] for d in cur.description]
            out[table] = [dict(zip(names, row)) for row in cur.fetchall()]
        return out


# ---------------------------------------------------------------------------
# Category 11 and the scorecard
# ---------------------------------------------------------------------------

def build_fact_use_phase(fact_sales: list[dict]) -> list[dict]:
    """Lifetime electricity of the pumps sold in each month, at the grid factor of
    the region of use. Products that use no energy, and regions with no factor
    source (Rest of world), get no row."""
    spec = {p[0]: (p[5], p[6]) for p in c.PRODUCTS}
    rows = []
    for s in fact_sales:
        kwh, life = spec[s["product_id"]]
        factor = c.USE_PHASE_GRID_FACTOR.get(s["region_id"])
        if not kwh or factor is None:
            continue
        activity = s["units"] * life * kwh
        rows.append({"date_key": s["date_key"], "site_id": s["site_id"], "source_id": "S14",
                     "product_id": s["product_id"], "region_id": s["region_id"],
                     "units": s["units"], "net_sales_eur": s["net_sales_eur"],
                     "activity_amount": activity, "unit": "kWh", "emission_factor": factor,
                     "tco2e": round(activity * factor / 1000, 6)})
    return rows


def build_dim_score_criterion() -> list[dict]:
    return [{"criterion_id": i, "criterion_name": n, "weight": w,
             "source": "Criterion: Cooper and Edgett (Stage-Gate International, 2022). "
                       "Weight: Fjordvik's own choice."}
            for i, n, w in c.SCORE_CRITERIA]


def build_fact_product_rating(months, rng_for) -> list[dict]:
    """Each quarter's review rates every product group 1 to 10 on each criterion."""
    rows = []
    for group, _family in c.PRODUCT_GROUPS:
        for cid, _name, _w in c.SCORE_CRITERIA:
            rng = rng_for(group, cid, "rating")
            level = c.BASE_RATING[group] + rng.choice([-1, 0, 0, 1])
            for d in months():
                if d.month % 3 != 1:
                    continue  # one rating per quarter, keyed to its first month
                level = min(10, max(1, level + rng.choice([-1, 0, 0, 0, 1])))
                rows.append({"date_key": date_key_of(d), "product_group": group,
                             "criterion_id": cid, "rating": level})
    return rows
