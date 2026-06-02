import logging

import numpy as np
import pandas as pd

from babelbetes import tdd as tdd_module
from babelbetes.logger import Logger

log = Logger.get_logger(__name__, level=logging.INFO)
from babelbetes.studies.studydataset import StudyDataset as _SD

CDF_QUANTILES = np.linspace(0, 1, 401)  # 0.25% resolution

_VALUE_COL: dict[str, str] = {
    "cgm":   _SD.COL_NAME_CGM,
    "bolus": _SD.COL_NAME_BOLUS,
    "basal": _SD.COL_NAME_BASAL_RATE,
    "age":   _SD.COL_NAME_AGE,
}

GAP_THRESHOLDS = {
    "cgm":   pd.Timedelta(minutes=30),
    "basal": pd.Timedelta(hours=6),
    "bolus": pd.Timedelta(hours=16),
}



def _geometric_mean(x: np.ndarray) -> float:
    """Geometric mean of positive finite values."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) > 0 else float("nan")


def _geometric_std(x: np.ndarray) -> float:
    """Geometric std (multiplicative) of positive finite values."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.std(np.log(x)))) if len(x) > 1 else float("nan")


def _patient_metrics(series: pd.Series) -> dict:
    """Value and temporal stats for a single datetime-indexed measurement series.

    Args:
        series: Measurement values for one patient with a `datetime` index.

    Returns:
        Dict with keys `row_count`, `nan_count`, `duplicate_count`, `min`, `max`,
        `gm`, `gs`, `patient_days`, `data_fraction_days`, `missing_days`, `samples_per_day`.
    """
    v = series.dropna().values.astype(float)
    dates = series.index.normalize()
    span_days = max((dates.max() - dates.min()).days + 1, 1)
    patient_days = float(dates.nunique())
    return {
        "row_count":          float(len(series)),
        "nan_count":          float(series.isna().sum()),
        "duplicate_count":    float(series.index.duplicated().sum()),
        "min":                float(v.min()) if len(v) > 0 else np.nan,
        "max":                float(v.max()) if len(v) > 0 else np.nan,
        "gm":                 _geometric_mean(v),
        "gs":                 _geometric_std(v),
        "patient_days":       patient_days,
        "data_fraction_days": patient_days / span_days,
        "missing_days":       float(span_days - patient_days),
        "samples_per_day":    float(len(series) / span_days),
    }


def _chunk_gap_stats(dt: pd.Series, threshold: pd.Timedelta) -> dict:
    """Chunk and gap duration statistics for a single patient's datetime series.

    Args:
        dt: Datetime Series for one patient.
        threshold: Maximum gap within one continuous chunk.

    Returns:
        Dict with keys `data_fraction`, `chunk_count`, `gm_chunk_dur_hrs`,
        `gs_chunk_dur_hrs`, `gm_gap_dur_hrs`, `gs_gap_dur_hrs`.
    """
    dt = dt.sort_values()
    _nan = {
        "data_fraction": np.nan, "chunk_count": float(len(dt)),
        "gm_chunk_dur_hrs": np.nan, "gs_chunk_dur_hrs": np.nan,
        "gm_gap_dur_hrs": np.nan,   "gs_gap_dur_hrs": np.nan,
    }
    if len(dt) < 2:
        return _nan

    total_span = dt.iloc[-1] - dt.iloc[0]
    if total_span == pd.Timedelta(0):
        return {**_nan, "chunk_count": 1.0}

    group_ids = (dt.diff() > threshold).cumsum()
    chunks = dt.groupby(group_ids).agg(start="min", end="max")
    durations = (chunks["end"] - chunks["start"]) / pd.Timedelta("1h")
    gaps = ((chunks["start"].shift(-1) - chunks["end"]) / pd.Timedelta("1h")).dropna()

    return {
        "data_fraction":    float(durations.sum() / (total_span / pd.Timedelta("1h"))),
        "chunk_count":      float(len(durations)),
        "gm_chunk_dur_hrs": _geometric_mean(durations[durations > 0].values),
        "gs_chunk_dur_hrs": _geometric_std(durations[durations > 0].values),
        "gm_gap_dur_hrs":   _geometric_mean(gaps.values),
        "gs_gap_dur_hrs":   _geometric_std(gaps.values),
    }


