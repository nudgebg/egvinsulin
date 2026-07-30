# File: iobp2.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from functools import cached_property
from datetime import timedelta
from babelbetes.pandas_helper import get_df
import os
from babelbetes.date_helper import parse_flair_dates
from babelbetes.studies.studydataset import StudyDataset

class IOBP2(StudyDataset):

    _raw_attrs = ('_df',)

    def __init__(self, study_path: str, subset=False):
        super().__init__(study_path, "IOBP2", subset=subset)
        self._iletFilePath = os.path.join(study_path, 'Data Tables', 'IOBP2DeviceiLet.txt')

    @cached_property
    def _df(self):
        #keep the original raw column names throughout; rename to standard names only at the end of each extractor
        df = get_df(self._iletFilePath, usecols=['PtID', 'DeviceDtTm', 'CGMVal', 'BasalDelivPrev', 'BolusDelivPrev',
                                                  'MealBolusDelivPrev'], subset=self.subset, dtype={'PtID': str, 'CGMVal': float})
        #date time strings without time component are assumed to be midnight
        df['DeviceDtTm'] = df['DeviceDtTm'].transform(parse_flair_dates).astype('datetime64[ns]')
        return df.sort_values(['PtID', 'DeviceDtTm'])

    def _extract_bolus_event_history(self):
        df_bolus = self._df[['PtID', 'DeviceDtTm', 'BolusDelivPrev','MealBolusDelivPrev']].copy()

        #Bolus delivery is separated into two different columns: bolus and meal bolus.
        df_bolus['BolusDelivPrev'] = df_bolus['BolusDelivPrev'] + df_bolus['MealBolusDelivPrev']
        df_bolus = df_bolus[df_bolus['BolusDelivPrev'] > 0]

        #duplicates are resolved using last record
        df_bolus = df_bolus.drop_duplicates(subset=['PtID', 'DeviceDtTm'], keep='last')

        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        df_bolus['DeviceDtTm'] = (df_bolus['DeviceDtTm'] - timedelta(minutes=5))

        #there are no extended boluses in ilet only standard/micro boluses
        df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION] = pd.Timedelta('0 minutes')

        #rename to standard names, reduce, return
        df_bolus = df_bolus.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                                            'DeviceDtTm': self.COL_NAME_DATETIME, 
                                            'BolusDelivPrev': self.COL_NAME_BOLUS})
        return df_bolus[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BOLUS, self.COL_NAME_BOLUS_DELIVERY_DURATION]]

    def _extract_cgm_history(self):
        #get only cgms, this also resolves duplicated rows which have CGM NaN
        df_cgm = self._df.dropna(subset=['CGMVal']).copy()

        # replace magic numbers 39,401 with 40,400
        df_cgm['CGMVal'] = df_cgm['CGMVal'].replace({ 39: 40, 401: 400 })

        #there are only two duplicates (almost identical values), we keep just one
        df_cgm = df_cgm.drop_duplicates(['PtID', 'DeviceDtTm'], keep='first')

        #rename to standard names, reduce, return
        df_cgm = df_cgm.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                                        'DeviceDtTm': self.COL_NAME_DATETIME, 'CGMVal': self.COL_NAME_CGM})
        return df_cgm[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_CGM]]

    def _extract_basal_event_history(self):
        df_basal = self._df[['PtID', 'DeviceDtTm', 'BasalDelivPrev']].copy()

        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        df_basal['DeviceDtTm'] = (df_basal['DeviceDtTm'] - timedelta(minutes=5))

        #convert to rate
        df_basal['BasalDelivPrev'] = df_basal['BasalDelivPrev'] * 12 # 5 minute delivery to hourly rate

        #drop duplicates
        df_basal = df_basal.drop_duplicates(['PtID', 'DeviceDtTm'], keep='last')

        #rename to standard names, reduce, return
        df_basal = df_basal.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                                            'DeviceDtTm': self.COL_NAME_DATETIME, 
                                            'BasalDelivPrev': self.COL_NAME_BASAL_RATE})
        return df_basal[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BASAL_RATE]]

    def _extract_age_data(self):
        age_file_path = os.path.join(self.study_path, 'Data Tables', 'IOBP2PtRoster.txt')
        df_age = get_df(age_file_path, usecols=['PtID', 'AgeAsofEnrollDt'], dtype={'PtID': str, 'AgeAsofEnrollDt': int})
        return df_age.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAsofEnrollDt': self.COL_NAME_AGE})
