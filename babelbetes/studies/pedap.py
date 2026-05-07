# File: pedap.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
from functools import cached_property
from babelbetes.studies.studydataset import StudyDataset
import os
import pandas as pd
from babelbetes.date_helper import parse_flair_dates
from babelbetes import pandas_helper as ph
from babelbetes.logger import Logger

logger = Logger.get_logger(__name__)

class PEDAP(StudyDataset):

    _raw_attrs = ('_df_bolus', '_df_basal', '_df_cgm')

    def __init__(self, study_path, subset=False):
        super().__init__(study_path, 'PEDAP', subset=subset)
        self._data_table_path = os.path.join(study_path, 'Data Files')

    @cached_property
    def _df_bolus(self):
        df = ph.get_df(os.path.join(self._data_table_path, 'PEDAPTandemBolusDelivered.txt'),
                       usecols=['PtID', 'DeviceDtTm', 'BolusAmount', 'Duration', 'ExtendedBolusPortion', 'BolusType'],
                       subset=self.subset)
        df = df.drop_duplicates(subset=['PtID', 'DeviceDtTm', 'BolusAmount'])
        df = df.dropna(subset=['DeviceDtTm'])
        df['DeviceDtTm'] = parse_flair_dates(df['DeviceDtTm'])
        return df.sort_values(by=['PtID', 'DeviceDtTm'])

    @cached_property
    def _df_basal(self):
        df = ph.get_df(os.path.join(self._data_table_path, 'PEDAPTandemBASALDELIVERY.txt'),
                       usecols=['PtID', 'DeviceDtTm', 'BasalRate'],
                       subset=self.subset)
        df = df.drop_duplicates(subset=['PtID', 'DeviceDtTm', 'BasalRate'])
        df['DeviceDtTm'] = parse_flair_dates(df['DeviceDtTm'])
        return df.sort_values(by=['PtID', 'DeviceDtTm'])

    @cached_property
    def _df_cgm(self):
        df = ph.get_df(os.path.join(self._data_table_path, 'PEDAPTandemCGMDATAGXB.txt'),
                       usecols=['PtID', 'DeviceDtTm', 'CGMValue', 'HighLowIndicator'],
                       subset=self.subset)
        df = df.drop_duplicates(subset=['PtID', 'DeviceDtTm'])
        df['DeviceDtTm'] = parse_flair_dates(df['DeviceDtTm'])
        return df.sort_values(by=['PtID', 'DeviceDtTm'])

    def _extract_basal_event_history(self):
        temp = self._df_basal.copy()

        #force datetime, needed for vectorized operations and to pass the data set validaiton
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)

        # Drop duplicates (majority are identical) while for those with identical time, keeping the maximum basal rate.
        _,_,i_drop = ph.get_duplicated_max_indexes(temp, ['PtID', 'DeviceDtTm'], 'BasalRate')
        temp = temp.drop(i_drop)

        #reduce rename return
        temp = temp[['PtID', 'BasalRate', 'DeviceDtTm']].astype({'PtID':str})
        temp = temp.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime', 'BasalRate': 'basal_rate'})
        return temp

    def _extract_bolus_event_history(self):
        temp = self._df_bolus.copy()

        #force datetime, needed for vectorized operations and to pass the data set validaiton
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)

        # convert to adjust start delivery times (only affects extended boluses)
        temp['Duration'] = pd.to_timedelta(temp.Duration, unit='m')

        #Extended boluses reported upon completion, adjust start time accordingly
        bMaskLater = temp.ExtendedBolusPortion == 'Later'
        temp.loc[bMaskLater, 'DeviceDtTm'] = temp.loc[bMaskLater, 'DeviceDtTm'] - temp.loc[bMaskLater, 'Duration']
        temp = temp.sort_values(by=['PtID','DeviceDtTm'])

        #Immediate boluses reported with identical duration, set to 0
        bMaskNow = temp.ExtendedBolusPortion == 'Now'
        temp.loc[bMaskNow, 'Duration'] = pd.Timedelta(0)

        #reduce rename return
        temp = temp[['PtID', 'DeviceDtTm', 'BolusAmount', 'Duration']].astype({'PtID':str})
        temp = temp.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime',
                           'BolusAmount': 'bolus', 'Duration': 'delivery_duration'})
        return temp

    def _extract_cgm_history(self):
        temp = self._df_cgm.copy()

        # replace 0 CGMs with lower upper bounds
        b_zero = temp.CGMValue == 0
        temp.loc[b_zero, 'CGMValue'] = temp.HighLowIndicator.loc[b_zero].replace({ 2: 40, 1: 400 })

        #reduce rename return
        temp = temp[['PtID', 'DeviceDtTm', 'CGMValue']].astype({'PtID':str})
        temp['DeviceDtTm'] = pd.to_datetime(temp.DeviceDtTm)
        temp = temp.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                    'DeviceDtTm': self.COL_NAME_DATETIME,
                                    'CGMValue': self.COL_NAME_CGM})
        temp[self.COL_NAME_CGM] = temp[self.COL_NAME_CGM].astype(float)
        return temp

    def _extract_age_data(self):
        age_file_path = os.path.join(self.study_path, 'Data Files', 'PtRoster.txt')
        return ph.get_df(age_file_path, usecols=['PtID', 'AgeAsofEnrollDt'],
                         dtype={'PtID': str, 'AgeAsofEnrollDt': int}
                         ).rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                           'AgeAsofEnrollDt': self.COL_NAME_AGE})