def _cgm_patient_metrics(s: pd.Series) -> dict:
    """CGM metrics for a single datetime-indexed glucose series.

    Args:
        s: CGM values (mg/dL) for one patient with a `datetime` index.

    Returns:
        Dict with all keys from `_patient_metrics` and `_chunk_gap_stats`, plus
        `tir`, `tar`, `tbr`, `outlier_low`, `outlier_high`.
    """
    vals = s.dropna().values.astype(float)
    n = len(vals)
    return {
        **_patient_metrics(s),
        **_chunk_gap_stats(s.index.to_series(), GAP_THRESHOLDS["cgm"]),
        "tir":          float(np.sum((vals >= 70) & (vals <= 180)) / n) if n > 0 else np.nan,
        "tar":          float(np.sum(vals > 180) / n) if n > 0 else np.nan,
        "tbr":          float(np.sum(vals < 70) / n) if n > 0 else np.nan,
        "outlier_low":  float(np.sum(vals < 40)),
        "outlier_high": float(np.sum(vals > 400)),
    }


def _basal_patient_metrics(s: pd.Series) -> dict:
    """Basal stats for a single datetime-indexed basal rate series.

    Args:
        s: Basal rate values (U/hr) for one patient with a `datetime` index.

    Returns:
        Dict with all keys from `_patient_metrics` and `_chunk_gap_stats`.
    """
    return {**_patient_metrics(s), **_chunk_gap_stats(s.index.to_series(), GAP_THRESHOLDS["basal"])}


def _bolus_patient_metrics(s: pd.Series) -> dict:
    """Bolus stats for a single datetime-indexed bolus series.

    Args:
        s: Bolus values (U) for one patient with a `datetime` index.

    Returns:
        Dict with all keys from `_patient_metrics` and `_chunk_gap_stats`.
    """
    return {**_patient_metrics(s), **_chunk_gap_stats(s.index.to_series(), GAP_THRESHOLDS["bolus"])}


def _to_long(applied: pd.Series, data_type: str) -> list[dict]:
    """Convert a groupby.apply result (Series of dicts) to long-format records.

    Args:
        applied: Result of groupby(`study_name`, `patient_id`).apply(func_returning_dict).
        data_type: Value assigned to the `data_type` column in the output.

    Returns:
        List of dicts with keys `study`, `patient_id`, `data_type`, `metric`, `value`.
    """
    return (
        applied.apply(pd.Series)
               .reset_index()
               .melt(id_vars=["study_name", "patient_id"], var_name="metric", value_name="value")
               .rename(columns={"study_name": "study"})
               .assign(data_type=data_type)
               [["study", "patient_id", "data_type", "metric", "value"]]
               .to_dict("records")
    )


def compute_cgm_stats(df: pd.DataFrame) -> list[dict]:
    """Per-patient CGM stats: value metrics, temporal coverage, TIR/TAR/TBR, and outliers.

    Args:
        df: CGM DataFrame. Required columns: `study_name`, `patient_id`, `datetime`, `cgm`.

    Returns:
        Long-format records with columns `study`, `patient_id`, `data_type`=`cgm`,
        `metric`, `value`. Metrics: `row_count`, `nan_count`, `duplicate_count`, `min`,
        `max`, `gm`, `gs`, `patient_days`, `data_fraction_days`, `missing_days`,
        `samples_per_day`, `data_fraction`, `chunk_count`, `gm_chunk_dur_hrs`,
        `gs_chunk_dur_hrs`, `gm_gap_dur_hrs`, `gs_gap_dur_hrs`, `tir`, `tar`, `tbr`,
        `outlier_low`, `outlier_high`.
    """
    return _to_long(
        df.groupby(["study_name", "patient_id"], observed=True).apply(
            lambda g: _cgm_patient_metrics(g.set_index("datetime")["cgm"]),
            include_groups=False,
        ),
        "cgm",
    )


def compute_basal_stats(df: pd.DataFrame) -> list[dict]:
    """Per-patient basal stats: value metrics and temporal coverage.

    Args:
        df: Basal DataFrame. Required columns: `study_name`, `patient_id`, `datetime`,
            `basal_rate`.

    Returns:
        Long-format records with columns `study`, `patient_id`, `data_type`=`basal`,
        `metric`, `value`. Metrics: `row_count`, `nan_count`, `duplicate_count`, `min`,
        `max`, `gm`, `gs`, `patient_days`, `data_fraction_days`, `missing_days`,
        `samples_per_day`, `data_fraction`, `chunk_count`, `gm_chunk_dur_hrs`,
        `gs_chunk_dur_hrs`, `gm_gap_dur_hrs`, `gs_gap_dur_hrs`.
    """
    return _to_long(
        df.groupby(["study_name", "patient_id"], observed=True).apply(
            lambda g: _basal_patient_metrics(g.set_index("datetime")["basal_rate"]),
            include_groups=False,
        ),
        "basal",
    )


