import numpy as np
import pandas as pd

from babelbetes.src import pandas_helper, tdd as tdd_module
from babelbetes.studies.studydataset import StudyDataset as _SD

CDF_QUANTILES = np.linspace(0, 1, 401)  # 0.25% resolution

# Maps store key → primary value column, as defined in StudyDataset
_VALUE_COL: dict[str, str] = {
    "cgm":   _SD.COL_NAME_CGM,        # "cgm"
    "bolus": _SD.COL_NAME_BOLUS,       # "bolus"
    "basal": _SD.COL_NAME_BASAL_RATE,  # "basal_rate"
    "age":   _SD.COL_NAME_AGE,         # "age"
}

# Gap threshold that starts a new continuous chunk per data type
GAP_THRESHOLDS = {
    "cgm":   pd.Timedelta(minutes=30),
    "basal": pd.Timedelta(hours=6),
    "bolus": pd.Timedelta(hours=16),
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _geometric_mean(x: np.ndarray) -> float:
    """Geometric mean of positive finite values."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) > 0 else float("nan")


def _geometric_std(x: np.ndarray) -> float:
    """Geometric std (multiplicative) of positive finite values."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.std(np.log(x)))) if len(x) > 1 else float("nan")


def _chunk_gap_stats(df: pd.DataFrame, threshold: pd.Timedelta) -> dict:
    """Chunk/gap statistics for a single patient DataFrame.

    Args:
        df:        Must have a 'datetime' column.
        threshold: Maximum gap within one chunk.

    Returns:
        Dict: data_fraction, chunk_count, gm/gs_chunk_dur_hrs, gm/gs_gap_dur_hrs.
    """
    dt = df["datetime"].sort_values()
    _nan = dict(
        data_fraction=np.nan, chunk_count=len(dt),
        gm_chunk_dur_hrs=np.nan, gs_chunk_dur_hrs=np.nan,
        gm_gap_dur_hrs=np.nan,   gs_gap_dur_hrs=np.nan,
    )
    if len(dt) < 2:
        return _nan

    total_span = (dt.iloc[-1] - dt.iloc[0]) / pd.Timedelta(hours=1)
    if total_span == 0:
        return {**_nan, "chunk_count": 1}

    group_ids   = pandas_helper.split_groups(dt, threshold)
    groups      = dt.groupby(group_ids)
    chunk_starts = groups.min()
    chunk_ends   = groups.max()

    chunk_dur_hrs = ((chunk_ends - chunk_starts) / pd.Timedelta(hours=1)).values
    gap_dur_hrs   = (chunk_starts.values[1:] - chunk_ends.values[:-1]) / np.timedelta64(1, "h")

    return {
        "data_fraction":    float(chunk_dur_hrs.sum() / total_span),
        "chunk_count":      int(len(chunk_starts)),
        "gm_chunk_dur_hrs": _geometric_mean(chunk_dur_hrs[chunk_dur_hrs > 0]),
        "gs_chunk_dur_hrs": _geometric_std(chunk_dur_hrs[chunk_dur_hrs > 0]),
        "gm_gap_dur_hrs":   _geometric_mean(gap_dur_hrs),
        "gs_gap_dur_hrs":   _geometric_std(gap_dur_hrs),
    }


# ── public functions ───────────────────────────────────────────────────────────

def compute_cdf_quantiles(store: dict[str, pd.DataFrame], verbose: bool = False) -> pd.DataFrame:
    """Pre-compute CDF quantiles per study for CGM, bolus, and basal.

    Args:
        store:   Flat dict {data_type: DataFrame} with a 'study_name' column.
        verbose: Print per data_type progress.

    Returns:
        DataFrame with columns [study, data_type, quantile_level, value].
        401 rows per (study, data_type) pair (0–100% at 0.25% steps).
    """
    configs = [
        ("cgm",   _SD.COL_NAME_CGM,       False),
        ("bolus", _SD.COL_NAME_BOLUS,      True),   # exclude zeros for log-scale
        ("basal", _SD.COL_NAME_BASAL_RATE, False),
    ]
    frames = []
    for data_type, col, exclude_zeros in configs:
        if data_type not in store:
            continue
        if verbose:
            print(f"  {data_type}")
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


def compute_basic_stats(store: dict[str, pd.DataFrame], verbose: bool = False) -> list[dict]:
    """Scalar study-level statistics for each study/data_type.

    Metrics: row_count, patient_count, nan_count, nan_pct.

    Args:
        store:   Flat dict {data_type: DataFrame} with a 'study_name' column.
        verbose: Print per data_type progress.

    Returns:
        List of {study, data_type, metric, value} dicts.
    """
    frames = []
    for data_type, df in store.items():
        if verbose:
            print(f"  {data_type}")
        col = _VALUE_COL.get(data_type)
        grp = df.groupby("study_name", observed=True)

        stats = pd.DataFrame({
            "row_count":     grp.size(),
            "patient_count": grp[_SD.COL_NAME_PATIENT_ID].nunique(),
        })
        if col and col in df.columns:
            stats["nan_count"] = df[col].isna().groupby(df["study_name"], observed=True).sum().astype(float)
            stats["nan_pct"]   = stats["nan_count"] / stats["row_count"] * 100

        melted = (
            stats.astype(float)
                 .reset_index()
                 .rename(columns={"study_name": "study"})
                 .melt(id_vars="study", var_name="metric", value_name="value")
        )
        melted["data_type"] = data_type
        frames.append(melted[["study", "data_type", "metric", "value"]])

    return pd.concat(frames, ignore_index=True).to_dict("records")


def compute_patient_stats(store: dict[str, pd.DataFrame], verbose: bool = False) -> list[dict]:
    """Per-patient statistics for each study/data_type.

    Scalar metrics (vectorized): gm, gs, min, max, nan_count.
    Temporal metrics (per patient): data_fraction, chunk_count,
        gm/gs_chunk_dur_hrs, gm/gs_gap_dur_hrs. Skipped for 'age'.

    Args:
        store:   Flat dict {data_type: DataFrame} with a 'study_name' column.
        verbose: Print per-study progress for chunk stats.

    Returns:
        List of {study, patient_id, data_type, metric, value} dicts.
    """
    all_frames = []

    for data_type, df in store.items():
        col = _VALUE_COL.get(data_type)
        if not col or col not in df.columns:
            continue
        if verbose:
            print(f"  {data_type}: scalar stats")

        grp = df.groupby(["study_name", _SD.COL_NAME_PATIENT_ID], observed=True)

        scalar = pd.DataFrame({
            "min":       grp[col].min(),
            "max":       grp[col].max(),
            "nan_count": df[col].isna().groupby([df["study_name"], df[_SD.COL_NAME_PATIENT_ID]], observed=True).sum().astype(float),
            "gm":        grp[col].apply(lambda s: _geometric_mean(s.values)),
            "gs":        grp[col].apply(lambda s: _geometric_std(s.values)),
        }).reset_index().rename(columns={"study_name": "study"})

        melted = scalar.melt(
            id_vars=["study", _SD.COL_NAME_PATIENT_ID],
            var_name="metric", value_name="value",
        )
        melted["data_type"] = data_type
        all_frames.append(melted)

        if data_type == "age" or _SD.COL_NAME_DATETIME not in df.columns:
            continue

        # Chunk/gap stats — sequential per patient; show per-study progress
        threshold = GAP_THRESHOLDS[data_type]
        chunk_records = []
        studies = df["study_name"].unique()
        for i, (study, study_df) in enumerate(df.groupby("study_name", observed=True), 1):
            if verbose:
                print(f"  {data_type}: chunk stats [{i}/{len(studies)}] {study}")
            for patient_id, pat_df in study_df.groupby(_SD.COL_NAME_PATIENT_ID, observed=True):
                for k, v in _chunk_gap_stats(pat_df, threshold).items():
                    chunk_records.append({
                        "study": study, "patient_id": patient_id,
                        "data_type": data_type, "metric": k, "value": float(v),
                    })
        if chunk_records:
            all_frames.append(pd.DataFrame(chunk_records))

    if not all_frames:
        return []
    return pd.concat(all_frames, ignore_index=True).to_dict("records")


def compute_tdd_per_patient(store: dict[str, pd.DataFrame], verbose: bool = False) -> pd.DataFrame:
    """Daily Total Daily Dose (TDD) per patient for each study.

    Requires both 'bolus' and 'basal' keys in the store.

    Args:
        store:   Flat dict {data_type: DataFrame} with a 'study_name' column.
        verbose: Print per-study progress.

    Returns:
        Wide DataFrame with columns: study, patient_id, date, basal, bolus, total.
    """
    if "bolus" not in store or "basal" not in store:
        return pd.DataFrame(columns=["study", "patient_id", "date", "basal", "bolus", "total"])

    bolus_by_study = dict(list(store["bolus"].groupby("study_name", observed=True)))
    basal_by_study = dict(list(store["basal"].groupby("study_name", observed=True)))
    studies = list(bolus_by_study)

    frames = []
    for i, study in enumerate(studies, 1):
        if verbose:
            print(f"  [{i}/{len(studies)}] {study}")
        try:
            tdd_df = tdd_module.calculate_tdd(
                bolus_by_study[study],
                basal_by_study.get(study, store["basal"].iloc[:0]),
            ).reset_index()
            tdd_df["total"] = tdd_df["basal"].fillna(0) + tdd_df["bolus"].fillna(0)
            tdd_df["study"] = study
            frames.append(tdd_df)
        except Exception as e:
            print(f"  Warning: TDD failed for {study}: {e}")

    if not frames:
        return pd.DataFrame(columns=["study", "patient_id", "date", "basal", "bolus", "total"])
    return pd.concat(frames, ignore_index=True)[["study", "patient_id", "date", "basal", "bolus", "total"]]


def compute_study_stats_extended(store: dict[str, pd.DataFrame], verbose: bool = False) -> list[dict]:
    """Extended study-level statistics (supplements compute_basic_stats).

    Adds:
      - patient_days per data_type (cgm/bolus/basal): unique days with ≥1 sample
      - patient_days (data_type="all"): complete days where CGM + bolus + basal all present
      - patient_count (data_type="all"): patients with ≥1 complete day
      - duplicate_count per data_type

    Args:
        store:   Flat dict {data_type: DataFrame} with a 'study_name' column.
        verbose: Print step progress.

    Returns:
        List of {study, data_type, metric, value} dicts.
    """
    records = []

    # Duplicate counts — vectorized: duplicated() on full df, then groupby sum
    if verbose:
        print("  duplicate counts")
    for dt, df in store.items():
        is_dup = df.duplicated()
        for study, count in is_dup.groupby(df["study_name"], observed=True).sum().items():
            records.append({"study": study, "data_type": dt, "metric": "duplicate_count", "value": float(count)})

    # Patient-days — all studies at once, one groupby per data_type
    if verbose:
        print("  patient-days")
    presence: dict[str, pd.Series] = {}
    for dt in ("cgm", "bolus", "basal"):
        if dt not in store:
            continue
        df = store[dt]
        presence[dt] = (
            df.groupby(["study_name", _SD.COL_NAME_PATIENT_ID, df[_SD.COL_NAME_DATETIME].dt.normalize()], observed=True)
              .size()
              .rename(dt)
        )

    if presence:
        combined = pd.concat(presence.values(), axis=1, join="outer")
        combined.index.names = ["study", "patient_id", "date"]
        combined = combined.reset_index()

        # A complete day requires all three data types to be present
        complete_cols = [dt for dt in ("cgm", "bolus", "basal") if dt in presence]
        combined["complete"] = (
            combined[complete_cols].notna().all(axis=1)
            if set(complete_cols) == {"cgm", "bolus", "basal"}
            else False
        )

        # Patient-days per data_type
        for dt in presence:
            for study, days in combined.groupby("study", observed=True)[dt].count().items():
                records.append({"study": study, "data_type": dt, "metric": "patient_days", "value": float(days)})

        # Complete days and patients per study
        complete_per_patient = (
            combined.groupby(["study", "patient_id"], observed=True)["complete"]
                    .sum()
                    .reset_index()
        )
        for study, grp in complete_per_patient.groupby("study", observed=True):
            records.append({"study": study, "data_type": "all", "metric": "patient_days",  "value": float(grp["complete"].sum())})
            records.append({"study": study, "data_type": "all", "metric": "patient_count", "value": float((grp["complete"] > 0).sum())})

    return records
