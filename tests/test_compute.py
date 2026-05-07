import pandas as pd
import pytest

from babelbetes.survey.compute import (
    compute_cgm_stats,
    compute_basal_stats,
    compute_bolus_stats,
    compute_complete_days,
    compute_tdd_stats,
    aggregate_study_stats,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_store(cgm_dates, bolus_dates, basal_dates, patient_id="P1", study="S1"):
    """Build a minimal flat store {data_type: df_with_study_name} from date lists."""
    def df(dates, col):
        return pd.DataFrame({
            "patient_id": patient_id,
            "study_name": study,
            "datetime": pd.to_datetime(dates),
            col: 1.0,
        })

    store = {}
    if cgm_dates is not None:
        store["cgm"] = df(cgm_dates, "cgm")
    if bolus_dates is not None:
        store["bolus"] = df(bolus_dates, "bolus")
    if basal_dates is not None:
        store["basal"] = df(basal_dates, "basal_rate")
    return store


def _cgm_df(datetimes, values, patient_id="P1", study="S1"):
    """Build a single-patient CGM DataFrame."""
    return pd.DataFrame({
        "study_name": study,
        "patient_id": patient_id,
        "datetime": pd.to_datetime(datetimes),
        "cgm": values,
    })


def _patient_metrics(records, patient_id="P1"):
    """Extract per-patient metrics as a plain dict."""
    return {r["metric"]: r["value"] for r in records if r["patient_id"] == patient_id}


def _get(records, metric, data_type, study="S1"):
    """Get a study-level metric value from a list of record dicts."""
    for r in records:
        if r.get("study") == study and r["metric"] == metric and r["data_type"] == data_type:
            return r["value"]
    return None


def _build_patient_df(store):
    """Build patient_stats_df from a store, including complete_days."""
    records = []
    if "cgm" in store:
        records += compute_cgm_stats(store["cgm"])
    if "basal" in store:
        records += compute_basal_stats(store["basal"])
    if "bolus" in store:
        records += compute_bolus_stats(store["bolus"])
    records += compute_complete_days(store)
    if not records:
        return pd.DataFrame(columns=["study", "patient_id", "data_type", "metric", "value"])
    return pd.DataFrame(records)


# ── patient_days ──────────────────────────────────────────────────────────────

def test_patient_days_counts_unique_dates_not_samples():
    """Multiple samples on the same day count as one patient-day."""
    dates = ["2020-01-01 08:00", "2020-01-01 12:00", "2020-01-02 08:00"]
    store = _make_store(cgm_dates=dates, bolus_dates=None, basal_dates=None)
    records = aggregate_study_stats(_build_patient_df(store))
    assert _get(records, "patient_days", "cgm") == 2


def test_patient_days_each_type_counted_independently():
    cgm_dates   = ["2020-01-01", "2020-01-02"]
    bolus_dates = ["2020-01-01"]
    basal_dates = ["2020-01-01", "2020-01-02", "2020-01-03"]
    store = _make_store(cgm_dates, bolus_dates, basal_dates)
    records = aggregate_study_stats(_build_patient_df(store))
    assert _get(records, "patient_days", "cgm")   == 2
    assert _get(records, "patient_days", "bolus") == 1
    assert _get(records, "patient_days", "basal") == 3


# ── missing days ──────────────────────────────────────────────────────────────

def test_missing_days_gap_in_calendar():
    """Data on day 1 and day 3 leaves day 2 missing (span = 3, patient_days = 2)."""
    df = _cgm_df(["2020-01-01", "2020-01-03"], [100.0, 100.0])
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["patient_days"] == 2.0
    assert m["missing_days"] == 1.0


def test_missing_days_zero_when_all_days_present():
    df = _cgm_df(["2020-01-01", "2020-01-02", "2020-01-03"], [100.0, 100.0, 100.0])
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["missing_days"] == 0.0


# ── chunk / gap stats ─────────────────────────────────────────────────────────

def test_chunk_count_and_data_fraction():
    """Two 1-hour CGM chunks (5-min readings) separated by a 2-hour gap.

    Chunk 1: 00:00–01:00 (1 h), gap: 2 h, Chunk 2: 03:00–04:00 (1 h).
    Total span = 4 h → data_fraction = 2/4 = 0.5.
    5-min spacing keeps readings within the 30-min CGM gap threshold.
    """
    times = list(pd.date_range("2020-01-01 00:00", "2020-01-01 01:00", freq="5min")) + \
            list(pd.date_range("2020-01-01 03:00", "2020-01-01 04:00", freq="5min"))
    df = _cgm_df(times, [100.0] * len(times))
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["chunk_count"] == 2.0
    assert m["data_fraction"] == pytest.approx(0.5)


def test_chunk_duration_geometric_mean():
    """Chunk geometric mean when chunks have unequal lengths (1 h and 3 h → gm = sqrt(3))."""
    times = list(pd.date_range("2020-01-01 00:00", "2020-01-01 01:00", freq="5min")) + \
            list(pd.date_range("2020-01-01 03:00", "2020-01-01 06:00", freq="5min"))
    df = _cgm_df(times, [100.0] * len(times))
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["gm_chunk_dur_hrs"] == pytest.approx(3**0.5, rel=1e-4)


def test_gap_duration_geometric_mean():
    """Single 2-hour gap → gm_gap_dur_hrs = 2.0."""
    times = list(pd.date_range("2020-01-01 00:00", "2020-01-01 01:00", freq="5min")) + \
            list(pd.date_range("2020-01-01 03:00", "2020-01-01 04:00", freq="5min"))
    df = _cgm_df(times, [100.0] * len(times))
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["gm_gap_dur_hrs"] == pytest.approx(2.0)


def test_single_chunk_no_gap():
    """Readings within the gap threshold form one chunk with no gaps."""
    df = _cgm_df(
        ["2020-01-01 00:00", "2020-01-01 00:05", "2020-01-01 00:10"],
        [100.0] * 3,
    )
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["chunk_count"] == 1.0
    assert m["data_fraction"] == pytest.approx(1.0)


# ── complete days ─────────────────────────────────────────────────────────────

def test_complete_days_require_all_three_types():
    """Day 1 has all three types; day 2 is missing bolus → only 1 complete day."""
    store = _make_store(
        cgm_dates=  ["2020-01-01", "2020-01-02"],
        bolus_dates=["2020-01-01"],
        basal_dates=["2020-01-01", "2020-01-02"],
    )
    assert compute_complete_days(store)[0]["value"] == 1


def test_complete_days_all_days_complete():
    dates = ["2020-01-01", "2020-01-02", "2020-01-03"]
    store = _make_store(cgm_dates=dates, bolus_dates=dates, basal_dates=dates)
    assert compute_complete_days(store)[0]["value"] == 3


def test_complete_days_zero_when_no_overlap():
    store = _make_store(
        cgm_dates=  ["2020-01-01"],
        bolus_dates=["2020-01-02"],
        basal_dates=["2020-01-03"],
    )
    assert compute_complete_days(store)[0]["value"] == 0


def test_complete_days_returns_empty_when_data_type_missing():
    store = _make_store(cgm_dates=["2020-01-01"], bolus_dates=["2020-01-01"], basal_dates=None)
    assert compute_complete_days(store) == []


# ── patients with complete data ───────────────────────────────────────────────

def test_patient_count_complete_sums_across_patients():
    """P1 has 1 complete day, P2 has 0 complete days → total complete_days = 1, patient_count = 2."""
    def rows(dates, pid, col):
        return pd.DataFrame({
            "patient_id": pid, "study_name": "S1",
            "datetime": pd.to_datetime(dates), col: 1.0,
        })

    store = {
        "cgm":   pd.concat([rows(["2020-01-01"], "P1", "cgm"),
                             rows(["2020-01-01"], "P2", "cgm")]),
        "bolus": pd.concat([rows(["2020-01-01"], "P1", "bolus"),
                             rows(["2020-01-02"], "P2", "bolus")]),
        "basal": pd.concat([rows(["2020-01-01"], "P1", "basal_rate"),
                             rows(["2020-01-03"], "P2", "basal_rate")]),
    }
    records = aggregate_study_stats(_build_patient_df(store))
    assert _get(records, "complete_days", "complete") == 1
    assert _get(records, "patient_count", "complete") == 2


def test_patient_count_only_patients_with_all_types_get_complete_days():
    """P3 has no basal → complete_days = 0; still counted in patient_count."""
    def rows(dates, pid, col):
        return pd.DataFrame({
            "patient_id": pid, "study_name": "S1",
            "datetime": pd.to_datetime(dates), col: 1.0,
        })

    store = {
        "cgm":   pd.concat([rows(["2020-01-01"], "P1", "cgm"),
                             rows(["2020-01-01"], "P3", "cgm")]),
        "bolus": pd.concat([rows(["2020-01-01"], "P1", "bolus"),
                             rows(["2020-01-01"], "P3", "bolus")]),
        "basal": rows(["2020-01-01"], "P1", "basal_rate"),  # P3 has no basal
    }
    records = compute_complete_days(store)
    by_patient = {r["patient_id"]: r["value"] for r in records}
    assert by_patient["P1"] == 1   # P1: complete
    assert by_patient["P3"] == 0   # P3: no basal → never complete


# ── glucose time in range and outliers ───────────────────────────────────────

def test_tir_tar_tbr_equal_thirds():
    """One reading in each zone: TBR (<70), TIR (70–180), TAR (>180) → each 1/3."""
    df = _cgm_df(
        ["2020-01-01", "2020-01-02", "2020-01-03"],
        [50.0, 120.0, 220.0],   # TBR, TIR, TAR
    )
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["tir"] == pytest.approx(1 / 3)
    assert m["tar"] == pytest.approx(1 / 3)
    assert m["tbr"] == pytest.approx(1 / 3)


def test_tir_all_in_range():
    df = _cgm_df(["2020-01-01", "2020-01-02"], [70.0, 180.0])
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["tir"] == pytest.approx(1.0)
    assert m["tar"] == pytest.approx(0.0)
    assert m["tbr"] == pytest.approx(0.0)


def test_outliers_detected():
    """Values <40 are low outliers, >400 are high outliers."""
    df = _cgm_df(
        ["2020-01-01", "2020-01-02", "2020-01-03"],
        [30.0, 120.0, 450.0],   # 1 low outlier, 1 normal, 1 high outlier
    )
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["outlier_low"]  == 1.0
    assert m["outlier_high"] == 1.0


def test_no_outliers_for_normal_values():
    df = _cgm_df(["2020-01-01", "2020-01-02"], [40.0, 400.0])
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["outlier_low"]  == 0.0
    assert m["outlier_high"] == 0.0


# ── duplicate_count ───────────────────────────────────────────────────────────

def test_duplicate_count_detects_exact_duplicates():
    # Same timestamp, different value — a temporal duplicate even though values differ
    df = _cgm_df(["2020-01-01", "2020-01-01", "2020-01-02"], [100.0, 200.0, 110.0])
    records = aggregate_study_stats(pd.DataFrame(compute_cgm_stats(df)))
    # duplicate_count is gm'd at study level; gm of 1 duplicate = 1.0
    assert _get(records, "duplicate_count_study_gm", "cgm") == 1.0


def test_duplicate_count_zero_for_clean_data():
    df = _cgm_df(["2020-01-01", "2020-01-02"], [100.0, 110.0])
    records = aggregate_study_stats(pd.DataFrame(compute_cgm_stats(df)))
    # gm is undefined for zero, so duplicate_count_study_gm is absent when count is 0
    assert _get(records, "duplicate_count_study_gm", "cgm") is None


# ── gm, gs, min, max ──────────────────────────────────────────────────────────

def test_gm_gs_min_max():
    """gm([1, 4]) = 2, gs([1, 4]) = 2, min = 1, max = 4."""
    df = _cgm_df(["2020-01-01", "2020-01-02"], [1.0, 4.0])
    m = _patient_metrics(compute_cgm_stats(df))
    assert m["min"] == pytest.approx(1.0)
    assert m["max"] == pytest.approx(4.0)
    assert m["gm"]  == pytest.approx(2.0)
    assert m["gs"]  == pytest.approx(2.0)


# ── TDD stats ─────────────────────────────────────────────────────────────────

def test_tdd_stats_gm_and_ratio():
    """Constant basal=10, bolus=5 over 2 days → gm equals the constant, ratio=0.5."""
    tdd_df = pd.DataFrame({
        "study":      ["S1", "S1"],
        "patient_id": ["P1", "P1"],
        "date":       ["2020-01-01", "2020-01-02"],
        "basal":      [10.0, 10.0],
        "bolus":      [5.0,  5.0],
        "total":      [15.0, 15.0],
    })
    m = _patient_metrics(compute_tdd_stats(tdd_df))
    assert m["basal_gm"]          == pytest.approx(10.0)
    assert m["bolus_gm"]          == pytest.approx(5.0)
    assert m["tdd_gm"]            == pytest.approx(15.0)
    assert m["bolus_basal_ratio"] == pytest.approx(0.5)
