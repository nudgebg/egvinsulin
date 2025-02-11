import pandas as pd
from .studydataset import StudyDataset
from datetime import datetime, timedelta
from functools import reduce
import numpy as np
from src import pandas_helper
class ReplaceBG(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'ReplaceBG')
    
    def _load_data(self, subset: bool = False):
        # Implement the logic to load data here
        # For now, we'll just set the data_loaded flag to True
        #define path variables
        study_name = 'REPLACE-BG Dataset-79f6bdc8-3c51-4736-a39f-c4c0f71d45e5'
        raw_path = os.path.join(os.getcwd(), '..', '..', 'data', 'raw')
        out_path = os.path.join(os.getcwd(), '..', '..', 'data', 'out')
        study_path = os.path.join(raw_path, study_name)
        
        #imaginary start date we chose since data is relative to enrollment
        enrollment_start = datetime(2025, 1, 1)

        #load data
        self.df_basal = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBasal.txt'), sep='|')
        self.df_bolus = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBolus.txt'), sep='|')
        self.df_patient = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HPtRoster.txt'), sep='|')
        self.df_cgm = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceCGM.txt'), sep='|')

        #convert datetimes
        self.df_basal['datetime'] = enrollment_start + pd.to_timedelta(self.df_basal['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(self.df_basal['DeviceTm'])
        self.df_bolus['datetime'] = enrollment_start + pd.to_timedelta(self.df_bolus['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(self.df_bolus['DeviceTm'])
        self.df_cgm['datetime'] = enrollment_start + pd.to_timedelta(self.df_cgm['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(self.df_cgm['DeviceTm'])

        self.df_basal['hour_of_day'] = self.df_basal.datetime.dt.hour
        self.df_bolus['hour_of_day'] = self.df_bolus.datetime.dt.hour
        self.df_cgm['hour_of_day'] = self.df_cgm.datetime.dt.hour

        self.df_bolus['day'] = self.df_bolus.datetime.dt.date
        self.df_basal['day'] = self.df_basal.datetime.dt.date
        self.df_cgm['day'] = self.df_cgm.datetime.dt.date

        self.df_basal.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)
        self.df_bolus.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)
        self.df_cgm.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)

        #convert durations
        self.df_basal['Duration'] = pd.to_timedelta(self.df_basal['Duration'], unit='ms')
        self.df_basal['ExpectedDuration'] = pd.to_timedelta(self.df_basal['ExpectedDuration'], unit='ms')
        self.df_basal['SuprDuration'] = pd.to_timedelta(self.df_basal['SuprDuration'], unit='ms')
        self.df_bolus['Duration'] = pd.to_timedelta(self.df_bolus['Duration'], unit='ms')
        self.df_bolus['ExpectedDuration'] = pd.to_timedelta(self.df_bolus['ExpectedDuration'], unit='ms')
        
        #drop patients that are not in all datasets 
        patient_ids_to_keep = reduce(np.intersect1d, [self.df_basal['PtID'].unique(), 
                                                      self.df_bolus['PtID'].unique(), 
                                                      self.df_cgm['PtID'].unique()])
        self.df_basal = self.df_basal[self.df_basal['PtID'].isin(patient_ids_to_keep)]
        self.df_bolus = self.df_bolus[self.df_bolus['PtID'].isin(patient_ids_to_keep)]
        self.df_cgm = self.df_cgm[self.df_cgm['PtID'].isin(patient_ids_to_keep)]

        #sort data by patient and datetime
        self.df_basal = self.df_basal.sort_values(by=['PtID', 'datetime'])
        self.df_bolus = self.df_bolus.sort_values(by=['PtID', 'datetime'])
        self.df_cgm = self.df_cgm.sort_values(by=['PtID', 'datetime'])

        self.data_loaded = True

    def _extract_bolus_event_history(self):
        #drop actual duplicates
        df_bolus = self.df_bolus.copy()
        df_bolus = df_bolus.drop_duplicates(subset=['PtID', 'datetime','BolusType','Normal','Extended','Duration'])

        #drop temporal duplciates keeping the maximum RecID row 
        _, _, i_drop = pandas_helper.get_duplicated_max_indexes(df_bolus, ['PtID', 'datetime'], 'RecID')
        df_bolus = df_bolus.drop(index=i_drop)

        #for boluses with BolusType == Combination, we treat these as Normal and set Duration to NaN
        combination_boluses = df_bolus.loc[df_bolus['BolusType'] == 'Combination']
        df_bolus.loc[combination_boluses.index, 'Duration'] = np.NaN
        df_bolus.loc[combination_boluses.index, 'Extended'] = np.NaN

        #we have a lot of 0 values, let's replace these with NaN so they are dropped later
        df_bolus = df_bolus.replace({'Normal':0, 'Extended':0, 'Duration':timedelta(0)}, np.nan)
                
        #split extended and normal boluses, the dropna should make sure we remove rows that had 0 deliveries
        normal = df_bolus.dropna(subset=['Normal']).drop(columns=['Extended'])
        #for normal boluses we set the delivery duration = 0 (this also overrides durations from extended parts)
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')
        #extended boluses have a delivery duration
        extended = df_bolus.dropna(subset=['Extended','Duration'],how='any').drop(columns=['Normal']).rename(columns={"Extended": "Normal"})

        df_bolus = pd.concat([normal, extended], axis=0, ignore_index=True)
        
        #reduce, rename, return
        df_bolus = df_bolus[['PtID', 'datetime', 'Normal', 'Duration']]
        df_bolus = df_bolus.rename(columns={'Normal': self.COL_NAME_BOLUS,
                                        'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION})
        return df_bolus

    def _extract_basal_event_history(self):
        df_basal = self.df_basal.copy()

        #drop actual duplicates
        df_basal = df_basal.drop_duplicates(subset=['PtID', 'datetime','Rate', 'Duration'],keep='first')
        
        #reduce, rename, return
        df_basal = df_basal[['PtID', 'datetime', 'Rate']]
        df_basal = df_basal.rename(columns={'Rate': self.COL_NAME_BASAL_RATE,
                                            'PtID': self.COL_NAME_PATIENT_ID,
                                            'datetime': self.COL_NAME_DATETIME}) 
        return df_basal

    def _extract_cgm_history(self):

        df_cgm = self.df_cgm.copy()
        df_cgm = df_cgm.drop_duplicates(subset=['PtID', 'datetime','RecordType','GlucoseValue'])
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
    study = ReplaceBG(study_path="dummy_path")
    print("Bolus Event History:")
    print(study.extract_bolus_event_history())
    print("\nBasal Event History:")
    print(study.extract_basal_event_history())
    print("\nCGM History:")
    print(study.extract_cgm_history())