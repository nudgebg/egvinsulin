# File: template.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from studydataset import StudyDataset

class ConcreteStudyDataset(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'ConcreteStudyDataset')
    
    def _load_data(self, subset: bool = False):
        # Implement the logic to load data here
        # For now, we'll just set the data_loaded flag to True
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
    import sys,os
    
    print(f'file = {os.path.dirname(__file__)}')
    study = ConcreteStudyDataset(study_path="dummy_path")
    print("Bolus Event History:")
    print(study.extract_bolus_event_history())
    print("\nBasal Event History:")
    print(study.extract_basal_event_history())
    print("\nCGM History:")
    print(study.extract_cgm_history())