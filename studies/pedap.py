from studies.studydataset import StudyDataset
import os
import pandas as pd
from src.date_helper import parse_flair_dates

class PEDAP(StudyDataset):
    def _load_data(self, subset):
        data_table_path = os.path.join(self.study_path, 'Data Files')

        df_bolus = pd.read_csv(os.path.join(data_table_path, 'PEDAPTandemBOLUSDELIVERED.txt'), sep="|", 
                                    usecols=['PtID', 'DeviceDtTm', 'BolusAmount', 'Duration'],
                                    skiprows=lambda x: (x % 10 != 0) & subset)
        
        df_basal = pd.read_csv(os.path.join(data_table_path, 'PEDAPTandemBASALRATECHG.txt'), sep="|", 
                               usecols=['PtID', 'DeviceDtTm', 'BasalRate'],
                               skiprows=lambda x: (x % 10 != 0) & subset)
        
        df_cgm = pd.read_csv(os.path.join(data_table_path, 'PEDAPTandemCGMDataGXB.txt'), sep="|", 
                                  usecols=['PtID', 'DeviceDtTm', 'CGMValue'],
                                  skiprows=lambda x: (x % 10 != 0) & subset)
        
        # remove duplicated rows
        df_basal = df_basal.drop_duplicates(subset=['PtID','DeviceDtTm','BasalRate'])
        df_bolus = df_bolus.drop_duplicates(subset=['PtID','DeviceDtTm','BolusAmount'])
        df_cgm = df_cgm.drop_duplicates(subset=['PtID','DeviceDtTm'])
        
        #remove missing DeviceDtTm for the bolus dataset (there are 4 entries)
        df_bolus = df_bolus.dropna(subset=['DeviceDtTm'])

        # get patient ids with data in all 3 datasets
        intersecting_patient_ids = set(df_cgm.PtID.unique()).intersection(set(df_bolus.PtID.unique())).intersection(set(df_basal.PtID.unique()))
        
        df_bolus = df_bolus[df_bolus.PtID.isin(intersecting_patient_ids)]
        df_basal = df_basal[df_basal.PtID.isin(intersecting_patient_ids)]
        df_cgm = df_cgm[df_cgm.PtID.isin(intersecting_patient_ids)]
        df_basal.drop
        df_bolus['DeviceDtTm'] = parse_flair_dates(df_bolus['DeviceDtTm'])
        df_basal['DeviceDtTm'] = parse_flair_dates(df_basal['DeviceDtTm'])
        df_cgm['DeviceDtTm'] = parse_flair_dates(df_cgm['DeviceDtTm'])

        self.df_bolus = df_bolus
        self.df_basal = df_basal
        self.df_cgm = df_cgm
    
    def __init__(self, study_path):
        super().__init__(study_path, 'PEDAP')

    def _extract_basal_event_history(self):
        temp = self.df_basal[['PtID', 'BasalRate', 'DeviceDtTm']].astype({'PtID':str}).copy()
        #to pass the data set validaiton
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)
        return temp.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime', 'BasalRate': 'basal_rate'})

    def _extract_bolus_event_history(self):
        # keep only tandem patients (having data in all 3 datasets)
        temp = self.df_bolus[['PtID', 'DeviceDtTm', 'BolusAmount', 'Duration']].astype({'PtID':str}).copy()

        #force datetime, needed for vectorized operations and to pass the data set validaiton
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)

        # convert to adjust start delivery times (only affects extended boluses)
        temp['Duration'] = pd.to_timedelta(self.df_bolus.Duration, unit='m')
        temp['DeviceDtTm'] = temp.DeviceDtTm - temp.Duration
        
        temp = temp.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime',
                           'BolusAmount': 'bolus', 'Duration': 'delivery_duration'})
        return temp.copy()

    def _extract_cgm_history(self):
        temp = self.df_cgm[['PtID', 'DeviceDtTm', 'CGMValue']].astype({'PtID':str}).copy()
        #to pass the data set validaiton
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)
        return temp.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime', 'CGMValue': 'cgm'})
