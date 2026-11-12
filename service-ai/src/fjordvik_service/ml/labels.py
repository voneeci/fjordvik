"""Labels and at-risk rows, from fact_service_event only (four columns; never the answer key).

Label for pump p on day t: 1 when a Failure event for p has reported_date in (t, t+30].
At-risk rows drop, in this order: days with an open failure ticket, days with no running,
and days before the pump's baseline warm-up. Each drop is counted and asserted (D15).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from ..common.checks import PipelineCheckError, check_frame
from .splits import failure_period_bounds, periods

EVENT_COLUMNS = ["event_type", "asset_id", "reported_date", "completed_date"]


def read_failures(data_dir, ev, *, cut_off=None, pumps=None):
    """Failure events: asset, reported and completed dates. With a cut-off, no event reported
    after it is read, and a ticket still open then is treated as open to the cut-off, which is
    what is known on that day."""
    e = pd.read_csv(Path(data_dir) / "fact_service_event.csv", usecols=EVENT_COLUMNS)
    f = e[e["event_type"] == ev["labels"]["event_type"]].drop(columns="event_type")
    f = f.assign(reported_date=pd.to_datetime(f["reported_date"]), completed_date=pd.to_datetime(f["completed_date"]))
    if cut_off is not None:
        f = f[f["reported_date"] <= cut_off]
        f = f.assign(completed_date=f["completed_date"].clip(upper=cut_off))
    if pumps is not None:
        f = f[f["asset_id"].isin(pumps)]
    f = f.sort_values(["asset_id", "reported_date"]).reset_index(drop=True)
    check_frame(f, "failures", ["asset_id", "reported_date"], min_rows=0,
                required=["asset_id", "reported_date", "completed_date"])
    return f


def _by_pump(failures, column):
    return {p: g[column].to_numpy(dtype="datetime64[ns]") for p, g in failures.groupby("asset_id")}


def label(rows, failures, days):
    """1 when the pump has a failure reported in (t, t+days], else 0."""
    reported = _by_pump(failures, "reported_date")
    out = np.zeros(len(rows), dtype=np.int8)
    span = np.timedelta64(days, "D")
    for pump, idx in rows.groupby("asset_id").indices.items():
        rep = reported.get(pump)
        if rep is None:
            continue
        t = rows["date"].to_numpy(dtype="datetime64[ns]")[idx]
        n = np.searchsorted(rep, t + span, side="right") - np.searchsorted(rep, t, side="right")
        out[idx] = (n > 0).astype(np.int8)
    return out


def open_ticket(rows, failures):
    """True on days from a failure's reported_date to its completed_date, inclusive."""
    out = np.zeros(len(rows), dtype=bool)
    dates = rows["date"].to_numpy(dtype="datetime64[ns]")
    index = rows.groupby("asset_id").indices
    for pump, g in failures.groupby("asset_id"):
        idx = index.get(pump)
        if idx is None:
            continue
        t = dates[idx]
        for start, end in zip(g["reported_date"].to_numpy(), g["completed_date"].to_numpy(), strict=True):
            out[idx[(t >= start) & (t <= end)]] = True
    return out


def at_risk(feats, failures, ev):
    """Label every row, drop the three kinds of row in order, and count each drop."""
    rows = feats.copy()
    rows["label"] = label(rows, failures, ev["periods"]["label_window_days"])
    ticket = open_ticket(rows, failures)
    need = ev["model"]["features"]["baseline"]["min_readings"]
    no_running = rows["_no_running"].to_numpy() & ~ticket
    warm = (rows["_baseline_readings"].to_numpy() < need) & ~ticket & ~no_running
    rows["_open_ticket"] = ticket
    rows["_warm_up"] = warm
    keep = ~ticket & ~no_running & ~warm
    counts = {"telemetry_rows": len(rows), "open_failure_ticket": int(ticket.sum()),
              "no_running_with_no_open_ticket": int(no_running.sum()), "warm_up": int(warm.sum()),
              "at_risk_rows": int(keep.sum())}
    if counts["at_risk_rows"] + counts["warm_up"] + counts["no_running_with_no_open_ticket"] \
            + counts["open_failure_ticket"] != counts["telemetry_rows"]:
        raise PipelineCheckError(f"at-risk rows: the drops don't add up {counts}")
    return rows, keep, counts


def period_counts(rows, ev, available):
    """Counts per period over its scored days, as expected_counts lays them out."""
    p = periods(ev)
    out = {}
    for name in available:
        first = p[name]["first_scored"] or rows["date"].min()
        in_days = rows["date"].between(first, p[name]["last_scored"]).to_numpy()
        ticket, warm = rows["_open_ticket"].to_numpy(), rows["_warm_up"].to_numpy()
        no_run = rows["_no_running"].to_numpy() & ~ticket
        before_warm = in_days & ~ticket & ~no_run
        scored = before_warm & ~warm
        out[name] = {
            "telemetry_rows_in_scored_days": int(in_days.sum()),
            "after_open_ticket_filter": int((in_days & ~ticket).sum()),
            "at_risk_rows": int(before_warm.sum()),
            "positive_rows": int(rows["label"].to_numpy()[before_warm].sum()),
            "dropped_by_warm_up": int((in_days & warm).sum()),
            "scored_rows": int(scored.sum()),
            "scored_positive_rows": int(rows["label"].to_numpy()[scored].sum()),
        }
    return out


def failure_counts(failures, ev, available):
    bounds = failure_period_bounds(ev)
    out = {}
    for name in available:
        first, last = bounds[name]
        r = failures["reported_date"]
        out[name] = int(((r <= last) & (True if first is None else r >= first)).sum())
    return out


def check_expected(counts, by_period, failures_by_period, ev, *, full):
    """Assert every count the evaluation set records for the data this step read (D15)."""
    exp = ev["expected_counts"]
    problems = []

    def same(what, got, want):
        if got != want:
            problems.append(f"{what}: {got}, expected {want}")

    if full:
        same("telemetry rows", counts["telemetry_rows"], exp["telemetry_rows"])
        same("open-ticket rows", counts["open_failure_ticket"], exp["rows_dropped_over_all_dates"]["open_failure_ticket"])
        same("no-running rows", counts["no_running_with_no_open_ticket"],
             exp["rows_dropped_over_all_dates"]["no_running_with_no_open_ticket"])
    per = exp["rows_per_period"]
    for name, c in by_period.items():
        same(f"{name} failures", failures_by_period[name], exp["failures"][name])
        same(f"{name} telemetry rows in scored days", c["telemetry_rows_in_scored_days"], per["telemetry_rows_in_scored_days"][name])
        same(f"{name} rows after the open-ticket filter", c["after_open_ticket_filter"], per["after_open_ticket_filter"][name])
        same(f"{name} at-risk rows", c["at_risk_rows"], per["at_risk_rows"][name])
        same(f"{name} positive rows", c["positive_rows"], per["positive_rows"][name])
    if problems:
        raise PipelineCheckError("expected counts (D15): " + "; ".join(problems))