def compute_bolus_stats(df: pd.DataFrame) -> list[dict]:
    """Per-patient bolus stats: value metrics and temporal coverage.

    Args:
        df: Bolus DataFrame. Required columns: `study_name`, `patient_id`, `datetime`,
            `bolus`.

    Returns:
        Long-format records with columns `study`, `patient_id`, `data_type`=`bolus`,
        `metric`, `value`. Metrics: `row_count`, `nan_count`, `duplicate_count`, `min`,
        `max`, `gm`, `gs`, `patient_days`, `data_fraction_days`, `missing_days`,
        `samples_per_day`, `data_fraction`, `chunk_count`, `gm_chunk_dur_hrs`,
        `gs_chunk_dur_hrs`, `gm_gap_dur_hrs`, `gs_gap_dur_hrs`.
    """
    return _to_long(
        df.groupby(["study_name", "patient_id"], observed=True).apply(
            lambda g: _bolus_patient_metrics(g.set_index("datetime")["bolus"]),
            include_groups=False,
        ),
        "bolus",
    )


def compute_complete_days(store: dict[str, pd.DataFrame]) -> list[dict]:
    """Per-patient count of days where CGM, bolus, and basal all have at least one sample.

    Args:
        store: Dict mapping data type to DataFrame. Uses keys `cgm`, `bolus`, `basal`.
               Each DataFrame must have columns `study_name`, `patient_id`, `datetime`.

    Returns:
        Long-format records with columns `study`, `patient_id`, `data_type`=`all`,
        `metric`=`complete_days`, `value`. Empty list if any of `cgm`/`bolus`/`basal`
        is missing from the store.
    """
    if not {"cgm", "bolus", "basal"}.issubset(store):
        return []

    combined = pd.concat([
        store["cgm"].groupby(["study_name", "patient_id", store["cgm"]["datetime"].dt.date]).size(),
        store["bolus"].groupby(["study_name", "patient_id", store["bolus"]["datetime"].dt.date]).size(),
        store["basal"].groupby(["study_name", "patient_id", store["basal"]["datetime"].dt.date]).size(),
    ], axis=1, join="outer", keys=["cgm", "bolus", "basal"])
    combined.index.names = ["study", "patient_id", "date"]
    combined["complete"] = combined[["cgm", "bolus", "basal"]].notna().all(axis=1)

    return (
        combined.reset_index()
        .groupby(["study", "patient_id"], observed=True)["complete"]
        .sum().reset_index()
        .rename(columns={"complete": "value"})
        .assign(data_type="complete", metric="complete_days")
        [["study", "patient_id", "data_type", "metric", "value"]]
        .astype({"value": float})
        .to_dict("records")
    )


def compute_tdd_per_patient(store: dict[str, pd.DataFrame], verbose: bool = False) -> pd.DataFrame:
    """Daily Total Daily Dose (TDD) per patient for each study.

    Requires both `bolus` and `basal` keys in the store.

    Args:
        store: Dict mapping data type to DataFrame. Uses keys `bolus` and `basal`.
               Each DataFrame must have a `study_name` column.
        verbose: Print per-study progress.

    Returns:
        Wide DataFrame with columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`.
    """
    if "bolus" not in store or "basal" not in store:
        return pd.DataFrame(columns=["study", "patient_id", "date", "basal", "bolus", "total"])

    bolus_by_study = dict(list(store["bolus"].groupby("study_name", observed=True)))
    basal_by_study = dict(list(store["basal"].groupby("study_name", observed=True)))
    studies = list(bolus_by_study)

    frames = []
    for i, study in enumerate(studies, 1):
        if verbose:
            log.info("  [%d/%d] %s", i, len(studies), study)
        try:
            tdd_df = tdd_module.calculate_tdd(
                bolus_by_study[study],
                basal_by_study.get(study, store["basal"].iloc[:0]),
            ).reset_index()
            tdd_df["total"] = tdd_df["basal"] + tdd_df["bolus"]
            tdd_df["study"] = study
            frames.append(tdd_df)
        except Exception as e:
            log.warning("TDD failed for %s: %s", study, e)

    if not frames:
        return pd.DataFrame(columns=["study", "patient_id", "date", "basal", "bolus", "total"])
    return pd.concat(frames, ignore_index=True)[["study", "patient_id", "date", "basal", "bolus", "total"]]


