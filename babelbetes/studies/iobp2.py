# File: iobp2.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from functools import cached_property
from datetime import timedelta
from babelbetes.src.pandas_helper import get_df
import os
from babelbetes.src.date_helper import parse_flair_dates
from babelbetes.studies.studydataset import StudyDataset

class IOBP2(StudyDataset):

    _raw_attrs = ('_df',)

    def __init__(self, study_path: str, subset=False):
        super().__init__(study_path, "IOBP2", subset=subset)
        self._iletFilePath = os.path.join(study_path, 'Data Tables', 'IOBP2DeviceiLet.txt')

    def _load_data(self, subset=False):
        pass  # data loaded lazily via cached_property file accessors

    @cached_property
    def _df(self):
        df = get_df(self._iletFilePath, usecols=['PtID', 'DeviceDtTm', 'CGMVal', 'BasalDelivPrev', 'BolusDelivPrev',
                                                  'MealBolusDelivPrev'], subset=self.subset, dtype={'PtID': str, 'CGMVal': float})
        df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'DeviceDtTm': self.COL_NAME_DATETIME, 'CGMVal': self.COL_NAME_CGM,
                        'BasalDelivPrev': self.COL_NAME_BASAL_RATE, 'BolusDelivPrev': self.COL_NAME_BOLUS}, inplace=True)
        #date time strings without time component are assumed to be midnight
        df[self.COL_NAME_DATETIME] = df[self.COL_NAME_DATETIME].transform(parse_flair_dates).astype('datetime64[ns]')
        return df.sort_values([self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME])

    def _extract_bolus_event_history(self):
        df_bolus = self._df.dropna(subset=[self.COL_NAME_BOLUS, 'MealBolusDelivPrev']).copy()

        #Bolus delivery is separated into two different columns: bolus and meal bolus.
        df_bolus[self.COL_NAME_BOLUS] = df_bolus[self.COL_NAME_BOLUS] + df_bolus['MealBolusDelivPrev']

        #there are no extended boluses in ilet only standard/micro boluses
        df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION] = pd.Timedelta('0 minutes')

        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        df_bolus[self.COL_NAME_DATETIME] = (df_bolus[self.COL_NAME_DATETIME] - timedelta(minutes=5))

        #0 values are dropped
        df_bolus = df_bolus[df_bolus.bolus > 0]

        #reduce, return
        df_bolus = df_bolus[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BOLUS, self.COL_NAME_BOLUS_DELIVERY_DURATION]]
        return df_bolus

    def _extract_cgm_history(self):
        #get only cgms
        df_cgm = self._df.dropna(subset=[self.COL_NAME_CGM]).copy()

        # replace magic numbers 39,401 with 40,400
        df_cgm[self.COL_NAME_CGM] = df_cgm[self.COL_NAME_CGM].replace({ 39: 40, 401: 400 })

        #there are only two duplicates (almost identical values), we keep just one
        df_cgm = df_cgm.drop_duplicates([self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME], keep='first')

        #reduce, return
        df_cgm = df_cgm[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_CGM]]
        return df_cgm

    def _extract_basal_event_history(self):
        df_basal = self._df.dropna(subset=[self.COL_NAME_BASAL_RATE]).copy()

        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        df_basal[self.COL_NAME_DATETIME] = (df_basal[self.COL_NAME_DATETIME] - timedelta(minutes=5))

        #convert to rate
        df_basal[self.COL_NAME_BASAL_RATE] = df_basal[self.COL_NAME_BASAL_RATE] * 12 # 5 minute delivery to hourly rate

        #drop duplicates
        df_basal = df_basal.drop_duplicates([self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME], keep='first')

        #reduce, return
        df_basal = df_basal[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BASAL_RATE]]
        return df_basal

    def _extract_age_data(self):
        age_file_path = os.path.join(self.study_path, 'Data Tables', 'IOBP2PtRoster.txt')
        df_age = get_df(age_file_path, usecols=['PtID', 'AgeAsofEnrollDt'], dtype={'PtID': str, 'AgeAsofEnrollDt': int})
        return df_age.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAsofEnrollDt': self.COL_NAME_AGE})
