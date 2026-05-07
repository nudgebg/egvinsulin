"""Integration tests for the full survey toolchain using real DCLP3 + Flair data.

Tests cover survey save/load roundtrip, metric consistency with raw data,
diff change detection, and HTML report generation.

Skipped automatically when data/out is absent (CI without data).
"""
import pandas as pd
import pytest

from babelbetes.src import data_store
from babelbetes.survey import compute, diff
from babelbetes.survey import report as report_module
from babelbetes.survey import survey

DATA_DIR = "data/out"
STUDIES = ["DCLP3", "Flair"]
N_PATIENTS = 5  # patients per study to keep tests fast


@pytest.fixture(scope="module")
def store():
    """Load a small subset of DCLP3 + Flair data (first N patients per study)."""
    import os
    if not os.path.isdir(DATA_DIR):
        pytest.skip("data/out not found — run extraction pipeline first")
    full = data_store.load(DATA_DIR, studies=STUDIES)
    if not full:
        pytest.skip("No data found for DCLP3/Flair")
    subset = {}
    for dt, df in full.items():
        frames = [
            sdf[sdf["patient_id"].isin(sdf["patient_id"].unique()[:N_PATIENTS])]
            for _, sdf in df.groupby("study_name", observed=True)
        ]
        if frames:
            subset[dt] = pd.concat(frames, ignore_index=True)
    return subset


@pytest.fixture(scope="module")
def computed(store):
    """Run the full compute pipeline once (expensive — module-scoped)."""
    patient_records = (
        (compute.compute_cgm_stats(store["cgm"])   if "cgm"   in store else [])
        + (compute.compute_basal_stats(store["basal"]) if "basal" in store else [])
        + (compute.compute_bolus_stats(store["bolus"]) if "bolus" in store else [])
        + compute.compute_complete_days(store)
    )
    tdd_df = compute.compute_tdd_per_patient(store)
    patient_records += compute.compute_tdd_stats(tdd_df)
    patient_df = pd.DataFrame(patient_records)
    study_records = compute.aggregate_study_stats(patient_df)
    cdf_df = compute.compute_cdf_quantiles(store)
    return dict(
        patient_records=patient_records,
        patient_df=patient_df,
        study_records=study_records,
        tdd_df=tdd_df,
        cdf_df=cdf_df,
    )


@pytest.fixture
def survey_dir(tmp_path, monkeypatch):
    """Redirect survey saves to a temp directory."""
    monkeypatch.setattr(survey, "SURVEY_DIR", tmp_path)
    return tmp_path


# ── survey roundtrip ──────────────────────────────────────────────────────────

def test_survey_saves_all_four_artifacts(computed, survey_dir):
    """Saving all artifact types creates four correctly-named Parquet files."""
    ts = "test_20200101_000000"
    survey.save_study_stats(computed["study_records"], survey_id=ts)
    survey.save_patient_stats(computed["patient_records"], survey_id=ts)
    survey.save_tdd(computed["tdd_df"], survey_id=ts)
    survey.save_cdf_quantiles(computed["cdf_df"], survey_id=ts)

    files = list(survey_dir.glob("*.parquet"))
    assert len(files) == 4, f"Expected 4 parquets, got {[f.name for f in files]}"


@pytest.mark.usefixtures("survey_dir")
def test_study_stats_schema(computed):
    """Loaded study_stats has the expected columns and at least one row."""
    path = survey.save_study_stats(computed["study_records"], survey_id="schema")
    df = survey.load_study_stats(path)
    assert {"study", "data_type", "metric", "value", "survey_id"}.issubset(df.columns)
    assert len(df) > 0


@pytest.mark.usefixtures("survey_dir")
def test_patient_stats_schema(computed):
    """Loaded patient_stats has the expected columns."""
    path = survey.save_patient_stats(computed["patient_records"], survey_id="schema_p")
    df = survey.load_patient_stats(path)
    assert {"study", "patient_id", "data_type", "metric", "value", "survey_id"}.issubset(df.columns)
    assert len(df) > 0


@pytest.mark.usefixtures("survey_dir")
def test_survey_list_finds_saved_files(computed):
    """list_study_stats_surveys returns paths in sorted order after saving."""
    survey.save_study_stats(computed["study_records"], survey_id="list_a")
    survey.save_study_stats(computed["study_records"], survey_id="list_b")
    paths = survey.list_study_stats_surveys()
    names = [p.name for p in paths]
    assert "list_a_study_stats.parquet" in names
    assert "list_b_study_stats.parquet" in names
    assert names == sorted(names)


