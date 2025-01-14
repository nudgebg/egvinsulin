import pandas as pd
from studydataset import StudyDataset
from studies.studydataset import StudyDataset
from src.logger import Logger
import os 
import numpy as np


def convert_timestamp(timestamps_col):
    """
    Converts timestamp columns in the input DataFrame from seconds since 1960-01-01
    to the format 'YYYY-MM-DD HH:MM:SS'

    Args:
    timestamps_col : timestamp column(s) to be converted
    
    Returns:
    converted_timestamp: (Datetime) timestamp column(s) converted to 'YYYY-MM-DD HH:MM:SS' format.
    """
    # Check the type of timestamps_col (If it's a Series and not of type pd.Timestamp)
    if isinstance(timestamps_col, pd.Series) and timestamps_col.dtype != pd.Timestamp:
        # Error handling
        try:
            # Convert timestamp to datetime format if not null or NaT
            timestamps_col = timestamps_col.apply(lambda x: datetime(1960, 1, 1) + timedelta(seconds=x) if pd.notnull(x) else pd.NaT)
        except TypeError:
            timestamps_col = pd.to_datetime(timestamps_col)
    
    # Otherwise if timestamps_col is in float format
    elif isinstance(timestamps_col, float):
        timestamps_col = datetime(1960, 1, 1) + timedelta(seconds=timestamps_col)

    return timestamps_col

class T1DEXI(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'T1DEXI')
    
    def _load_data(self, subset: bool = False):
        self.dx = pd.read_sas(os.path.join(self.study_path,'DX.xpt'),encoding='latin-1').replace('', np.nan)
        self.facm = pd.read_sas(os.path.join(self.study_path,'FACM.xpt'),encoding='latin-1').replace('', np.nan)

        self.data_loaded = True

    def _extract_bolus_event_history(self):
        # Return an empty DataFrame with the required columns
        return pd.DataFrame({
            self.COL_NAME_PATIENT_ID: pd.Series(dtype='str'),
            self.COL_NAME_DATETIME: pd.Series(dtype='datetime64[ns]'),
            self.COL_NAME_BOLUS: pd.Series(dtype='float'),
            self.COL_NAME_BOLUS_DELIVERY_DURATION: pd.Series(dtype='timedelta64[as]')
        })

    def _extract_basal_event_history(self):
        # Return an empty DataFrame with the required columns
        return pd.DataFrame({
            self.COL_NAME_PATIENT_ID: pd.Series(dtype='str'),
            self.COL_NAME_DATETIME: pd.Series(dtype='datetime64[ns]'),
            self.COL_NAME_BASAL_RATE: pd.Series(dtype='float')
        })

    def _extract_cgm_history(self):
        # Return an empty DataFrame with the required columns
        return pd.DataFrame({
            self.COL_NAME_PATIENT_ID: pd.Series(dtype='str'),
            self.COL_NAME_DATETIME: pd.Series(dtype='datetime64[ns]'),
            self.COL_NAME_CGM: pd.Series(dtype='float')
        })

# Example usage
if __name__ == "__main__":
    logger = Logger.get_logger(__file__)
    logger.info(os.getcwd())
    study = T1DEXI(study_path=os.path.join(os.getcwd(),'data', 'raw', 'T1DEXI'))
    study.load_data()
    # print("Bolus Event History:")
    # print(study.extract_bolus_event_history())
    # print("\nBasal Event History:")
    # print(study.extract_basal_event_history())
    # print("\nCGM History:")
    # print(study.extract_cgm_history())