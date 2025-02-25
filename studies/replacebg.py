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
        self.df_basal = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBasal.txt'), sep='|',dtype={'PtID':str})
        self.df_bolus = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBolus.txt'), sep='|',dtype={'PtID':str})
        self.df_patient = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HPtRoster.txt'), sep='|',dtype={'PtID':str})
        self.df_cgm = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceCGM.txt'), sep='|',dtype={'PtID':str})
        self.df_uploads = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceUploads.txt'), sep='|')
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

        # convert durations
        
        #Diasend specific: Diasend durations are in minutes not ms (only exist in boluses)
        # adjust bolus durations (from minutes to ms) and treat boluses without extended part as normal boluses
        self.df_bolus = pd.merge(self.df_bolus, 
                                 self.df_uploads.rename(columns={'PtId':'PtID','RecID':'ParentHDeviceUploadsID'})[['PtID','ParentHDeviceUploadsID','DataSource']],
                                 on=['PtID','ParentHDeviceUploadsID'])
        self.df_bolus.loc[self.df_bolus.DataSource=='Diasend','Duration'] *= 60*1000
        self.df_bolus.loc[(self.df_bolus.DataSource=='Diasend') & self.df_bolus.Extended.isna() & self.df_bolus.Duration.notna(),['Duration']] = np.nan

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

        #for boluses with BolusType == Combination, we treat these as Normal and set Duration to NaN,
        #this removes 4 extended boluses with zero duration considered to be invalid
        combination_boluses = df_bolus.loc[df_bolus['BolusType'] == 'Combination']
        df_bolus.loc[combination_boluses.index, 'Duration'] = np.NaN
        df_bolus.loc[combination_boluses.index, 'Extended'] = np.NaN

        #we have a lot of 0 values, we replace these with NaN so they are dropped in the next step
        df_bolus = df_bolus.replace({'Normal':0, 'Extended':0, 'Duration':timedelta(0)}, np.nan)
                
        #Split rows with normal and extended part in two rows and recombine
        #the dropna makes sure we remove rows that had 0 deliveries in the previous step
        normal = df_bolus.dropna(subset=['Normal']).drop(columns=['Extended']).rename(columns={"Normal": self.COL_NAME_BOLUS})
        #set normal bolus to 0 delivery durations this also override durations that related to the extended parts
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')
        
        extended = df_bolus.dropna(subset=['Extended','Duration'],how='any').drop(columns=['Normal']).rename(columns={"Extended": self.COL_NAME_BOLUS})
        df_bolus = pd.concat([normal, extended], axis=0, ignore_index=True)
        
        #reduce, rename, return
        df_bolus = df_bolus[['PtID', 'datetime', 'Normal', 'Duration']]
        df_bolus = df_bolus.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION})
        return df_bolus

    def _extract_basal_event_history(self):
        df_basal = self.df_basal.copy()

        #drop duplicates with same duration and rate
        _,_,i_drop = pandas_helper.get_duplicated_max_indexes(df_basal, ['PtID', 'datetime'], 'RecID')
        df_basal = df_basal.drop(index=i_drop)
        df_basal = df_basal.drop_duplicates(subset=['PtID', 'datetime','Rate', 'Duration'],keep='first')
        
        #replace NaNs Rates with zero (we know these only come from Suspends and temp basals)
        df_basal.fillna({'Rate':0}, inplace=True)
        
        #reduce, rename, return
        df_basal = df_basal[['PtID', 'datetime', 'Rate']]
        df_basal = df_basal.rename(columns={'Rate': self.COL_NAME_BASAL_RATE,
                                            'PtID': self.COL_NAME_PATIENT_ID,
                                            'datetime': self.COL_NAME_DATETIME}) 
        return df_basal

    def _extract_cgm_history(self):
        df_cgm = self.df_cgm.copy()
        df_cgm = df_cgm.drop_duplicates(subset=['PtID', 'datetime','RecordType','GlucoseValue'])
        df_cgm = df_cgm['GlucoseValue'].replace({39:40, 401:400})
        
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