import os
import pandas as pd
from src.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)

# Define expected columns for each type of CSV
EXPECTED_COLUMNS = {
    'bolus_history.csv': ['patient_id', 'datetime', 'bolus', 'delivery_duration'],
    'bolus_history-transformed.csv': ['patient_id', 'datetime', 'bolus'],
    'basal_history.csv': ['patient_id', 'datetime', 'basal_rate'],
    'basal_history-transformed.csv': ['patient_id', 'datetime', 'basal_delivery'],
    'cgm_history.csv': ['patient_id', 'datetime', 'cgm'],
    'cgm_history-transformed.csv': ['patient_id', 'datetime', 'cgm']
}

def validate_csv(file_path, expected_columns):
    """Validate a CSV file by checking if it exists, if the column names are correct, and if the DataFrame is not empty."""
    if not os.path.exists(file_path):
        logger.error(f"[!] ERROR: File not found: {os.path.basename(file_path)}")
        return False

    df = pd.read_csv(file_path)
    if df.empty:
        logger.error(f"[!] ERROR: DataFrame is empty: {os.path.basename(file_path)}")
        return False

    if set(df.columns) != set(expected_columns):
        logger.error(f"[!] ERROR: incorrect columns in {os.path.basename(file_path)}. Expected: {expected_columns}, Found: {df.columns}")
        return False

    logger.info(f"[x] PASSED {os.path.basename(file_path)}")
    return True

def validate_output(output_path):
    """Validate all output CSV files in the given output path."""
    for file_name, expected_columns in EXPECTED_COLUMNS.items():
        file_path = os.path.join(output_path, file_name)
        validate_csv(file_path, expected_columns)

def main():
    current_dir = os.getcwd()
    out_path = os.path.join(current_dir, 'data/out')

    potential_folders = ['DCLP3 Public Dataset - Release 3 - 2022-08-04',
                          'FLAIRPublicDataSet',
                          'DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53', 
                          'PEDAP Public Dataset - Release 3 - 2024-09-25', 
                          'IOBP2 RCT Public Dataset']
    
    # Get all study folders in the output path
    actual_folders = [f for f in os.listdir(out_path) if os.path.isdir(os.path.join(out_path, f))]
    available_folders = [f for f in actual_folders if f in potential_folders]
    print(available_folders)

    # Validate each study folder
    for folder in available_folders:
       folder_full_path = os.path.join(out_path, folder)
       logger.debug(f"Validating study folder: {folder_full_path}")
       validate_output(folder_full_path)

if __name__ == "__main__":
    main()