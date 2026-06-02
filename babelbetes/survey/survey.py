from datetime import datetime
from pathlib import Path

import pandas as pd

SURVEY_DIR = Path("data/out/survey/surveys")


def _survey_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save(data: list[dict] | pd.DataFrame, suffix: str, survey_id: str | None) -> Path:
    if survey_id is None:
        survey_id = _survey_id()
    SURVEY_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(data) if isinstance(data, list) else data.copy()
    df["survey_id"] = survey_id
    path = SURVEY_DIR / f"{survey_id}_{suffix}.parquet"
    df.to_parquet(path, index=False)
    return path


def _list(suffix: str) -> list[Path]:
    return sorted(SURVEY_DIR.glob(f"*_{suffix}.parquet"))


def _load(suffix: str, path: Path | str | None) -> pd.DataFrame:
    if path is not None:
        path = Path(path)
        if path.is_dir():
            candidates = sorted(path.glob(f"*_{suffix}.parquet"))
            if not candidates:
                raise FileNotFoundError(
                    f"No {suffix} surveys found in {path}. Run 'survey' first."
                )
            path = candidates[-1]
    else:
        candidates = _list(suffix)
        if not candidates:
            raise FileNotFoundError(
                f"No {suffix} surveys found in {SURVEY_DIR}. Run 'survey' first."
            )
        path = candidates[-1]
    return pd.read_parquet(path)


def save_study_stats(records: list[dict], survey_id: str | None = None) -> Path:
    """Save scalar study-level stats as a long-format Parquet survey.

    Args:
        records: List of `{study, data_type, metric, value}` dicts.
        survey_id: Optional timestamp string (YYYYMMDD_HHMMSS). Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(records, "study_stats", survey_id)


def load_study_stats(path: Path | str | None = None) -> pd.DataFrame:
    """Load a study stats survey.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest survey.

    Returns:
        DataFrame with columns `study`, `data_type`, `metric`, `value`, `survey_id`.
    """
    return _load("study_stats", path)


def list_study_stats_surveys() -> list[Path]:
    """Return all study stats survey paths sorted chronologically (oldest first)."""
    return _list("study_stats")


def save_patient_stats(records: list[dict], survey_id: str | None = None) -> Path:
    """Save per-patient stats as a long-format Parquet survey.

    Args:
        records: List of `{study, patient_id, data_type, metric, value}` dicts.
        survey_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(records, "patient_stats", survey_id)


def load_patient_stats(path: Path | str | None = None) -> pd.DataFrame:
    """Load a patient stats survey.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest survey.

    Returns:
        DataFrame with columns `study`, `patient_id`, `data_type`, `metric`, `value`,
        `survey_id`.
    """
    return _load("patient_stats", path)


def list_patient_stats_surveys() -> list[Path]:
    """Return all patient stats survey paths sorted chronologically."""
    return _list("patient_stats")


def save_tdd(df: pd.DataFrame, survey_id: str | None = None) -> Path:
    """Save per-patient daily TDD as a wide-format Parquet survey.

    Args:
        df: Wide DataFrame with columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`.
        survey_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(df, "tdd", survey_id)


def load_tdd(path: Path | str | None = None) -> pd.DataFrame:
    """Load a TDD survey.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest survey.

    Returns:
        DataFrame with columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`,
        `survey_id`.
    """
    return _load("tdd", path)


def list_tdd_surveys() -> list[Path]:
    """Return all TDD survey paths sorted chronologically."""
    return _list("tdd")


def save_cdf_quantiles(df: pd.DataFrame, survey_id: str | None = None) -> Path:
    """Save pre-computed CDF quantiles as a Parquet survey.

    Args:
        df: DataFrame with columns `study`, `data_type`, `quantile_level`, `value`.
        survey_id: Optional timestamp string. Generated if not provided.

    Returns:
        Path to the saved Parquet file.
    """
    return _save(df, "cdf_quantiles", survey_id)


def load_cdf_quantiles(path: Path | str | None = None) -> pd.DataFrame:
    """Load a CDF quantiles survey.

    Args:
        path: Path to a specific Parquet file. Defaults to the latest survey.

    Returns:
        DataFrame with columns `study`, `data_type`, `quantile_level`, `value`, `survey_id`.
    """
    return _load("cdf_quantiles", path)


def list_cdf_quantile_surveys() -> list[Path]:
    """Return all CDF quantile survey paths sorted chronologically."""
    return _list("cdf_quantiles")
