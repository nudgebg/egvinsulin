# File: data_store.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import os
import shutil
import pandas as pd


class ParquetStore:
    """Read/write interface for the partitioned Parquet output store.

    Data is stored as Hive-partitioned Parquet files under `base_path`,
    partitioned by study_name / data_type / patient_id.

    Args:
        base_path (str): Root directory of the store (e.g. "data/out").
    """

    def __init__(self, base_path):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save(self, df: pd.DataFrame, study_name: str, data_type: str):
        """Write a DataFrame to the store for a given study and data type.

        Args:
            df (pd.DataFrame): Data to save.
            study_name (str): Study identifier (e.g. "Flair").
            data_type (str): One of 'cgm', 'bolus', 'basal', 'age'.
        """
        df = df.assign(study_name=study_name, data_type=data_type)
        df.to_parquet(
            self.base_path,
            index=False,
            partition_cols=['study_name', 'data_type', 'patient_id'],
            engine="pyarrow",
            compression="snappy",
            existing_data_behavior='delete_matching',
        )

    def load(self, study=None, data_type=None, patient=None):
        """Load data from the store, optionally filtered by study, data type, or patient.

        Args:
            study (str | list[str]): Filter by study name(s) (e.g. "Flair" or ["Flair", "DCLP3"]).
            data_type (str | list[str]): One or more of 'cgm', 'bolus', 'basal', 'age'.
                A single string returns a DataFrame; a list returns a dict[str, DataFrame].
            patient (str | list[str]): Filter by patient ID(s).

        Returns:
            pd.DataFrame: When data_type is a single string.
            dict[str, pd.DataFrame]: When data_type is a list or None (keyed by data type).
        """
        ALL_DATA_TYPES = ['cgm', 'bolus', 'basal', 'age']

        base_filters = []
        if study is not None:
            studies = [study] if isinstance(study, str) else study
            base_filters.append(("study_name", "in", studies))
        if patient is not None:
            patients = [patient] if isinstance(patient, str) else patient
            base_filters.append(("patient_id", "in", patients))

        if data_type is None or isinstance(data_type, list):
            data_types = ALL_DATA_TYPES if data_type is None else data_type
            return {
                dt: pd.read_parquet(self.base_path, filters=base_filters + [("data_type", "==", dt)])
                for dt in data_types
            }

        filters = base_filters + [("data_type", "==", data_type)]
        return pd.read_parquet(self.base_path, filters=filters or None)

    def cleanup(self, study_name: str, data_types: list = None):
        """Remove existing output for a study to ensure a clean write.

        Args:
            study_name (str): Study whose output should be removed.
            data_types (list): Specific data types to remove. If None, removes
                the entire study directory.

        Returns:
            list: Paths that were actually removed.
        """
        if data_types is None:
            directories = [os.path.join(self.base_path, f"study_name={study_name}")]
        else:
            directories = [
                os.path.join(self.base_path, f"study_name={study_name}", f"data_type={dt}")
                for dt in data_types
            ]

        removed = []
        for d in directories:
            if os.path.isdir(d):
                shutil.rmtree(d)
                removed.append(d)
        return removed