def compute_tdd_stats(tdd_df: pd.DataFrame) -> list[dict]:
    """Per-patient TDD statistics: gm, gs, min, max, nan_count for basal, bolus, total, and ratio.

    Args:
        tdd_df: Wide DataFrame from `compute_tdd_per_patient`. Required columns:
                `study`, `patient_id`, `date`, `basal`, `bolus`, `total`.

    Returns:
        Long-format records with columns `study`, `patient_id`, `data_type`=`tdd`,
        `metric`, `value`. Metrics: `basal_gm`, `basal_gs`, `basal_min`, `basal_max`,
        `basal_nan_count`, `bolus_gm`, `bolus_gs`, `bolus_min`, `bolus_max`,
        `bolus_nan_count`, `tdd_gm`, `tdd_gs`, `tdd_min`, `tdd_max`, `tdd_nan_count`,
        `bolus_basal_ratio`.
    """
    if tdd_df.empty:
        return []

    records = []
    for (study, patient_id), grp in tdd_df.groupby(["study", "patient_id"], observed=True):
        base = {"study": study, "patient_id": patient_id, "data_type": "tdd"}

        for prefix, col in [("basal", "basal"), ("bolus", "bolus"), ("tdd", "total")]:
            vals = grp[col].dropna().values
            records += [
                {**base, "metric": f"{prefix}_gm",        "value": _geometric_mean(vals)},
                {**base, "metric": f"{prefix}_gs",        "value": _geometric_std(vals)},
                {**base, "metric": f"{prefix}_min",       "value": float(vals.min()) if len(vals) > 0 else np.nan},
                {**base, "metric": f"{prefix}_max",       "value": float(vals.max()) if len(vals) > 0 else np.nan},
                {**base, "metric": f"{prefix}_nan_count", "value": float(grp[col].isna().sum())},
            ]

        basal_mean = grp["basal"].dropna().mean()
        bolus_mean = grp["bolus"].dropna().mean()
        ratio = float(bolus_mean / basal_mean) if (pd.notna(basal_mean) and basal_mean != 0) else np.nan
        records.append({**base, "metric": "bolus_basal_ratio", "value": ratio})

    return records


def compute_cdf_quantiles(store: dict[str, pd.DataFrame], verbose: bool = False) -> pd.DataFrame:
    """Pre-compute CDF quantiles per study for CGM, bolus, and basal.

    Args:
        store: Dict mapping data type to DataFrame. Uses keys `cgm`, `bolus`, `basal`.
               Each DataFrame must have a `study_name` column.
        verbose: Print per-data-type progress.

    Returns:
        DataFrame with columns `study`, `data_type`, `quantile_level`, `value`.
        401 rows per (`study`, `data_type`) pair (0–100% at 0.25% steps).
    """
    configs = [
        ("cgm",   _SD.COL_NAME_CGM,       False),
        ("bolus", _SD.COL_NAME_BOLUS,      True),
        ("basal", _SD.COL_NAME_BASAL_RATE, False),
    ]
    frames = []
    for data_type, col, exclude_zeros in configs:
        if data_type not in store:
            continue
        if verbose:
            log.info("  %s", data_type)
        df = store[data_type][[col, "study_name"]].dropna()
        if exclude_zeros:
            df = df[df[col] > 0]
        for study, group in df.groupby("study_name", observed=True):
            frames.append(pd.DataFrame({
                "study":          study,
                "data_type":      data_type,
                "quantile_level": CDF_QUANTILES,
                "value":          np.quantile(group[col].to_numpy(), CDF_QUANTILES),
            }))
    if not frames:
        return pd.DataFrame(columns=["study", "data_type", "quantile_level", "value"])
    return pd.concat(frames, ignore_index=True)


def compute_age_stats(store: dict[str, pd.DataFrame]) -> list[dict]:
    """Study-level age statistics: min, max, geometric mean, and std.

    Args:
        store: Dict mapping data type to DataFrame. Uses the `age` key.
               The DataFrame must have columns `study_name` and `age`.

    Returns:
        List of dicts with keys `study`, `data_type`=`age`, `metric`, `value`.
        Metrics: `age_min`, `age_max`, `age_gm`, `age_std`.
    """
    if "age" not in store:
        return []
    df = store["age"]
    col = _VALUE_COL["age"]
    if col not in df.columns:
        return []

    records = []
    for study, grp in df.groupby("study_name", observed=True):
        vals = grp[col].dropna().values
        if len(vals) == 0:
            continue
        for metric, value in [
            ("age_min", float(vals.min())),
            ("age_max", float(vals.max())),
            ("age_gm",  _geometric_mean(vals)),
            ("age_std", float(vals.std())),
        ]:
            records.append({"study": study, "data_type": "age", "metric": metric, "value": value})

    return records


