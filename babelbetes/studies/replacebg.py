# File: replacebg.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from functools import cached_property
from babelbetes.studies.studydataset import StudyDataset
from datetime import datetime
import numpy as np
import os
from babelbetes.src import pandas_helper, logger


class ReplaceBG(StudyDataset):

    _raw_attrs = ('_df_patient', '_df_uploads', '_df_bolus', '_df_basal', '_df_cgm', '_df_wizard')

    def __init__(self, study_path, subset=False):
        super().__init__(study_path, 'ReplaceBG', subset=subset)
        self._enrollment_start = datetime(2015, 1, 1)

    @cached_property
    def _df_patient(self):
        return pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HPtRoster.txt'),
                                    dtype={'PtID': str}, subset=self.subset)

    @cached_property
    def _df_uploads(self):
        return pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HDeviceUploads.txt'),
                                    dtype={'PtId': str}, subset=self.subset).rename(columns={'PtId': 'PtID'})

    @cached_property
    def _excluded_patients(self) -> set:
        dropped = set(self._df_patient.loc[self._df_patient['PtStatus'] != 'Completed', 'PtID'])
        diasend = set(self._df_uploads.loc[self._df_uploads['DataSource'] == 'Diasend', 'PtID'])
        faulty  = {'244', '277', '288'}
        return dropped | diasend | faulty

    def _apply_study_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter excluded patients and clip to study window [0, RandDtDaysAfterEnroll + 182 days]."""
        df = df[~df['PtID'].isin(self._excluded_patients)].copy()
        #exclude data before/after study start (study was 26 weeks (182 days) after enrollment)
        end_days = self._df_patient.set_index('PtID')['RandDtDaysAfterEnroll'] + 182 
        df['_end_day'] = end_days.reindex(df['PtID']).values
        df = df.query('DeviceDtTmDaysFromEnroll >= 0 and DeviceDtTmDaysFromEnroll <= _end_day')
        return df.drop(columns=['_end_day'])

    @cached_property
    def _df_bolus(self):
        df = pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HDeviceBolus.txt'),
                                  dtype={'PtID': str}, subset=self.subset)
        df['datetime'] = self._enrollment_start + pd.to_timedelta(df['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df['DeviceTm'])
        df['hour_of_day'] = df.datetime.dt.hour
        df['day'] = df.datetime.dt.date
        df.drop(columns=['DeviceTm'], inplace=True)

        # Diasend patients are excluded by _apply_study_filters, so the duration fix below is a no-op
        # for remaining patients. Kept for correctness in case of partial Diasend uploads.
        df = pd.merge(df,
                      self._df_uploads.rename(columns={'RecID': 'ParentHDeviceUploadsID'})[['PtID', 'ParentHDeviceUploadsID', 'DataSource']],
                      on=['PtID', 'ParentHDeviceUploadsID'])
        df.loc[df.DataSource == 'Diasend', 'Duration'] *= 60 * 1000
        df.loc[(df.DataSource == 'Diasend') & df.Extended.isna() & df.Duration.notna(), ['Duration']] = np.nan

        df['Duration'] = pd.to_timedelta(df['Duration'], unit='ms')
        df['ExpectedDuration'] = pd.to_timedelta(df['ExpectedDuration'], unit='ms')
        return df.sort_values(by=['PtID', 'datetime'])

    @cached_property
    def _df_basal(self):
        df = pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HDeviceBasal.txt'),
                                  dtype={'PtID': str}, subset=self.subset)
        df['datetime'] = self._enrollment_start + pd.to_timedelta(df['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df['DeviceTm'])
        df['hour_of_day'] = df.datetime.dt.hour
        df['day'] = df.datetime.dt.date
        df.drop(columns=['DeviceTm'], inplace=True)
        df['Duration'] = pd.to_timedelta(df['Duration'], unit='ms')
        df['ExpectedDuration'] = pd.to_timedelta(df['ExpectedDuration'], unit='ms')
        df['SuprDuration'] = pd.to_timedelta(df['SuprDuration'], unit='ms')
        return df.sort_values(by=['PtID', 'datetime'])

    @cached_property
    def _df_cgm(self):
        df = pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HDeviceCGM.txt'),
                                  dtype={'PtID': str}, subset=self.subset)
        df['datetime'] = self._enrollment_start + pd.to_timedelta(df['DeviceDtTmDaysFromEnroll'], unit='D') + pd.to_timedelta(df['DeviceTm'])
        df['hour_of_day'] = df.datetime.dt.hour
        df['day'] = df.datetime.dt.date
        df.drop(columns=['DeviceTm'], inplace=True)
        return df.sort_values(by=['PtID', 'datetime'])

    def _extract_bolus_event_history(self):
        df_bolus = self._apply_study_filters(self._df_bolus.copy())

        #drop actual duplicates
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
        #resort
        df_bolus = df_bolus.sort_values(by=['PtID','datetime', 'Duration'])

        #reduce, rename, return
        df_bolus = df_bolus[['PtID', 'datetime', 'Normal', 'Duration']]
        df_bolus = df_bolus.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION,
                                        'Normal': self.COL_NAME_BOLUS})
        return df_bolus

    def _extract_basal_event_history(self):
        df_basal = self._apply_study_filters(self._df_basal.copy())

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
        df_cgm = self._apply_study_filters(self._df_cgm.copy())

        #drop Calibrations
        df_cgm = df_cgm.loc[df_cgm.RecordType == 'CGM']

        #handle out of range values
        df_cgm.replace({'GlucoseValue': {39:40, 401:400}},inplace=True)

        #drop temporal duplicates
        df_cgm = df_cgm.drop_duplicates(subset=['PtID', 'datetime'])

        #reduce, rename, return
        df_cgm = df_cgm.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                        'datetime': self.COL_NAME_DATETIME,
                                        'GlucoseValue': self.COL_NAME_CGM})
        return df_cgm[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_CGM]]

    def _extract_age_data(self):
        df_age = self._df_patient.copy()
        df_age = df_age[~df_age['PtID'].isin(self._excluded_patients)]
        df_age = df_age[['PtID', 'AgeAsOfEnrollDt']].rename(
            columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAsOfEnrollDt': self.COL_NAME_AGE})
        return df_age.astype({self.COL_NAME_PATIENT_ID: str, self.COL_NAME_AGE: int})

    @cached_property
    def _df_wizard(self):
        df = pandas_helper.get_df(os.path.join(self.study_path, 'Data Tables', 'HDeviceWizard.txt'),
                                  dtype={'PtId': str}, subset=self.subset).rename(columns={'PtId': 'PtID'})
        df['datetime'] = (self._enrollment_start
                          + pd.to_timedelta(df['DeviceDtTmDaysFromEnroll'], unit='D')
                          + pd.to_timedelta(df['DeviceTm']))
        return df.sort_values(by=['PtID', 'datetime'])

    def _extract_carb_history(self):
        df = self._apply_study_filters(self._df_wizard.copy())
        df = df.dropna(subset=['CarbInput'])
        df = df[df['CarbInput'] > 0]
        # all temporal dups share the same CarbInput value, so drop_duplicates is sufficient
        df = df.drop_duplicates(subset=['PtID', 'datetime', 'CarbInput'])
        df = df[['PtID', 'datetime', 'CarbInput']]
        return df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                  'datetime': self.COL_NAME_DATETIME,
                                  'CarbInput': self.COL_NAME_CARBS})
