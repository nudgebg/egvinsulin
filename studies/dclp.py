import os
import pandas as pd
from functools import reduce
from datetime import timedelta
import numpy as np

from src.find_periods import find_periods, Period
from src import pandas_helper
from .studydataset import StudyDataset
from src.date_helper import parse_flair_dates

class DCLP3(StudyDataset):
    def _load_data(self, subset):
        data_table_path = os.path.join(self.study_path, 'Data Files')
        df_bolus = pd.read_csv(os.path.join(data_table_path, 'Pump_BolusDelivered.txt'), sep='|', low_memory=False, 
                               usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                               skiprows=lambda x: (x % 10 != 0) & subset)
        df_basal = pd.read_csv(os.path.join(data_table_path, 'Pump_BasalRateChange.txt'), sep='|', low_memory=False, 
                               usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                               skiprows=lambda x: (x % 10 != 0) & subset)
        df_cgm = pd.read_csv(os.path.join(data_table_path, 'Pump_CGMGlucoseValue.txt'), sep='|', low_memory=False, 
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                             skiprows=lambda x: (x % 10 != 0) & subset)

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
        
        #force datatypes (needed for output validation)
        df_cgm['PtID'] = df_cgm.PtID.astype(str)
        df_bolus['PtID'] = df_bolus.PtID.astype(str)
        df_basal['PtID'] = df_basal.PtID.astype(str)

        self.datetime_col = 'datetime'
        #setting datetimes (using the adjusted datetime if available)
        df_bolus[self.datetime_col] = pd.to_datetime(df_bolus.DataDtTm_adjusted.fillna(df_bolus.DataDtTm))
        df_basal[self.datetime_col] = pd.to_datetime(df_basal.DataDtTm_adjusted.fillna(df_basal.DataDtTm))
        df_cgm[self.datetime_col] = pd.to_datetime(df_cgm.DataDtTm_adjusted.fillna(df_cgm.DataDtTm))

        df_cgm.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        df_bolus.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        df_basal.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        
        self.df_bolus = df_bolus.sort_values(by=['PtID',self.datetime_col])
        self.df_basal = df_basal.sort_values(by=['PtID',self.datetime_col])
        self.df_cgm = df_cgm.sort_values(by=['PtID',self.datetime_col])
    
    def __init__(self, study_path):
        super().__init__(study_path, 'DCLP3')

    def _extract_basal_event_history(self):
        temp = self.df_basal.copy()
        temp = temp[['PtID', self.datetime_col, 'CommandedBasalRate']].rename(columns={'PtID': 'patient_id', 'CommandedBasalRate': 'basal_rate'})
        return temp

    def _extract_bolus_event_history(self):
        temp = self.df_bolus.copy()
        
        #Match standard and extended boluses (this will incorrectly match purely extended boluses to standard boluses)
        periods = temp.groupby('PtID').apply(lambda x: find_periods(x,'BolusType',self.datetime_col, lambda x: x == 'Standard',  lambda x: x == 'Extended', use_last_start_occurence=True))
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
        temp.loc[periods.index_end, self.datetime_col] = (periods.time_end - periods.delivery_duration).values
        temp.loc[periods.index_end, 'delivery_duration'] = periods.delivery_duration.values
        
        temp['delivery_duration'] = pd.to_timedelta(temp.delivery_duration)

        temp = temp[['PtID', self.datetime_col, 'BolusAmount', 'delivery_duration']].rename(columns={'PtID': 'patient_id', 'BolusAmount': 'bolus'})
        return temp

    def _extract_cgm_history(self):
        df_cgm = self.df_cgm.copy()
        
        # replace 0 CGMs with lower upper bounds
        b_zero = df_cgm.CGMValue == 0
        df_cgm.loc[b_zero, 'CGMValue'] = df_cgm.HighLowIndicator.loc[b_zero].replace({ 2: 40, 1: 400 })
        
        #reduce, rename, return
        df_cgm = df_cgm[['PtID',self.datetime_col,'CGMValue']]
        df_cgm = df_cgm.rename(columns={'PtID': 'patient_id', 'CGMValue': 'cgm'})
        return df_cgm

class DCLP5(DCLP3):
    def __init__(self, study_path):
        super().__init__(study_path)
        self.study_name = 'DCLP5'
    
    def _load_data(self, subset):
        df_bolus = pd.read_csv(os.path.join(self.study_path, 'DCLP5TandemBolus_Completed_Combined_b.txt'), sep='|', low_memory=False, 
                               usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                               skiprows=lambda x: (x % 10 != 0) & subset)
        df_basal = pd.read_csv(os.path.join(self.study_path, 'DCLP5TandemBASALRATECHG_b.txt'), sep='|', low_memory=False, 
                               usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                               skiprows=lambda x: (x % 10 != 0) & subset)
        df_cgm = pd.read_csv(os.path.join(self.study_path, 'DCLP5TandemCGMDATAGXB_b.txt'), sep='|', low_memory=False, 
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                             skiprows=lambda x: (x % 10 != 0) & subset)

        # Handle duplicates
        # for cgm we just keep the first value
        df_cgm.drop_duplicates(['PtID', 'DataDtTm'], keep='first', inplace=True)
        # for basal we decided top use the maximum value
        _, _, drop_indexes = pandas_helper.get_duplicated_max_indexes(df_basal, ['PtID', 'DataDtTm'], 'CommandedBasalRate')
        df_basal.drop(drop_indexes, inplace=True)

        #force datatypes (needed for output validation)
        df_cgm['PtID'] = df_cgm.PtID.astype(str)
        df_bolus['PtID'] = df_bolus.PtID.astype(str)
        df_basal['PtID'] = df_basal.PtID.astype(str)

        #setting datetimes (using the adjusted datetime if available)
        self.datetime_col = 'datetime'
        df_bolus[self.datetime_col] = df_bolus.DataDtTm_adjusted.fillna(df_bolus.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df_basal[self.datetime_col] = df_basal.DataDtTm_adjusted.fillna(df_basal.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df_cgm[self.datetime_col] = df_cgm.DataDtTm_adjusted.fillna(df_cgm.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')

        df_cgm.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        df_bolus.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        df_basal.drop(columns=['DataDtTm', 'DataDtTm_adjusted'], inplace=True)
        
        self.df_bolus = df_bolus
        self.df_basal = df_basal
        self.df_cgm = df_cgm