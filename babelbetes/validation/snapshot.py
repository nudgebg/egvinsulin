from datetime import datetime
from pathlib import Path

import pandas as pd

SNAPSHOT_DIR = Path("data/out/validation/snapshots")


def _snapshot_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_stats(records: list[dict], snapshot_id: str | None = None) -> Path:
    """Save scalar study-level stats as a long-format Parquet snapshot.

    Args:
        records: List of {study, data_type, metric, value} dicts from compute.compute_basic_stats()
        snapshot_id: Optional timestamp string (YYYYMMDD_HHMMSS). Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    if snapshot_id is None:
        snapshot_id = _snapshot_id()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df["snapshot_id"] = snapshot_id
    path = SNAPSHOT_DIR / f"{snapshot_id}_stats.parquet"
    df.to_parquet(path, index=False)
    return path


def load_stats(path: Path | str) -> pd.DataFrame:
    """Load a stats snapshot from a Parquet file."""
    return pd.read_parquet(path)


def list_stats_snapshots() -> list[Path]:
    """Return all stats snapshot paths sorted chronologically (oldest first)."""
    return sorted(SNAPSHOT_DIR.glob("*_stats.parquet"))


def save_patient_stats(records: list[dict], snapshot_id: str | None = None) -> Path:
    """Save per-patient stats as a long-format Parquet snapshot.

    Args:
        records: List of {study, patient_id, data_type, metric, value} dicts
                 from compute.compute_patient_stats().
        snapshot_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    if snapshot_id is None:
        snapshot_id = _snapshot_id()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df["snapshot_id"] = snapshot_id
    path = SNAPSHOT_DIR / f"{snapshot_id}_patient_stats.parquet"
    df.to_parquet(path, index=False)
    return path


def load_patient_stats(path: Path | str) -> pd.DataFrame:
    """Load a patient stats snapshot from a Parquet file."""
    return pd.read_parquet(path)


def list_patient_stats_snapshots() -> list[Path]:
    """Return all patient stats snapshot paths sorted chronologically."""
    return sorted(SNAPSHOT_DIR.glob("*_patient_stats.parquet"))


def save_tdd(df: pd.DataFrame, snapshot_id: str | None = None) -> Path:
    """Save per-patient daily TDD as a wide-format Parquet snapshot.

    Args:
        df: Wide DataFrame with columns (study, patient_id, date, basal, bolus, total)
            from compute.compute_tdd_per_patient().
        snapshot_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    if snapshot_id is None:
        snapshot_id = _snapshot_id()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    df["snapshot_id"] = snapshot_id
    path = SNAPSHOT_DIR / f"{snapshot_id}_tdd.parquet"
    df.to_parquet(path, index=False)
    return path


def load_tdd(path: Path | str) -> pd.DataFrame:
    """Load a TDD snapshot from a Parquet file."""
    return pd.read_parquet(path)


def list_tdd_snapshots() -> list[Path]:
    """Return all TDD snapshot paths sorted chronologically."""
    return sorted(SNAPSHOT_DIR.glob("*_tdd.parquet"))
