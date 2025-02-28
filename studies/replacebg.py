import pandas as pd
from studies.studydataset import StudyDataset
from datetime import datetime, timedelta
from functools import reduce
import numpy as np
import os
from src import pandas_helper, logger

class ReplaceBG(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'ReplaceBG')
    
    def _load_data(self, subset: bool = False):
        study_path = self.study_path

        #imaginary start date we chose since data is relative to enrollment
        enrollment_start = datetime(2015, 1, 1)
        #load data
        df_basal = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBasal.txt'), sep='|',dtype={'PtID':str},
                       skiprows=lambda x: (x % 10 != 0) & subset)
        df_bolus = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceBolus.txt'), sep='|',dtype={'PtID':str},
                       skiprows=lambda x: (x % 10 != 0) & subset)
        df_patient = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HPtRoster.txt'), sep='|',dtype={'PtID':str},
                     skiprows=lambda x: (x % 10 != 0) & subset)
        df_cgm = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceCGM.txt'), sep='|',dtype={'PtID':str},
                     skiprows=lambda x: (x % 10 != 0) & subset)
        df_uploads = pd.read_csv(os.path.join(study_path, 'Data Tables', 'HDeviceUploads.txt'), sep='|',dtype={'PtId':str}).rename(columns={'PtId':'PtID'})
        
        #convert datetimes
        df_basal['datetime'] = enrollment_start + pd.to_timedelta(df_basal['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df_basal['DeviceTm'])
        df_bolus['datetime'] = enrollment_start + pd.to_timedelta(df_bolus['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df_bolus['DeviceTm'])
        df_cgm['datetime'] = enrollment_start + pd.to_timedelta(df_cgm['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df_cgm['DeviceTm'])

        df_basal['hour_of_day'] = df_basal.datetime.dt.hour
        df_bolus['hour_of_day'] = df_bolus.datetime.dt.hour
        df_cgm['hour_of_day'] = df_cgm.datetime.dt.hour

        df_bolus['day'] = df_bolus.datetime.dt.date
        df_basal['day'] = df_basal.datetime.dt.date
        df_cgm['day'] = df_cgm.datetime.dt.date

        df_basal.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)
        df_bolus.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)
        df_cgm.drop(columns=['DeviceDtTmDaysFromEnroll', 'DeviceTm'], inplace=True)

        # convert durations
        
        #Diasend specific: Diasend durations are in minutes not ms (only exist in boluses)
        # adjust bolus durations (from minutes to ms) and treat boluses without extended part as normal boluses
        df_bolus = pd.merge(df_bolus, 
                    df_uploads.rename(columns={'RecID':'ParentHDeviceUploadsID'})[['PtID','ParentHDeviceUploadsID','DataSource']],
                    on=['PtID','ParentHDeviceUploadsID'])
        df_bolus.loc[df_bolus.DataSource=='Diasend','Duration'] *= 60*1000
        df_bolus.loc[(df_bolus.DataSource=='Diasend') & df_bolus.Extended.isna() & df_bolus.Duration.notna(),['Duration']] = np.nan

        df_basal['Duration'] = pd.to_timedelta(df_basal['Duration'], unit='ms')
        df_basal['ExpectedDuration'] = pd.to_timedelta(df_basal['ExpectedDuration'], unit='ms')
        df_basal['SuprDuration'] = pd.to_timedelta(df_basal['SuprDuration'], unit='ms')
        df_bolus['Duration'] = pd.to_timedelta(df_bolus['Duration'], unit='ms')
        df_bolus['ExpectedDuration'] = pd.to_timedelta(df_bolus['ExpectedDuration'], unit='ms')
        
        #drop patients that are not in all datasets 
        patient_ids_to_keep = reduce(np.intersect1d, [df_basal['PtID'].unique(), 
                                  df_bolus['PtID'].unique(), 
                                  df_cgm['PtID'].unique()])
        df_basal = df_basal[df_basal['PtID'].isin(patient_ids_to_keep)]
        df_bolus = df_bolus[df_bolus['PtID'].isin(patient_ids_to_keep)]
        df_cgm = df_cgm[df_cgm['PtID'].isin(patient_ids_to_keep)]

        #sort data by patient and datetime
        df_basal = df_basal.sort_values(by=['PtID', 'datetime'])
        df_bolus = df_bolus.sort_values(by=['PtID', 'datetime'])
        df_cgm = df_cgm.sort_values(by=['PtID', 'datetime'])

        # Assign to self
        self.df_basal = df_basal
        self.df_bolus = df_bolus
        self.df_patient = df_patient
        self.df_cgm = df_cgm
        self.df_uploads = df_uploads

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
        #for example there are extended boluses with zero units
        #these would just create larger output files and we want to obmit them
        df_bolus = df_bolus.replace({'Normal':0, 'Extended':0}, np.nan)
                
        #Convert extended part to new rows
        #the dropna makes sure we remove rows that had 0 deliveries in the previous step
        normal = df_bolus.dropna(subset=['Normal']).drop(columns=['Extended'])
        #normal boluses are assigned 0 duration (this also overrides durations that were coming from the extended part)
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')
        #the extended part is assigned as normal bolus but keeps its duration
        extended = df_bolus.dropna(subset=['Extended', 'Duration'],how='any').drop(columns=['Normal']).rename(columns={"Extended": 'Normal'})
        df_bolus = pd.concat([normal, extended], axis=0, ignore_index=True)
        
        #reduce, rename, return
        df_bolus = df_bolus[['PtID', 'datetime', 'Normal', 'Duration']]
        df_bolus = df_bolus.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION,
                                        'Normal': self.COL_NAME_BOLUS})
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

        #drop Calibrations
        df_cgm = df_cgm.loc[df_cgm.RecordType == 'CGM']

        #handle out of range values
        df_cgm.replace({'GlucoseValue': {39:40, 401:400}},inplace=True)
        
        #reduce, rename, return
        df_cgm = df_cgm.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'GlucoseValue': self.COL_NAME_CGM})
        return df_cgm[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_CGM]]

# Example usage
if __name__ == "__main__":
    logger = logger.Logger.get_logger(__file__)
    logger.info(os.getcwd())
    
    folder = 'REPLACE-BG Dataset-79f6bdc8-3c51-4736-a39f-c4c0f71d45e5'
    study = ReplaceBG(study_path=os.path.join(os.getcwd(),'data', 'raw', folder))
    out_path = os.path.join(os.getcwd(),'data', 'out', folder)
    study.load_data()
    study.extract_basal_event_history()
    study.extract_bolus_event_history()
    study.extract_cgm_history()
    study.save_basal_event_history_to_file(out_path)