# File: t1dexi.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta
from functools import cached_property
import isodate
import zipfile_deflate64

from babelbetes.studies.studydataset import StudyDataset
from babelbetes.src.logger import Logger
from babelbetes.src.pandas_helper import get_duplicated_max_indexes, get_df

def load_facm(path, subset):
        facm = get_df(path, subset=subset)
        facm = facm.replace('', np.nan).astype({'USUBJID': 'str', 'FAORRES': 'float'})

        #drop columns with no additional, duplicated or corrupt information
        facm = facm.drop(columns=['STUDYID','DOMAIN','FASEQ',# not informative
                                  'FAOBJ', #Always INSULIN, can be ignored.
                                  'FAORRESU', 'FASTRESU', #We don't need the unit. FAORRESU holds the original unit while FASTRESU is Nan when U/hr, we use FATEST to infer
                                  'FATESTCD',# abbrev version of `FATEST`, we use `FATEST`
                                  'FACAT',# BASAL or BOLUS. Not needed, we use FATEST which is more detailed (separtes between basal deliveries and basal flow rates)
                                  'FASTRESC','FASTRESN', # insulin amount without any additional information compared to FAORRES
                                  'INSDVSRC',# Source of insulin delivery (Injections or Pump). Not needed for extraction.
                                  'INSSTYPE'# Insulin subtype (e.g., suspend, etc.) but many NaN values making it unreliable to select basal, not needed
                                  ])

        #datetimes
        facm['FADTC'] = facm['FADTC'].apply(lambda x: datetime(1960, 1, 1) + timedelta(seconds=x) if pd.notnull(x) else pd.NaT)
        #durations
        facm['FADUR'] = facm.FADUR.dropna().apply(isodate.parse_duration, as_timedelta_if_possible=True)
        #drop duplciates
        facm = facm.drop_duplicates()
        return facm.sort_values('FADTC')


def load_dx(path):
        dx = get_df(path).replace('', np.nan)
        dx = dx.drop(columns=['DXSCAT','DXPRESP','STUDYID','DOMAIN','SPDEVID','DXSEQ','DXCAT','DXSCAT','DXSTRTPT','DXDTC','DXENRTPT','DXEVINTX','VISIT'])
        return dx


def load_lb(path, subset):
    lb = get_df(path, subset=subset)
    lb = lb.replace('', np.nan).astype({'USUBJID': 'str'})[['USUBJID','LBCAT','LBORRES','LBDTC']]
    #drop hab1c readings and keep only CGM readings
    lb = lb.loc[lb.LBCAT=='CGM']
    #date conversion
    lb['LBDTC'] = lb['LBDTC'].apply(lambda x: datetime(1960, 1, 1) + timedelta(seconds=x) if pd.notnull(x) else pd.NaT)
    lb.drop(columns='LBCAT',inplace=True)
    return lb


def overlaps(df):
    assert df.FADTC.is_monotonic_increasing
    end = df.FADTC + df.FADUR
    next = df.FADTC.shift(-1)
    overlap = (next < end)
    return overlap