# ── metric consistency with raw data ─────────────────────────────────────────

def test_row_count_matches_raw(store, computed):
    """Per-patient row_count in patient_stats equals the actual row count in the store."""
    patient_df = computed["patient_df"]
    for data_type in ("cgm", "bolus", "basal"):
        if data_type not in store:
            continue
        actual = store[data_type].groupby(["study_name", "patient_id"], observed=True).size()
        stats = (
            patient_df[
                (patient_df["data_type"] == data_type) &
                (patient_df["metric"] == "row_count")
            ]
            .set_index(["study", "patient_id"])["value"]
        )
        for (study_name, pid), actual_count in actual.items():
            if (study_name, pid) not in stats.index:
                continue
            assert actual_count == pytest.approx(stats.loc[(study_name, pid)], abs=0), (
                f"{study_name}/{pid}/{data_type}: raw={actual_count}, stats={stats.loc[(study_name, pid)]}"
            )


def test_patient_count_matches_raw(store, computed):
    """study_stats patient_count per (study, data_type) matches unique patients in the store."""
    study_df = pd.DataFrame(computed["study_records"])
    pc = (
        study_df[study_df["metric"] == "patient_count"]
        .set_index(["study", "data_type"])["value"]
    )
    for data_type in ("cgm", "bolus", "basal"):
        if data_type not in store:
            continue
        actual = store[data_type].groupby("study_name", observed=True)["patient_id"].nunique()
        for study_name, actual_n in actual.items():
            if (study_name, data_type) not in pc.index:
                continue
            assert actual_n == pytest.approx(pc.loc[(study_name, data_type)], abs=0), (
                f"{study_name}/{data_type}: raw={actual_n}, stats={pc.loc[(study_name, data_type)]}"
            )


def test_tir_manual_spot_check(store, computed):
    """TIR for one patient in patient_stats matches manually computed value from raw CGM."""
    cgm = store["cgm"]
    first = cgm.iloc[0]
    study_name, pid = first["study_name"], first["patient_id"]
    values = cgm[(cgm["study_name"] == study_name) & (cgm["patient_id"] == pid)]["cgm"].dropna()
    expected_tir = float(((values >= 70) & (values <= 180)).sum() / len(values))

    patient_df = computed["patient_df"]
    row = patient_df[
        (patient_df["study"] == study_name) &
        (patient_df["patient_id"] == pid) &
        (patient_df["data_type"] == "cgm") &
        (patient_df["metric"] == "tir")
    ]
    assert len(row) == 1, f"Expected exactly one TIR row for {study_name}/{pid}"
    assert row.iloc[0]["value"] == pytest.approx(expected_tir, rel=1e-6)


def test_tir_tar_tbr_sum_to_one(computed):
    """TIR + TAR + TBR = 1 for every patient and all values are in [0, 1]."""
    df = computed["patient_df"]
    cgm_df = df[(df["data_type"] == "cgm") & (df["metric"].isin(["tir", "tar", "tbr"]))]
    wide = cgm_df.pivot_table(index=["study", "patient_id"], columns="metric", values="value")
    assert wide[["tir", "tar", "tbr"]].ge(0).all().all(), "Negative TIR/TAR/TBR values found"
    assert wide[["tir", "tar", "tbr"]].le(1).all().all(), "TIR/TAR/TBR > 1 found"
    total = wide[["tir", "tar", "tbr"]].sum(axis=1)
    assert (total - 1.0).abs().max() < 1e-6, "TIR + TAR + TBR does not sum to 1"


def test_missing_days_non_negative(computed):
    """missing_days is non-negative for every patient and data type."""
    df = computed["patient_df"]
    missing = df[df["metric"] == "missing_days"]["value"]
    assert (missing >= 0).all(), f"Negative missing_days: {missing[missing < 0]}"


def test_patient_days_leq_span(computed):
    """patient_days never exceeds the calendar span (data_fraction_days in [0, 1])."""
    df = computed["patient_df"]
    frac = df[df["metric"] == "data_fraction_days"]["value"]
    assert (frac >= 0).all() and (frac <= 1.0 + 1e-9).all(), (
        f"data_fraction_days out of [0, 1]: {frac[(frac < 0) | (frac > 1.0 + 1e-9)]}"
    )


# ── diff ──────────────────────────────────────────────────────────────────────

