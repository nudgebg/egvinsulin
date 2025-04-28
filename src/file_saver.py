import os
from src import postprocessing
import pandas as pd

def save_to_csv(df, file_path, compressed):
    """
    Save a pandas DataFrame to a CSV file. The file can be compressed using gzip.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        file_path (str): The path to the output file.
        compressed (bool): If True, the output file will be compressed using gzip.
    """
    df.to_csv(file_path + (".csv.gz" if compressed else '.csv'), compression='gzip' if compressed else None, index=False)

def save_to_parquet_partitioned(df, base_path, study_name, data_type):
    """
    Save a pandas DataFrame to Parquet files, partitioned by specified columns.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        base_path (str): The base directory for the output files.
        study_name (str): The name of the study.
        data_type (str): The type of data being saved.
    """
    df = df.assign(study_name=study_name, data_type=data_type)
    df.to_parquet(
        base_path,
        index=False,
        partition_cols=['study_name', 'data_type', 'patient_id'],
        engine="pyarrow",
        compression="snappy",
        existing_data_behavior='delete_matching'
    )

def save_dataframe(df, out_path, output_format, compressed, study_name, data_type):
    """
    Save a DataFrame to a specified format (CSV or Parquet) with optional compression.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        out_path (str): The base directory for the output files.
        output_format (str): The output format ('csv' or 'parquet').
        compressed (bool): If True, reduces resolution and compressses the output file (for CSV).
        study_name (str): The name of the study.
        data_type (str): The type of data being saved (e.g., 'cgm', 'bolus', 'basal').
    """
    if output_format == "csv":
        if compressed:
            df = postprocessing.optimize_dataframe_storage(df)
        save_to_csv(df, os.path.join(out_path, f"{study_name}_{data_type}"), compressed)
    elif output_format == "parquet":
        save_to_parquet_partitioned(df, out_path, study_name, data_type)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    