# File: dclp.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import os
import pandas as pd
from functools import cached_property
from datetime import timedelta

from babelbetes.src.find_periods import find_periods, Period
from babelbetes.src import pandas_helper
from babelbetes.studies.studydataset import StudyDataset
from babelbetes.src.date_helper import parse_flair_dates


class DCLP3(StudyDataset):

    _raw_attrs = ('_df_bolus', '_df_basal', '_df_cgm')

    def __init__(self, study_path, study_name='DCLP3', subset=False):
        super().__init__(study_path, study_name, subset=subset)
        self._data_table_path = os.path.join(study_path, 'Data Files')

    def _load_data(self, subset=False):
        pass  # data loaded lazily via cached_property file accessors

    @cached_property
    def _df_bolus(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'Pump_BolusDelivered.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = pd.to_datetime(df.DataDtTm_adjusted.fillna(df.DataDtTm))
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

    @cached_property
    def _df_basal(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'Pump_BasalRateChange.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = pd.to_datetime(df.DataDtTm_adjusted.fillna(df.DataDtTm))
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

    @cached_property
    def _df_cgm(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'Pump_CGMGlucoseValue.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = pd.to_datetime(df.DataDtTm_adjusted.fillna(df.DataDtTm))
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

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
        df_cgm[StudyDataset.COL_NAME_CGM] = df_cgm[StudyDataset.COL_NAME_CGM].astype(float)
        return df_cgm

    def _extract_age_data(self):
        age_file_path = os.path.join(self._data_table_path, 'DiabScreening_a.txt')
        df_age = pandas_helper.get_df(age_file_path, usecols=['PtID', 'AgeAtEnrollment'],
                                      encoding='utf-16', dtype={'PtID': str, 'AgeAtEnrollment': int})
        return df_age.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAtEnrollment': self.COL_NAME_AGE})


class DCLP5(DCLP3):

    def __init__(self, study_path, study_name='DCLP5', subset=False):
        super().__init__(study_path, study_name, subset=subset)
        self._data_table_path = study_path  # files are in the root, not a subdirectory

    @cached_property
    def _df_bolus(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'DCLP5TandemBolus_Completed_Combined_b.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType', 'DataDtTm_adjusted'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = df.DataDtTm_adjusted.fillna(df.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

    @cached_property
    def _df_basal(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'DCLP5TandemBASALRATECHG_b.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate', 'DataDtTm_adjusted'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = df.DataDtTm_adjusted.fillna(df.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

    @cached_property
    def _df_cgm(self):
        df = pandas_helper.get_df(os.path.join(self._data_table_path, 'DCLP5TandemCGMDATAGXB_b.txt'),
                                  usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue', 'DataDtTm_adjusted', 'HighLowIndicator'],
                                  subset=self.subset)
        df['PtID'] = df.PtID.astype(str)
        df['DataDtTm'] = df.DataDtTm_adjusted.fillna(df.DataDtTm).transform(parse_flair_dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p')
        df.drop(columns=['DataDtTm_adjusted'], inplace=True)
        return df.sort_values(by=['PtID', 'DataDtTm'])

    def _extract_age_data(self):
        age_file_path = os.path.join(self._data_table_path, 'PtRoster.txt')
        df_age = pandas_helper.get_df(age_file_path, usecols=['PtID', 'AgeAtEnrollment'],
                                      dtype={'PtID': str, 'AgeAtEnrollment': int})
        return df_age.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAtEnrollment': self.COL_NAME_AGE})
