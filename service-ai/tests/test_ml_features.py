"""Features (D11, D12) and anomaly scores: windows end on day t, blanks are skipped, the
baseline needs its readings, and only a slow rise raises the robust z-score."""

import numpy as np
import pandas as pd
import pytest

from fjordvik_service.ml import anomaly, features, pipeline
from ml_fixtures import make_tables, rise, spike


def _build(tables, ev_ml, allow):
    return features.build(tables, ev_ml, allow).set_index(["asset_id", "date"])


def test_columns_sit_inside_the_allowlist_and_helpers_are_marked(ev_ml, allow):
    f = features.build(make_tables(200), ev_ml, allow)
    names = set(features.feature_names(allow))
    assert len(names) == allow["column_count"] == 32
    built = [c for c in f.columns if c not in ("asset_id", "date") and not c.startswith("_")]
    assert set(built) == names - {"iforest_score"}
    with pytest.raises(ValueError):
        features.assert_inside_allowlist(built + ["days_since_last_stop"], allow)


def test_blanks_are_skipped_and_a_stopped_day_has_no_power_reading(ev_ml, allow):
    tables = make_tables(200)
    tel = tables["telemetry"]
    stop = (tel["asset_id"] == "P01") & (tel["date"] == pd.Timestamp("2023-05-10"))
    tel.loc[stop, ["running_hours", "power_kw"]] = 0.0
    tel.loc[stop, ["vibration_mm_s", "bearing_temp_c"]] = np.nan
    f = _build(tables, ev_ml, allow)
    p = tel[tel["asset_id"] == "P01"].set_index("date")
    window = p.loc["2023-05-04":"2023-05-10"]
    row = f.loc[("P01", pd.Timestamp("2023-05-10"))]
    assert row["vibration_med7"] == window["vibration_mm_s"].median()          # six readings, blank skipped
    assert row["power_per_rated_kw_med7"] == (window["power_kw"] / 30).where(window["vibration_mm_s"].notna()).median()
    assert bool(row["_no_running"])


def test_the_warm_up_needs_60_readings_in_days_t_97_to_t_8(ev_ml, allow):
    f = _build(make_tables(200), ev_ml, allow).loc["P01"]
    # Day index 67 is the first with 60 days in its baseline (days 0 to 59).
    assert f["_baseline_readings"].iloc[66] == 59 and f["_baseline_readings"].iloc[67] == 60
    assert np.isnan(f["vibration_z"].iloc[66]) and not np.isnan(f["vibration_z"].iloc[67])
    assert f["_baseline_readings"].iloc[150] == 90


def test_a_rebuild_without_later_rows_changes_no_real_feature(data_dir, ev_ml, allow, subset_pumps):
    """D11 on the real tables, 20 random pump-days."""
    tables = features.read_tables(data_dir, allow, cut_off=pd.Timestamp(ev_ml["periods"]["validation"]["cut_off"]),
                                  pumps=subset_pumps)
    full = features.build(tables, ev_ml, allow)
    sample = full[full["_baseline_readings"] >= 60].sample(20, random_state=np.random.RandomState(np.random.PCG64(1)))
    columns = [c for c in features.feature_names(allow) if c != "iforest_score"]
    changed = features.check_point_in_time(lambda tb: features.build(tb, ev_ml, allow), tables,
                                           list(zip(sample["asset_id"], sample["date"], strict=True)), columns,
                                           full=full, lookback=pipeline.lookback_days(ev_ml))
    assert changed == []


def test_a_seasonal_wave_shared_by_the_fleet_raises_no_z_score(ev_ml, allow):
    """The season is plain in the raw change against the baseline (bearing temperature swings
    6 C), but the fleet adjustment removes it: almost no z-score passes 3. The few that do
    come from noise on readings rounded to 0.1 across four pumps, not from the season."""
    f = _build(make_tables(500), ev_ml, allow)
    assert f["bearing_temp_med7_vs_base"].abs().max() > 3
    for s in features.SENSORS:
        assert (f[f"{s}_z"].abs() > 3).mean() < 0.005, s


def test_a_one_day_spike_raises_no_z_score(ev_ml, allow):
    pumps = {f"P{i:02d}": {"application": "A"} for i in range(6)}
    pumps["P00"]["events"] = [spike("vibration_mm_s", 300, 8.0)]
    f = _build(make_tables(400, pumps), ev_ml, allow).loc["P00"]
    assert f["vibration_z"].iloc[295:315].abs().max() < 3
    assert f["vibration_med7"].iloc[300] < 3


def test_a_slow_rise_raises_the_z_score_and_the_forest_score(ev_ml, allow):
    pumps = {f"P{i:02d}": {"application": "A"} for i in range(6)}
    pumps["P00"]["events"] = [rise("vibration_mm_s", 300, 30, 2.0)]
    f = features.build(make_tables(400, pumps), ev_ml, allow)
    p0 = f[f["asset_id"] == "P00"].set_index("date")
    assert p0["vibration_z"].iloc[:300].abs().max() < 3
    assert p0["vibration_z"].iloc[330] > 3 and p0["z_days_above_3_14d"].iloc[335] > 0
    train = f[f["date"] < f["date"].iloc[0] + pd.Timedelta(days=290)]
    forest = anomaly.fit_iforest(train, 20230101)
    scores = pd.Series(anomaly.iforest_score(forest, f), index=f.index)
    late = f["date"] == p0.index[330]
    assert scores[late & (f["asset_id"] == "P00")].iloc[0] > scores[late & (f["asset_id"] != "P00")].max()