@pytest.mark.usefixtures("survey_dir")
def test_diff_identical_surveys_no_flags(computed):
    """Diffing a survey against itself produces no flagged rows."""
    path = survey.save_study_stats(computed["study_records"], survey_id="nodiff")
    snap = survey.load_study_stats(path)
    diff_df = diff.diff_study_stats(snap, snap)
    assert not diff_df["flagged"].any(), "Diff of identical surveys flagged changes"
    assert (diff_df["status"] == "unchanged").all()


@pytest.mark.usefixtures("survey_dir")
def test_diff_detects_large_change(computed):
    """Doubling patient_count in survey_b is detected as a 100% change and flagged."""
    path_a = survey.save_study_stats(computed["study_records"], survey_id="diff_a")
    snap_a = survey.load_study_stats(path_a)

    snap_b = snap_a.copy()
    mask = (snap_b["metric"] == "patient_count") & (snap_b["data_type"] == "cgm")
    assert mask.any(), "No patient_count/cgm rows found in survey"
    snap_b.loc[mask, "value"] *= 2.0

    path_b = survey.save_study_stats(snap_b.to_dict("records"), survey_id="diff_b")
    snap_b_loaded = survey.load_study_stats(path_b)

    diff_df = diff.diff_study_stats(snap_a, snap_b_loaded)
    flagged = diff_df[diff_df["flagged"]]
    assert len(flagged) > 0, "No flagged changes found after doubling patient_count"
    assert (flagged["metric"] == "patient_count").all()
    assert (flagged["pct_change"].abs() - 100.0).abs().max() < 1e-6


@pytest.mark.usefixtures("survey_dir")
def test_diff_detects_removed_metric(computed):
    """A metric present in survey_a but absent in survey_b gets status='removed'."""
    path_a = survey.save_study_stats(computed["study_records"], survey_id="rem_a")
    snap_a = survey.load_study_stats(path_a)

    snap_b_records = snap_a[snap_a["metric"] != "patient_count"].to_dict("records")
    path_b = survey.save_study_stats(snap_b_records, survey_id="rem_b")
    snap_b = survey.load_study_stats(path_b)

    diff_df = diff.diff_study_stats(snap_a, snap_b)
    removed = diff_df[diff_df["status"] == "removed"]
    assert len(removed) > 0 and (removed["metric"] == "patient_count").all()


@pytest.mark.usefixtures("survey_dir")
def test_diff_detects_added_metric(computed):
    """A metric absent in survey_a but present in survey_b gets status='added'."""
    snap_a_records = [r for r in computed["study_records"] if r["metric"] != "patient_count"]
    path_a = survey.save_study_stats(snap_a_records, survey_id="add_a")
    snap_a = survey.load_study_stats(path_a)

    path_b = survey.save_study_stats(computed["study_records"], survey_id="add_b")
    snap_b = survey.load_study_stats(path_b)

    diff_df = diff.diff_study_stats(snap_a, snap_b)
    added = diff_df[diff_df["status"] == "added"]
    assert len(added) > 0 and (added["metric"] == "patient_count").all()


@pytest.mark.usefixtures("survey_dir")
def test_diff_small_change_not_flagged(computed):
    """A 1% change stays within the 5% threshold and is not flagged."""
    path_a = survey.save_study_stats(computed["study_records"], survey_id="small_a")
    snap_a = survey.load_study_stats(path_a)

    snap_b = snap_a.copy()
    mask = (snap_b["metric"] == "patient_count") & (snap_b["data_type"] == "cgm")
    snap_b.loc[mask, "value"] *= 1.01  # +1%

    path_b = survey.save_study_stats(snap_b.to_dict("records"), survey_id="small_b")
    snap_b_loaded = survey.load_study_stats(path_b)

    diff_df = diff.diff_study_stats(snap_a, snap_b_loaded)
    small_change = diff_df[(diff_df["metric"] == "patient_count") & (diff_df["data_type"] == "cgm")]
    assert not small_change["flagged"].any(), "1% change should not be flagged"
    assert (small_change["status"] == "changed").all()


# ── report ────────────────────────────────────────────────────────────────────

def test_report_generates_html(computed, tmp_path):
    """generate_report produces a non-empty HTML file with expected structure."""
    out = report_module.generate_report(
        computed["patient_df"],
        computed["patient_df"],
        computed["tdd_df"],
        cdf_df=computed["cdf_df"],
        output_path=tmp_path / "report.html",
    )
    assert out.exists(), f"Report file not found: {out}"
    assert out.stat().st_size > 5_000, "Report file is suspiciously small"
    content = out.read_text()
    assert "<html" in content.lower()
    assert "base64" in content, "No embedded figures found in report"
