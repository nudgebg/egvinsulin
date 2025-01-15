import pandas as pd
from studydataset import StudyDataset
from studies.studydataset import StudyDataset
from src.logger import Logger
import os 
import numpy as np
from datetime import datetime, timedelta
import isodate

def load_facm(path):
        facm = pd.read_sas(path,encoding='latin-1').replace('', np.nan).drop(columns=['STUDYID','DOMAIN','FASEQ'])
        #datetimes
        facm['FADTC'] = facm['FADTC'].apply(lambda x: datetime(1960, 1, 1) + timedelta(seconds=x) if pd.notnull(x) else pd.NaT)
        #durations
        facm['FADUR'] = facm.FADUR.dropna().apply(isodate.parse_duration, as_timedelta_if_possible=True)
        
        return facm

def load_dx(path):
        dx = pd.read_sas(path,encoding='latin-1').replace('', np.nan)
        dx = dx.drop(columns=['DXSCAT','DXPRESP','STUDYID','DOMAIN','SPDEVID','DXSEQ','DXCAT','DXSCAT','DXSTRTPT','DXDTC','DXENRTPT','DXEVINTX','VISIT'])
        return dx

class T1DEXI(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'T1DEXI')
    
    

    
    
    def _load_data(self, subset: bool = False):
        self.facm = load_facm(os.path.join(self.study_path,'FACM.xpt'))
        self.dx = load_dx(os.path.join(self.study_path,'DX.xpt'))
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