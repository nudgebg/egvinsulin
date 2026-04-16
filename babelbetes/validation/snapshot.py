from datetime import datetime
from pathlib import Path

import pandas as pd

SNAPSHOT_DIR = Path("data/out/validation/snapshots")


def _snapshot_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save(data: list[dict] | pd.DataFrame, suffix: str, snapshot_id: str | None) -> Path:
    if snapshot_id is None:
        snapshot_id = _snapshot_id()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data) if isinstance(data, list) else data.copy()
    df["snapshot_id"] = snapshot_id
    path = SNAPSHOT_DIR / f"{snapshot_id}_{suffix}.parquet"
    df.to_parquet(path, index=False)
    return path


def _list(suffix: str) -> list[Path]:
    return sorted(SNAPSHOT_DIR.glob(f"*_{suffix}.parquet"))


def _load(suffix: str, path: Path | str | None) -> pd.DataFrame:
    if path is not None:
        path = Path(path)
        if path.is_dir():
            # Caller passed a directory — find the latest matching file within it
            candidates = sorted(path.glob(f"*_{suffix}.parquet"))
            if not candidates:
                raise FileNotFoundError(
                    f"No {suffix} snapshots found in {path}. Run 'snapshot' first."
                )
            path = candidates[-1]
    else:
        candidates = _list(suffix)
        if not candidates:
            raise FileNotFoundError(
                f"No {suffix} snapshots found in {SNAPSHOT_DIR}. Run 'snapshot' first."
            )
        path = candidates[-1]
    return pd.read_parquet(path)


def save_study_stats(records: list[dict], snapshot_id: str | None = None) -> Path:
    """Save scalar study-level stats as a long-format Parquet snapshot.

    Args:
        records: List of `{study, data_type, metric, value}` dicts.
        snapshot_id: Optional timestamp string (YYYYMMDD_HHMMSS). Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(records, "study_stats", snapshot_id)


def load_study_stats(path: Path | str | None = None) -> pd.DataFrame:
    """Load a study stats snapshot.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest snapshot.

    Returns:
        DataFrame with columns `study`, `data_type`, `metric`, `value`, `snapshot_id`.
    """
    return _load("study_stats", path)


def list_study_stats_snapshots() -> list[Path]:
    """Return all study stats snapshot paths sorted chronologically (oldest first)."""
    return _list("study_stats")


def save_patient_stats(records: list[dict], snapshot_id: str | None = None) -> Path:
    """Save per-patient stats as a long-format Parquet snapshot.

    Args:
        records: List of `{study, patient_id, data_type, metric, value}` dicts.
        snapshot_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(records, "patient_stats", snapshot_id)


def load_patient_stats(path: Path | str | None = None) -> pd.DataFrame:
    """Load a patient stats snapshot.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest snapshot.

    Returns:
        DataFrame with columns `study`, `patient_id`, `data_type`, `metric`, `value`,
        `snapshot_id`.
    """
    return _load("patient_stats", path)


def list_patient_stats_snapshots() -> list[Path]:
    """Return all patient stats snapshot paths sorted chronologically."""
    return _list("patient_stats")


def save_tdd(df: pd.DataFrame, snapshot_id: str | None = None) -> Path:
    """Save per-patient daily TDD as a wide-format Parquet snapshot.

    Args:
        df: Wide DataFrame with columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`.
        snapshot_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(df, "tdd", snapshot_id)


def load_tdd(path: Path | str | None = None) -> pd.DataFrame:
    """Load a TDD snapshot.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest snapshot.

    Returns:
        DataFrame with columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`,
        `snapshot_id`.
    """
    return _load("tdd", path)


def list_tdd_snapshots() -> list[Path]:
    """Return all TDD snapshot paths sorted chronologically."""
    return _list("tdd")


def save_cdf_quantiles(df: pd.DataFrame, snapshot_id: str | None = None) -> Path:
    """Save pre-computed CDF quantiles as a Parquet snapshot.

    Args:
        df: DataFrame with columns `study`, `data_type`, `quantile_level`, `value`.
        snapshot_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(df, "cdf_quantiles", snapshot_id)


def load_cdf_quantiles(path: Path | str | None = None) -> pd.DataFrame:
    """Load a CDF quantiles snapshot.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest snapshot.

    Returns:
        DataFrame with columns `study`, `data_type`, `quantile_level`, `value`, `snapshot_id`.
    """
    return _load("cdf_quantiles", path)


def list_cdf_quantile_snapshots() -> list[Path]:
    """Return all CDF quantile snapshot paths sorted chronologically."""
    return _list("cdf_quantiles")