def compute_gap_durations(store: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Raw gap and chunk durations per patient for CDF plotting.

    Args:
        store: Dict mapping data type to DataFrame. Uses keys `cgm`, `basal`, `bolus`.
               Each DataFrame must have columns `study_name`, `patient_id`, `datetime`.

    Returns:
        Dict keyed by data type. Each value is a DataFrame with columns `study`,
        `patient_id`, `kind` (`gap` or `chunk`), `dur_hrs`.
    """
    result = {}
    for data_type in ("cgm", "basal", "bolus"):
        if data_type not in store:
            continue
        df = store[data_type]
        threshold = GAP_THRESHOLDS[data_type]
        rows = []
        for (study, patient_id), pat_df in df.groupby(
            ["study_name", _SD.COL_NAME_PATIENT_ID], observed=True
        ):
            dt = pat_df[_SD.COL_NAME_DATETIME].sort_values()
            if len(dt) < 2:
                continue
            group_ids = (dt.diff() > threshold).cumsum()
            chunks = dt.groupby(group_ids).agg(start="min", end="max")
            chunk_durs = ((chunks["end"] - chunks["start"]) / pd.Timedelta(hours=1)).values
            gap_durs = ((chunks["start"].shift(-1) - chunks["end"]) / pd.Timedelta(hours=1)).dropna().values

            for dur in chunk_durs:
                rows.append({"study": study, "patient_id": patient_id,
                             "kind": "chunk", "dur_hrs": float(dur)})
            for dur in gap_durs:
                rows.append({"study": study, "patient_id": patient_id,
                             "kind": "gap", "dur_hrs": float(dur)})

        if rows:
            result[data_type] = pd.DataFrame(rows)
    return result


def aggregate_study_stats(patient_stats_df: pd.DataFrame) -> list[dict]:
    """Aggregate per-patient stats to study level using vectorised groupby.

    Every per-patient metric is aggregated to geometric mean and std across
    patients, producing two output metrics suffixed `_study_gm` / `_study_gs`.
    For example, `row_count` becomes `row_count_study_gm` and `row_count_study_gs`
    — it is **not** summed, so it does not give the total row count for the study.
    To get study-level totals, use the explicitly summed metrics below.

    Explicitly summed (appear without a suffix):

    - `patient_days` — total patient-days across all patients per `data_type`
    - `complete_days` — total complete patient-days (CGM + bolus + basal) per patient

    Always present (never NaN):

    - `patient_count` — number of patients in each (`study`, `data_type`) group

    May be NaN and are dropped from the output:

    - `_study_gs` for any metric where a study has only one patient (std undefined)
    - `_study_gm` for any metric that is zero or negative for all patients
      (geometric mean requires positive values; e.g. `duplicate_count_study_gm`
      is absent when no patient has any duplicates)

    Args:
        patient_stats_df: DataFrame with columns `study`, `patient_id`, `data_type`,
                          `metric`, `value`.

    Returns:
        List of dicts with keys `study`, `data_type`, `metric`, `value`
        (no `patient_id` column). NaN values are dropped.
    """
    # Pivot to wide: one row per patient, one column per metric.
    wide = patient_stats_df.pivot_table(
        index=["study", "data_type", "patient_id"],
        columns="metric",
        values="value",
    ).reset_index(["study", "data_type"])
    grp = wide.groupby(["study", "data_type"])

    gm = grp.agg(_geometric_mean).add_suffix("_study_gm")
    gs = grp.agg(_geometric_std).add_suffix("_study_gs")
    
    # Each row is one patient, so size() == patient_count
    patient_count = grp.size().rename("patient_count")
    gm_records = (
        gm.join(gs).join(patient_count)
        .reset_index()
        .melt(id_vars=["study", "data_type"], var_name="metric", value_name="value")
        .dropna(subset=["value"])
    )

    # Total patient_days per (study, data_type) and total complete_days
    total_records = (
        patient_stats_df[patient_stats_df["metric"].isin({"patient_days", 
                                                          "complete_days",
                                                          #"row_count"
                                                          })]
        .groupby(["study", "data_type", "metric"], observed=True)["value"]
        .sum().reset_index()
    )

    return pd.concat([gm_records, total_records], ignore_index=True).to_dict("records")