class T1DEXI(StudyDataset):

    _raw_attrs = ('_facm', '_lb')

    def __init__(self, study_path, study_name='T1DEXI', subset=False, drop_mdi=False):
        super().__init__(study_path, study_name, subset=subset)
        self.drop_mdi = drop_mdi

    def _load_data(self, subset=False):
        pass  # data loaded lazily via cached_property file accessors

    @cached_property
    def _facm(self):
        dx = load_dx(os.path.join(self.study_path, 'DX.xpt'))
        facm = load_facm(os.path.join(self.study_path, 'FACM.xpt'), self.subset)

        #only keep patients that have data in all three datasets
        shared_patients = set(facm.USUBJID.unique()) & set(dx.USUBJID.unique()) & set(self._lb.USUBJID.unique())
        facm = facm[facm['USUBJID'].isin(shared_patients)]
        dx = dx[dx['USUBJID'].isin(shared_patients)]

        if self.drop_mdi:
            mdi_patients = dx.loc[dx.DXTRT=='MULTIPLE DAILY INJECTIONS'].USUBJID.unique()
            facm = facm.loc[~facm.USUBJID.isin(mdi_patients)]

        # merge device data (DXTRT) to facm (we need this later to distinguish between pump and mdi patients)
        facm = pd.merge(facm, dx.loc[~dx.DXTRT.isin(['INSULIN PUMP','CLOSED LOOP INSULIN PUMP'])], on='USUBJID', how='left')
        return facm.astype({'USUBJID': 'str'})

    @cached_property
    def _lb(self):
        lb = load_lb(os.path.join(self.study_path, 'LB.xpt'), self.subset)
        shared_patients = set(lb.USUBJID.unique())
        return lb[lb['USUBJID'].isin(shared_patients)]

    def _extract_bolus_event_history(self):
        bolus_rows = self._facm.loc[self._facm.FATEST=='BOLUS INSULIN'].copy()

        #assign FAORRES values to INSNMBOL when both INSMBOL and INSEXBOL are empty (treat as normal bolus)
        bolus_rows.loc[(bolus_rows.FATEST=='BOLUS INSULIN') & bolus_rows[['INSEXBOL','INSNMBOL']].isna().all(axis=1),'INSMNBL'] = bolus_rows.FAORRES

        # Replace values in FAORRES, INSEXBOL, INSMBOL that are < 1e-20 with zero
        bolus_rows.loc[bolus_rows.FAORRES < 1e-20, 'FAORRES'] = 0
        bolus_rows.loc[bolus_rows.INSEXBOL < 1e-20, 'INSEXBOL'] = 0
        bolus_rows.loc[bolus_rows.INSNMBOL < 1e-20, 'INSNMBOL'] = 0

        bolus_rows.loc[:,'INSNMBOL'] = bolus_rows.INSNMBOL.fillna(0)
        bolus_rows.loc[:,'INSEXBOL'] = bolus_rows.INSEXBOL.fillna(0)

        #split extended and normal bolus rows
        normal   = bolus_rows.loc[bolus_rows.INSNMBOL>0][['USUBJID','FADTC','FADUR','INSNMBOL']].copy()
        normal = normal.rename(columns={'INSNMBOL':self.COL_NAME_BOLUS})
        normal['FADUR'] = timedelta(0) #when there was a normal bolus, it would still carry the extended bolus duration
        extended = bolus_rows.loc[bolus_rows.INSEXBOL>0][['USUBJID','FADTC','FADUR','INSEXBOL']].copy()
        extended = extended.rename(columns={'INSEXBOL': self.COL_NAME_BOLUS})

        #merge back into single dataframe
        bolus_rows = pd.concat([normal,extended],ignore_index=True).sort_values(by=['USUBJID','FADTC','FADUR'])

        # Reduce, Rename
        bolus_rows = bolus_rows.rename(columns={'USUBJID': self.COL_NAME_PATIENT_ID,
                                                'FADTC': self.COL_NAME_DATETIME,
                                                'FADUR': self.COL_NAME_BOLUS_DELIVERY_DURATION})
        return bolus_rows

    def _extract_basal_event_history(self):
        basal_rows = self._facm.loc[self._facm.FATEST.isin(['BASAL INSULIN','BASAL FLOW RATE'])].copy()

        #drop mdi basal flow rates (these are empty)
        basal_rows = basal_rows.loc[~ ((basal_rows.FATEST=='BASAL FLOW RATE') & (basal_rows.DXTRT=='MULTIPLE DAILY INJECTIONS'))]

        ## convert to flow rates: approximate duration using time between the basal injections
        mdi_basal_injections = basal_rows.loc[(basal_rows.DXTRT == 'MULTIPLE DAILY INJECTIONS') & (basal_rows.FATEST=='BASAL INSULIN')]
        if not mdi_basal_injections.empty:
            mdi_basal_injections.loc[:,'FADUR'] = mdi_basal_injections.groupby('USUBJID',group_keys=False).FADTC.apply(lambda x: x.sort_values().diff().shift(-1))
            basal_rows.loc[mdi_basal_injections.index, 'FADUR'] = mdi_basal_injections.FADUR
            basal_rows.loc[mdi_basal_injections.index, 'FAORRES'] = mdi_basal_injections.FAORRES/(mdi_basal_injections.FADUR.dt.total_seconds()/3600)
            basal_rows.loc[mdi_basal_injections.index, 'FATEST'] = 'BASAL FLOW RATE'

        ## only keep flow rates
        basal_rows = basal_rows.loc[basal_rows.FATEST=='BASAL FLOW RATE']

        #drop duplicated flow rates, keeping the maximum value
        (_,_,i_drop) =  get_duplicated_max_indexes(basal_rows, ['USUBJID','FADTC'], 'FAORRES')
        basal_rows = basal_rows.drop(i_drop)

        #fill NaN basal rates with zeros (in some cases, these are suspends, in others we don't know)
        basal_rows.loc[:,'FAORRES'] = basal_rows.FAORRES.fillna(0)

        ## correct for overlaps
        def correct_overlap(df):
            fadur = df.FADUR
            fadur[df.overlaps] = df.FADTC.diff().shift(-1)[df.overlaps]
            return fadur
        basal_rows['overlaps'] = basal_rows.groupby('USUBJID').apply(overlaps, include_groups=False).droplevel(0)
        basal_rows['FADUR'] = basal_rows.groupby('USUBJID', group_keys=False).apply(correct_overlap)
        basal_rows.drop(columns='overlaps', inplace=True)

        # Reduce, Rename
        basal_rows = basal_rows[['USUBJID','FADTC','FAORRES']]
        basal_rows = basal_rows.rename(columns={'USUBJID': self.COL_NAME_PATIENT_ID,
                                                'FADTC': self.COL_NAME_DATETIME,
                                                'FAORRES': self.COL_NAME_BASAL_RATE})
        return basal_rows

    def _extract_cgm_history(self):
        lb = self._lb.drop_duplicates(subset=['USUBJID','LBDTC'],keep='first')
        return lb.rename(columns={
            'USUBJID': self.COL_NAME_PATIENT_ID,
            'LBDTC': self.COL_NAME_DATETIME,
            'LBORRES': self.COL_NAME_CGM
        })

    def _extract_age_data(self):
        df_age = get_df(os.path.join(self.study_path, 'DM.xpt'), usecols=['USUBJID', 'AGE'], dtype={'USUBJID': str, 'AGE': int})
        return df_age.rename(columns={'USUBJID': self.COL_NAME_PATIENT_ID, 'AGE': self.COL_NAME_AGE})


class T1DEXIP(T1DEXI):
    def __init__(self, study_path, study_name='T1DEXIP', subset=False, drop_mdi=False):
        super().__init__(study_path, study_name, subset=subset, drop_mdi=drop_mdi)

    def _extract_cgm_history(self):
        glucose = super()._extract_cgm_history()
        #there is one row with values > 401, we remove it
        return glucose.loc[glucose[self.COL_NAME_CGM] <= 401]
