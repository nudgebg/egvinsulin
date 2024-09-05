from scipy.io import savemat
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime

def save_data_as(data: pd.DataFrame, file_format: str, export_filename: str) -> None:
    """
    Save data as a file in the specified format.

    Parameters:
    - data (pd.DataFrame): pandas dataframe with 4 columns: 
        - patient_id (int): the patient identifier
        - datetime (datetime): datetime of event in iso format
    - file_format (str): the format of the saved data. For a .csv file, specify 'CSV'
    - export_filename (str): the name the file should be saved as excluding the file type

    Returns:
    - None

    Raises:
    - ValueError: If the required columns are not present in the data or if the column types are incorrect.
    """
    

    # Check if all required columns are present in the data
    if not all(col in data.columns for col in ['patient_id', 'datetime']):
        missing_columns = [col for col in ['patient_id', 'datetime'] if col not in data.columns]
        raise ValueError(f"Missing required columns in the data: {missing_columns}")
        
    if not is_datetime(data['datetime']):
        raise ValueError("The 'datetime' column should be of type datetime.")

    out_file_path = export_filename + '.' + file_format.lower()
    if file_format == 'CSV':
        data.to_csv(out_file_path, index=False)
    else:
        raise ValueError(f"Unsupported file format: {file_format}. Please specify 'CSV'.")
    
    return out_file_path
