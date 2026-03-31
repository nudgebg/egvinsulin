import numpy as np
import pandas as pd

from babelbetes.src import pandas_helper, tdd as tdd_module

# Maps data_type name to its primary value column
VALUE_COLUMNS = {
    "cgm": "cgm",
    "bolus": "bolus",
    "basal": "basal_rate",
    "age": "age",
}

# Gap thresholds for chunk/gap analysis: a new chunk starts when the gap exceeds this
GAP_THRESHOLDS = {
    "cgm":   pd.Timedelta(minutes=30),
    "basal": pd.Timedelta(hours=6),
    "bolus": pd.Timedelta(hours=16),
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _geometric_mean(x: np.ndarray) -> float:
    """Geometric mean of positive values (NaN and ≤0 excluded)."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) > 0 else float("nan")


def _geometric_std(x: np.ndarray) -> float:
    """Geometric std (multiplicative) of positive values."""
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.std(np.log(x)))) if len(x) > 1 else float("nan")


def _chunk_gap_stats(df: pd.DataFrame, threshold: pd.Timedelta) -> dict:
    """Compute chunk/gap statistics for a single patient/data_type DataFrame.

    Args:
        df: Must have a 'datetime' column, sorted ascending.
        threshold: Maximum gap between consecutive readings within one chunk.

    Returns:
        Dict with keys: data_fraction, chunk_count,
        gm_chunk_dur_hrs, gs_chunk_dur_hrs, gm_gap_dur_hrs, gs_gap_dur_hrs
    """
    df = df.sort_values("datetime").reset_index(drop=True)
    if len(df) < 2:
        return {
            "data_fraction": float("nan"),
            "chunk_count": len(df),
            "gm_chunk_dur_hrs": float("nan"),
            "gs_chunk_dur_hrs": float("nan"),
            "gm_gap_dur_hrs": float("nan"),
            "gs_gap_dur_hrs": float("nan"),
        }

    total_span = (df["datetime"].iloc[-1] - df["datetime"].iloc[0]).total_seconds() / 3600
    if total_span == 0:
        return {
            "data_fraction": float("nan"),
            "chunk_count": 1,
            "gm_chunk_dur_hrs": float("nan"),
            "gs_chunk_dur_hrs": float("nan"),
            "gm_gap_dur_hrs": float("nan"),
            "gs_gap_dur_hrs": float("nan"),
        }

    group_ids = pandas_helper.split_groups(df["datetime"], threshold)
    groups = df.groupby(group_ids)["datetime"]
    chunk_starts = groups.min()
    chunk_ends   = groups.max()

    chunk_dur_hrs = ((chunk_ends - chunk_starts).dt.total_seconds() / 3600).values
    # Exclude zero-duration chunks (single readings) from gm/gs
    nonzero_chunks = chunk_dur_hrs[chunk_dur_hrs > 0]

    # Gaps: time between consecutive chunks
    gap_dur_hrs = ((chunk_starts.values[1:] - chunk_ends.values[:-1]) /
                   np.timedelta64(1, "h"))

    return {
        "data_fraction": float(chunk_dur_hrs.sum() / total_span),
        "chunk_count": int(len(chunk_starts)),
        "gm_chunk_dur_hrs": _geometric_mean(nonzero_chunks),
        "gs_chunk_dur_hrs": _geometric_std(nonzero_chunks),
        "gm_gap_dur_hrs": _geometric_mean(gap_dur_hrs),
        "gs_gap_dur_hrs": _geometric_std(gap_dur_hrs),
    }


# ── public functions ───────────────────────────────────────────────────────────

def compute_basic_stats(store: dict[str, dict[str, pd.DataFrame]]) -> list[dict]:
    """Compute scalar study-level statistics for each study/data_type.

    Args:
        store: Nested dict {study_name: {data_type: DataFrame}}

    Returns:
        List of records with keys: study, data_type, metric, value.
        Intended to be saved as *_stats.parquet via snapshot.save_stats().
    """
    records = []
    for study, data_types in store.items():
        for data_type, df in data_types.items():
            row_count = len(df)
            patient_count = int(df["patient_id"].nunique()) if "patient_id" in df.columns else None

            def add(metric, value, _study=study, _dt=data_type):
                records.append({"study": _study, "data_type": _dt, "metric": metric, "value": float(value)})

            add("row_count", row_count)
            if patient_count is not None:
                add("patient_count", patient_count)

            value_col = VALUE_COLUMNS.get(data_type)
            if value_col and value_col in df.columns:
                nan_count = int(df[value_col].isna().sum())
                nan_pct = nan_count / row_count * 100 if row_count > 0 else 0.0
                add("nan_count", nan_count)
                add("nan_pct", nan_pct)

    return records


def compute_patient_stats(store: dict[str, dict[str, pd.DataFrame]]) -> list[dict]:
    """Compute per-patient statistics for each study/data_type.

    For each (study, patient_id, data_type) computes:
      - gm, gs (geometric mean/std of the value column, positive values only)
      - min, max, nan_count
      - data_fraction, chunk_count, gm_chunk_dur_hrs, gs_chunk_dur_hrs,
        gm_gap_dur_hrs, gs_gap_dur_hrs  (skipped for 'age')

    Returns:
        List of {study, patient_id, data_type, metric, value} dicts.
        Saved as *_patient_stats.parquet via snapshot.save_patient_stats().
    """
    records = []

    for study, data_types in store.items():
        for data_type, df in data_types.items():
            value_col = VALUE_COLUMNS.get(data_type)
            if value_col not in df.columns:
                continue

            for patient_id, pat_df in df.groupby("patient_id", observed=True):

                def add(metric, value, _s=study, _p=patient_id, _dt=data_type):
                    records.append({
                        "study": _s,
                        "patient_id": _p,
                        "data_type": _dt,
                        "metric": metric,
                        "value": float(value) if value is not None else float("nan"),
                    })

                vals = pat_df[value_col].dropna().values
                add("gm",        _geometric_mean(vals))
                add("gs",        _geometric_std(vals))
                add("min",       float(vals.min())       if len(vals) > 0 else float("nan"))
                add("max",       float(vals.max())       if len(vals) > 0 else float("nan"))
                add("nan_count", int(pat_df[value_col].isna().sum()))

                # Temporal / chunk analysis (not meaningful for age)
                if data_type != "age" and "datetime" in pat_df.columns:
                    threshold = GAP_THRESHOLDS[data_type]
                    cg = _chunk_gap_stats(pat_df[["datetime"]], threshold)
                    for k, v in cg.items():
                        add(k, v)

    return records


def compute_tdd_per_patient(store: dict[str, dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """Compute daily Total Daily Dose (TDD) per patient for each study.

    Requires both 'bolus' and 'basal' data_types in the store.

    Returns:
        Wide DataFrame with columns: study, patient_id, date, basal, bolus, total.
        Saved as *_tdd.parquet via snapshot.save_tdd().
    """
    frames = []
    for study, data_types in store.items():
        if "bolus" not in data_types or "basal" not in data_types:
            continue
        df_bolus = data_types["bolus"]
        df_basal  = data_types["basal"]
        try:
            tdd_df = tdd_module.calculate_tdd(df_bolus, df_basal)
            tdd_df = tdd_df.reset_index()
            tdd_df["total"] = tdd_df["basal"].fillna(0) + tdd_df["bolus"].fillna(0)
            tdd_df["study"] = study
            frames.append(tdd_df)
        except Exception as e:
            print(f"  Warning: TDD failed for {study}: {e}")

    if not frames:
        return pd.DataFrame(columns=["study", "patient_id", "date", "basal", "bolus", "total"])
    return pd.concat(frames, ignore_index=True)[["study", "patient_id", "date", "basal", "bolus", "total"]]


def compute_study_stats_extended(
    store: dict[str, dict[str, pd.DataFrame]],
    patient_stats_df: pd.DataFrame,
) -> list[dict]:
    """Compute extended study-level statistics (supplements compute_basic_stats).

    Adds:
      - complete_patient_count (patients with CGM + bolus + basal)
      - patient_days_{cgm,bolus,basal,complete}
      - duplicate_count (exact duplicate rows per data_type)
      - gm_of_patient_gm, gs_of_patient_gm (study-level summary of per-patient gm)

    Args:
        store: Nested dict {study_name: {data_type: DataFrame}}
        patient_stats_df: DataFrame from compute_patient_stats(), for gm aggregation.

    Returns:
        List of {study, data_type, metric, value} dicts (data_type='all' for cross-type metrics).
    """
    records = []

    for study, data_types in store.items():

        def add(metric, value, data_type="all", _s=study):
            records.append({"study": _s, "data_type": data_type, "metric": metric, "value": float(value)})

        # ── patient_days per data_type + complete patient-days ────────────────
        # A day counts for a data_type only if the patient has ≥1 sample that day.
        # A "complete" day requires ≥1 sample of CGM, bolus, AND basal on that day.
        #
        # Approach: count samples per (patient_id, date) for each data_type,
        # outer-join them, then a complete day = no NaN across all three columns.
        counts = {}
        for data_type in ("cgm", "bolus", "basal"):
            if data_type not in data_types or "datetime" not in data_types[data_type].columns:
                continue
            df = data_types[data_type]
            counts[data_type] = (
                df.groupby(["patient_id", df["datetime"].dt.date], observed=True)
                .size()
                .rename(data_type)
            )

        if counts:
            combined = pd.concat(counts.values(), axis=1, join="outer")
            combined.index.names = ["patient_id", "date"]

            for data_type in ("cgm", "bolus", "basal"):
                if data_type in combined.columns:
                    add("patient_days", int(combined[data_type].notna().sum()), data_type=data_type)

            if set(counts.keys()) == {"cgm", "bolus", "basal"}:
                complete_mask = combined[["cgm", "bolus", "basal"]].notna().all(axis=1)
                add("patient_days_complete", int(complete_mask.sum()))

                # complete_patient_count: patients with ≥1 complete day
                complete_patients = set(combined.index.get_level_values("patient_id")[complete_mask])
                add("complete_patient_count", len(complete_patients))
            else:
                complete_patients = set()

        # ── duplicate_count per data_type ─────────────────────────────────────
        for data_type, df in data_types.items():
            dup_count = int(df.duplicated().sum())
            add("duplicate_count", dup_count, data_type=data_type)

        # ── gm / gs of per-patient gm values ──────────────────────────────────
        if not patient_stats_df.empty:
            for data_type in data_types:
                mask = (
                    (patient_stats_df["study"] == study) &
                    (patient_stats_df["data_type"] == data_type) &
                    (patient_stats_df["metric"] == "gm")
                )
                gm_vals = patient_stats_df.loc[mask, "value"].dropna().values
                add("gm_of_patient_gm", _geometric_mean(gm_vals), data_type=data_type)
                add("gs_of_patient_gm", _geometric_std(gm_vals),  data_type=data_type)

    return records
