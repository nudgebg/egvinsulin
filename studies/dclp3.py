from src.find_periods import find_periods, Period
from src import pandas_helper
from studies.studydataset import StudyDataset
import os
import pandas as pd
from functools import reduce
from datetime import timedelta
import numpy as np

class DCLP3(StudyDataset):
    def load_data(self):
        data_table_path = os.path.join(self.study_path, 'Data Files')
        df_bolus = pd.read_csv(os.path.join(data_table_path, 'Pump_BolusDelivered.txt'), sep='|', low_memory=False,
                               usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'])

        df_basal = pd.read_csv(os.path.join(data_table_path, 'Pump_BasalRateChange.txt'), sep='|', low_memory=False,
                               usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'])

        df_cgm = pd.read_csv(os.path.join(data_table_path, 'Pump_CGMGlucoseValue.txt'), sep='|', low_memory=False, 
                               usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'])

        
        # Handle duplicates
        # for cgm we just keep the first value
        df_cgm.drop_duplicates(['PtID', 'DataDtTm'], keep='first', inplace=True)
        # for basal we decided top use the maximum value
        _, _, drop_indexes = pandas_helper.get_duplicated_max_indexes(df_basal, ['PtID', 'DataDtTm'], 'CommandedBasalRate')
        df_basal.drop(drop_indexes, inplace=True)

        #remove patients with incomplete data
        intersecting_ids = reduce(np.intersect1d, (df_basal.PtID.unique(), df_bolus.PtID.unique(), df_cgm.PtID.unique()))
        df_basal = df_basal[df_basal.PtID.isin(intersecting_ids)]
        df_bolus = df_bolus[df_bolus.PtID.isin(intersecting_ids)]
        df_cgm = df_cgm[df_cgm.PtID.isin(intersecting_ids)]

        #setting datetimes (using the adjusted datetime if available)
        df_bolus['DataDtTm'] = pd.to_datetime(df_bolus['DataDtTm'])
        df_basal['DataDtTm'] = pd.to_datetime(df_basal['DataDtTm'])
        df_cgm['DataDtTm'] = pd.to_datetime(df_cgm['DataDtTm'])

        df_bolus['DataDtTm_adjusted'] = df_bolus.DataDtTm_adjusted.fillna(pd.NaT)
        df_basal['DataDtTm_adjusted'] = df_basal.DataDtTm_adjusted.fillna(pd.NaT)
        df_cgm['DataDtTm_adjusted'] = df_cgm.DataDtTm_adjusted.fillna(pd.NaT)

        df_cgm['DataDtTm_adjusted'] = pd.to_datetime(df_cgm['DataDtTm_adjusted'])
        df_basal['DataDtTm_adjusted'] = pd.to_datetime(df_basal['DataDtTm_adjusted'])
        df_bolus['DataDtTm_adjusted'] = pd.to_datetime(df_bolus['DataDtTm_adjusted'])

        self.df_bolus = df_bolus
        self.df_basal = df_basal
        self.df_cgm = df_cgm
    
    def __init__(self, study_path):
        super().__init__(study_path, 'PEDAP')

    def _extract_basal_event_history(self):
        temp = self.df_basal.copy()

        #adjust datetimes
        temp['DataDtTm'] = temp.DataDtTm_adjusted.fillna(temp.DataDtTm)

        #force datatypes needed for vectorized operations and to pass the data set validaiton
        temp['DataDtTm'] = pd.to_datetime(temp.DataDtTm)
        temp['PtID'] = temp.PtID.astype(str)
        temp = temp[['PtID','DataDtTm','CommandedBasalRate']].rename(columns={'PtID': 'patient_id', 'DataDtTm': 'datetime', 'CommandedBasalRate': 'basal_rate'})
        return temp

    def _extract_bolus_event_history(self):
        temp = self.df_bolus.copy()
        #adjust datetimes
        temp['DataDtTm'] = temp.DataDtTm_adjusted.fillna(temp.DataDtTm)
        
        #Match standard and extended boluses (this will incorrectly match purely extended boluses to standard boluses)
        periods = temp.groupby('PtID').apply(lambda x: find_periods(x,'BolusType','DataDtTm', lambda x: x == 'Standard',  lambda x: x == 'Extended', use_last_start_occurence=True))
        periods = periods[periods.apply(lambda x: len(x)>0)] 
        periods = pd.DataFrame(periods.explode(),columns=['Periods'])
        pt_ids_copy = periods.index
        periods = pd.DataFrame(periods.Periods.tolist(), columns=Period._fields)
        periods['PtID'] = pt_ids_copy
        
        #calculate extended bolus delivery durations
        #durations above 8 hours are not possible, therefore treated as extended boluses (no standard part)
        #and assigned 55 minutes duration which is the observed meadian duration
        periods['delivery_duration'] = periods.time_end - periods.time_start
        periods.loc[periods.delivery_duration>timedelta(hours=8), 'delivery_duration'] = timedelta(minutes=55)
        temp['delivery_duration'] = timedelta(0)
        #use .values here, otherwise will try to assign by index
        temp.loc[periods.index_end, 'DataDtTm'] = (periods.time_end - periods.delivery_duration).values
        temp.loc[periods.index_end, 'delivery_duration'] = periods.delivery_duration.values
        
        #force datatypes needed for vectorized operations and to pass the data set validaiton
        temp['DataDtTm'] = pd.to_datetime(temp.DataDtTm)
        temp['PtID'] = temp.PtID.astype(str)
        temp['delivery_duration'] = pd.to_timedelta(temp.delivery_duration)

        temp = temp[['PtID','DataDtTm','BolusAmount','delivery_duration']].rename(columns={'PtID': 'patient_id', 'DataDtTm': 'datetime', 'BolusAmount': 'bolus'})
        return temp

    def _extract_cgm_history(self):
        df_cgm = self.df_cgm.copy()
        #adjust datetimes
        df_cgm['DataDtTm'] = df_cgm.DataDtTm_adjusted.fillna(df_cgm.DataDtTm)

        # replace 0 CGMs with lower upper bounds
        b_zero = df_cgm.CGMValue == 0
        df_cgm.loc[b_zero, 'CGMValue'] = df_cgm.HighLowIndicator.loc[b_zero].replace({ 2: 40, 1: 400 })
        
        #force datatypes to pass the data set validaiton
        df_cgm['PtID'] = df_cgm.PtID.astype(str)
        df_cgm['DataDtTm'] = pd.to_datetime(df_cgm.DataDtTm)

        #reduce, rename, return
        return df_cgm.rename(columns={'PtID': 'patient_id', 'DataDtTm': 'datetime', 'CGMValue': 'cgm'})