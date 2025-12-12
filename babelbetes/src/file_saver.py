import os
from babelbetes.src import postprocessing
import pandas as pd

def get_output_paths(out_path, study_name, data_types=None):
    """
    Determine the output paths that will be created for a study in Parquet format.
    This function can be used both for saving files and for cleanup operations.
    
    Args:
        out_path (str): Base output directory
        study_name (str): Name of the study
        data_types (list): List of data types to include ['cgm', 'bolus', 'basal']. If None, all types are included.
        
    Returns:
        list: List of directory paths that will be created/removed
    """
    directories = []
    
    # For parquet format, data is partitioned by study_name, data_type, patient_id
    if data_types is None:
        # Remove entire study directory when no specific data types specified
        directories = [os.path.join(out_path, f"study_name={study_name}")]
    else:
        # Remove specific data type partitions
        for data_type in data_types:
            directories.append(os.path.join(out_path, f"study_name={study_name}", f"data_type={data_type}"))
    
    return directories

def cleanup_study_output(out_path, study_name, data_types=None):
    """
    Remove existing output directories for a study to ensure clean output.
    
    Args:
        out_path (str): Base output directory
        study_name (str): Name of the study
        data_types (list): List of data types to clean ['cgm', 'bolus', 'basal']. If None, all types are cleaned.
        
    Returns:
        list: List of paths that were actually removed
    """
    import shutil
    
    directories = get_output_paths(out_path, study_name, data_types)
    removed_paths = []
    
    # Remove directories
    for directory in directories:
        if os.path.exists(directory) and os.path.isdir(directory):
            shutil.rmtree(directory)
            removed_paths.append(directory)
    
    return removed_paths



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
    Save a DataFrame to Parquet format with partitioning.

    Args:
        df (pd.DataFrame): The DataFrame to save.
        out_path (str): The base directory for the output files.
        output_format (str): The output format (only 'parquet' is supported).
        compressed (bool): Not used for parquet (compression is handled by pyarrow).
        study_name (str): The name of the study.
        data_type (str): The type of data being saved (e.g., 'cgm', 'bolus', 'basal').
    """
    if output_format == "parquet":
        save_to_parquet_partitioned(df, out_path, study_name, data_type)
    else:
        raise ValueError(f"Unsupported output format: {output_format}. Only 'parquet' is supported.")
    