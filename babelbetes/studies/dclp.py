# File: dclp.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import os
import io
import pandas as pd
from functools import reduce
from datetime import timedelta
import numpy as np

from babelbetes.src.find_periods import find_periods, Period
from babelbetes.src import pandas_helper
from babelbetes.studies.studydataset import StudyDataset
from babelbetes.src.date_helper import parse_flair_dates


class DCLP3(StudyDataset):
    def _load_data(self, subset):
        data_table_path = os.path.join(self.study_path, 'Data Files')
        df_bolus = pandas_helper.get_df(os.path.join(data_table_path, 'Pump_BolusDelivered.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                          subset=subset)
        df_basal = pandas_helper.get_df(os.path.join(data_table_path, 'Pump_BasalRateChange.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                          subset=subset)
        df_cgm = pandas_helper.get_df(os.path.join(data_table_path, 'Pump_CGMGlucoseValue.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                          subset=subset)

        #remove patients with incomplete data
        intersecting_ids = reduce(np.intersect1d, (df_basal.PtID.unique(), df_bolus.PtID.unique(), df_cgm.PtID.unique()))
        df_basal = df_basal[df_basal.PtID.isin(intersecting_ids)]
        df_bolus = df_bolus[df_bolus.PtID.isin(intersecting_ids)]
        df_cgm = df_cgm[df_cgm.PtID.isin(intersecting_ids)]
        
        #force datatypes (needed for output validation)
        df_cgm['PtID'] = df_cgm.PtID.astype(str)
        df_bolus['PtID'] = df_bolus.PtID.astype(str)
        df_basal['PtID'] = df_basal.PtID.astype(str)

        #setting datetimes (using the adjusted datetime if available)
        df_bolus['DataDtTm'] = pd.to_datetime(df_bolus.DataDtTm_adjusted.fillna(df_bolus.DataDtTm))
        df_basal['DataDtTm'] = pd.to_datetime(df_basal.DataDtTm_adjusted.fillna(df_basal.DataDtTm))
        df_cgm['DataDtTm'] = pd.to_datetime(df_cgm.DataDtTm_adjusted.fillna(df_cgm.DataDtTm))

        df_cgm.drop(columns=['DataDtTm_adjusted'], inplace=True)
        df_bolus.drop(columns=['DataDtTm_adjusted'], inplace=True)
        df_basal.drop(columns=['DataDtTm_adjusted'], inplace=True)
        
        self._df_bolus = df_bolus.sort_values(by=['PtID','DataDtTm'])
        self._df_basal = df_basal.sort_values(by=['PtID','DataDtTm'])
        self._df_cgm = df_cgm.sort_values(by=['PtID','DataDtTm'])
    
    def __init__(self, study_path, study_name='DCLP3'):
        super().__init__(study_path, study_name)

    def _extract_basal_event_history(self):
        df_basal = self._df_basal.copy()

        #duplicates
        _, _, drop_indexes = pandas_helper.get_duplicated_max_indexes(df_basal, ['PtID', 'DataDtTm'], 'CommandedBasalRate')
        df_basal.drop(drop_indexes, inplace=True)

        df_basal = df_basal[['PtID', 'DataDtTm', 'CommandedBasalRate']].rename(columns={'PtID': StudyDataset.COL_NAME_PATIENT_ID, 
                                                                                'DataDtTm': StudyDataset.COL_NAME_DATETIME,
                                                                                'CommandedBasalRate': StudyDataset.COL_NAME_BASAL_RATE})
        return df_basal

    def _extract_bolus_event_history(self):
        df_bolus = self._df_bolus.copy()
        
        #Match standard and extended boluses (this will incorrectly match some orphan extended boluses to "a" previous standard boluses)
        periods = df_bolus.groupby('PtID').apply(lambda x: find_periods(x,'BolusType','DataDtTm', lambda x: x == 'Standard',  lambda x: x == 'Extended', use_last_start_occurence=True))
        periods = periods[periods.apply(lambda x: len(x)>0)] 
        periods = pd.DataFrame(periods.explode(),columns=['Periods'])
        pt_ids_copy = periods.index
        periods = pd.DataFrame(periods.Periods.tolist(), columns=Period._fields)
        periods['PtID'] = pt_ids_copy
        
        #calculate extended bolus delivery durations
        #durations above 8 hours are not possible, therefore treated as extended boluses (no standard part)
        #and assigned 80 minutes duration which is the observed median duration in PEDAP
        periods['delivery_duration'] = periods.time_end - periods.time_start
        periods.loc[periods.delivery_duration>timedelta(hours=8), 'delivery_duration'] = timedelta(minutes=80)
        df_bolus['delivery_duration'] = timedelta(0)
        #use .values here, otherwise will try to assign by index
        df_bolus.loc[periods.index_end, 'DataDtTm'] = (periods.time_end - periods.delivery_duration).values
        df_bolus.loc[periods.index_end, 'delivery_duration'] = periods.delivery_duration.values
        #df_bolus['delivery_duration'] = pd.to_timedelta(df_bolus.delivery_duration)
        df_bolus = df_bolus.sort_values(by=['PtID','DataDtTm', 'delivery_duration'])
        
        # Handling Duplicates
        # After accounting for extended boluses, there are a few duplicates left. We keep the maximum.
        _,_,i_drop = pandas_helper.get_duplicated_max_indexes(df_bolus,['PtID', 'DataDtTm', 'delivery_duration'], 'BolusAmount')
        df_bolus.drop(i_drop, inplace=True)

        #drop zero boluses (there are sometimes a handful of records with 0 bolus amount left)
        df_bolus = df_bolus[df_bolus.BolusAmount > 0]

        df_bolus = df_bolus[['PtID', 'DataDtTm', 'BolusAmount', 'delivery_duration']].rename(columns={'PtID': StudyDataset.COL_NAME_PATIENT_ID,
                                                                                              'DataDtTm': StudyDataset.COL_NAME_DATETIME,
                                                                                              'BolusAmount': StudyDataset.COL_NAME_BOLUS})
        return df_bolus

    def _extract_cgm_history(self):
        df_cgm = self._df_cgm.copy()

        #duplicates
        df_cgm.drop_duplicates(['PtID', 'DataDtTm'], keep='first', inplace=True)

        # replace 0 CGMs with lower upper bounds
        b_zero = df_cgm.CGMValue == 0
        df_cgm.loc[b_zero, 'CGMValue'] = df_cgm.HighLowIndicator.loc[b_zero].replace({ 2: 40, 1: 400 })
        
        #reduce, rename, return
        df_cgm = df_cgm[['PtID','DataDtTm','CGMValue']]
        df_cgm = df_cgm.rename(columns={'PtID': StudyDataset.COL_NAME_PATIENT_ID, 
                                        'DataDtTm': StudyDataset.COL_NAME_DATETIME,
                                        'CGMValue': StudyDataset.COL_NAME_CGM})
        return df_cgm

class DCLP5(DCLP3):
    def __init__(self, study_path, study_name='DCLP5'):
        super().__init__(study_path, study_name)
        #self.study_name = 'DCLP5' #super sets it to DCLP3, so we override it here
    
    def _load_data(self, subset):
        df_bolus = pandas_helper.get_df(os.path.join(self.study_path, 'DCLP5TandemBolus_Completed_Combined_b.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                          subset=subset)
        df_basal = pandas_helper.get_df(os.path.join(self.study_path, 'DCLP5TandemBASALRATECHG_b.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                          subset=subset)
        df_cgm = pandas_helper.get_df(os.path.join(self.study_path, 'DCLP5TandemCGMDATAGXB_b.txt'),
                          usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                          subset=subset)

        #force datatypes (needed for output validation)
        df_cgm['PtID'] = df_cgm.PtID.astype(str)
        df_bolus['PtID'] = df_bolus.PtID.astype(str)
        df_basal['PtID'] = df_basal.PtID.astype(str)

        #setting datetimes (using the adjusted datetime if available)
        df_bolus['DataDtTm'] = df_bolus.DataDtTm_adjusted.fillna(df_bolus.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df_basal['DataDtTm'] = df_basal.DataDtTm_adjusted.fillna(df_basal.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df_cgm['DataDtTm'] = df_cgm.DataDtTm_adjusted.fillna(df_cgm.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')

        df_cgm.drop(columns=['DataDtTm_adjusted'], inplace=True)
        df_bolus.drop(columns=['DataDtTm_adjusted'], inplace=True)
        df_basal.drop(columns=['DataDtTm_adjusted'], inplace=True)

        self._df_bolus = df_bolus.sort_values(by=['PtID','DataDtTm'])
        self._df_basal = df_basal.sort_values(by=['PtID','DataDtTm'])
        self._df_cgm = df_cgm.sort_values(by=['PtID','DataDtTm'])
