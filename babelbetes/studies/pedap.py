# File: pedap.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
from datetime import timedelta
from babelbetes.studies.studydataset import StudyDataset
import os
import pandas as pd
from babelbetes.src.date_helper import parse_flair_dates
from babelbetes.src import pandas_helper as ph


class PEDAP(StudyDataset):
    def __init__(self, study_path):
        super().__init__(study_path, 'PEDAP')

    def _load_data(self, subset):
        data_table_path = os.path.join(self.study_path, 'Data Files')

        df_bolus = ph.get_df(os.path.join(data_table_path, 'PEDAPTandemBolusDelivered.txt'), usecols=['PtID', 'DeviceDtTm',
                                                                                                   'BolusAmount',
                                                                                                   'Duration','ExtendedBolusPortion','BolusType'],
                          subset=subset)
        df_basal = ph.get_df(os.path.join(data_table_path, 'PEDAPTandemBASALDELIVERY.txt'), usecols=['PtID', 'DeviceDtTm',
                                                                                                 'BasalRate'],
                          subset=subset)
        df_cgm = ph.get_df(os.path.join(data_table_path, 'PEDAPTandemCGMDATAGXB.txt'), usecols=['PtID', 'DeviceDtTm',
                                                                                             'CGMValue','HighLowIndicator'],
                          subset=subset)
        
        # remove duplicated rows
        df_basal = df_basal.drop_duplicates(subset=['PtID','DeviceDtTm','BasalRate'])
        df_bolus = df_bolus.drop_duplicates(subset=['PtID','DeviceDtTm','BolusAmount'])
        df_cgm = df_cgm.drop_duplicates(subset=['PtID','DeviceDtTm'])
        
        #remove missing DeviceDtTm for the bolus dataset (there are 4 entries)
        df_bolus = df_bolus.dropna(subset=['DeviceDtTm'])

        df_bolus['DeviceDtTm'] = parse_flair_dates(df_bolus['DeviceDtTm'])
        df_basal['DeviceDtTm'] = parse_flair_dates(df_basal['DeviceDtTm'])
        df_cgm['DeviceDtTm'] = parse_flair_dates(df_cgm['DeviceDtTm'])

    
        self._df_bolus = df_bolus.sort_values(by=['PtID','DeviceDtTm'])
        self._df_basal = df_basal.sort_values(by=['PtID','DeviceDtTm'])
        self._df_cgm = df_cgm.sort_values(by=['PtID','DeviceDtTm'])

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
        return temp
