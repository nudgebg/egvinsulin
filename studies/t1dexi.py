import pandas as pd
import os 
import numpy as np
from datetime import datetime, timedelta
import isodate

from studies.studydataset import StudyDataset
from src.logger import Logger
from src.pandas_helper import get_duplicated_max_indexes

def load_facm(path, subset):
        
        #if subset, read only the first 25k Rows
        if subset:
            chunk_size = 25000 
            facm_iter = pd.read_sas(path, encoding='latin-1', chunksize=chunk_size)
            facm = next(facm_iter)
        else:
            facm = pd.read_sas(path,encoding='latin-1',)
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
        dx = pd.read_sas(path, encoding='latin-1').replace('', np.nan)
        dx = dx.drop(columns=['DXSCAT','DXPRESP','STUDYID','DOMAIN','SPDEVID','DXSEQ','DXCAT','DXSCAT','DXSTRTPT','DXDTC','DXENRTPT','DXEVINTX','VISIT'])
        return dx

def load_lb(path, subset):
    #if subset, read only the first 25k Rows
    if subset:
        chunk_size = 25000 
        lb_iter = pd.read_sas(path, encoding='latin-1', chunksize=chunk_size)
        lb = next(lb_iter)
    else:
        lb = pd.read_sas(path,encoding='latin-1',)
    
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
    def __init__(self, study_path, drop_mdi=False):
        super().__init__(study_path, 'T1DEXI')
        self.drop_mdi = drop_mdi
    
    
    def _load_data(self, subset: bool = False):
        dx = load_dx(os.path.join(self.study_path,'DX.xpt'))
        facm = load_facm(os.path.join(self.study_path,'FACM.xpt'),subset)
        lb = load_lb(os.path.join(self.study_path,'LB.xpt'),subset)
        
        #only keep patients that have data in all three datasets
        facm_patients = facm.USUBJID.unique()
        dx_patients = dx.USUBJID.unique()
        lb_patients = lb.USUBJID.unique()
        shared_patients = set(facm_patients) & set(dx_patients) & set(lb_patients)
        
        facm = facm[facm['USUBJID'].isin(shared_patients)]
        dx = dx[dx['USUBJID'].isin(shared_patients)]
        lb = lb[lb['USUBJID'].isin(shared_patients)]
        
        #drop all mdi patients (we have reasons to believe the recordings contain a lot of duplicates)
        if self.drop_mdi:
            mdi_patients = dx.loc[dx.DXTRT=='MULTIPLE DAILY INJECTIONS'].USUBJID.unique()
            facm = facm.loc[~facm.USUBJID.isin(mdi_patients)]
            lb = lb.loc[~lb.USUBJID.isin(mdi_patients)]

        
        # merge device data (DXTRT) to facm (we need this later to distinguish between pump and mdi patients)
        facm = pd.merge(facm, dx.loc[~dx.DXTRT.isin(['INSULIN PUMP','CLOSED LOOP INSULIN PUMP'])], on='USUBJID',how='left')
        facm = facm.astype({'USUBJID': 'str'})

        self.facm = facm
        self.dx = dx
        self.lb = lb
        self.data_loaded = True

    def _extract_bolus_event_history(self):
        bolus_rows = self.facm.loc[self.facm.FATEST=='BOLUS INSULIN'].copy()

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
        bolus_rows = pd.concat([normal,extended],ignore_index=True)
    
        # Reduce, Rename
        bolus_rows = bolus_rows.rename(columns={'USUBJID': self.COL_NAME_PATIENT_ID, 
                                                'FADTC': self.COL_NAME_DATETIME,
                                                'FADUR': self.COL_NAME_BOLUS_DELIVERY_DURATION})
        return bolus_rows

    def _extract_basal_event_history(self):
        basal_rows = self.facm.loc[self.facm.FATEST.isin(['BASAL INSULIN','BASAL FLOW RATE'])].copy()
        
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
        #print(f'Dropping {basal_rows.FAORRES.isna().sum()} rows with NaN basal rates')
        basal_rows.loc[:,'FAORRES'] = basal_rows.FAORRES.fillna(0)
        
        ## correct for overlaps
        def correct_overlap(df):
            fadur = df.FADUR
            fadur[df.overlaps] = df.FADTC.diff().shift(-1)[df.overlaps]
            return fadur
        basal_rows['overlaps'] = basal_rows.groupby('USUBJID').apply(overlaps, include_groups=False).droplevel(0)
        basal_rows['FADUR'] = basal_rows.groupby('USUBJID', group_keys=False).apply(correct_overlap)
        basal_rows.drop(columns='overlaps', inplace=True)
        
        #TODO: Decide how to treat extremely large delivery durations (happening often at the very end)

        # Reduce, Rename
        basal_rows = basal_rows[['USUBJID','FADTC','FAORRES']]
        basal_rows = basal_rows.rename(columns={'USUBJID': self.COL_NAME_PATIENT_ID, 
                                                'FADTC': self.COL_NAME_DATETIME,
                                                'FAORRES': self.COL_NAME_BASAL_RATE})
        return basal_rows

    def _extract_cgm_history(self):
        lb = self.lb.drop_duplicates(subset=['USUBJID','LBDTC'],keep='first')
        return lb.rename(columns={
            'USUBJID': self.COL_NAME_PATIENT_ID,
            'LBDTC': self.COL_NAME_DATETIME,
            'LBORRES': self.COL_NAME_CGM
        })
        
class T1DEXIP(T1DEXI):
    def __init__(self, study_path, drop_mdi=False):
        super().__init__(study_path)
        self.study_name = 'T1DEXIP'
        self.drop_mdi = drop_mdi
    
    def _extract_cgm_history(self):
        glucose = super()._extract_cgm_history()
        #there is one row with values > 401, we remove it
        return glucose.loc[glucose[self.COL_NAME_CGM] <= 401]

# Example usage
if __name__ == "__main__":
    logger = Logger.get_logger(__file__)
    logger.info(os.getcwd())
    study = T1DEXI(study_path=os.path.join(os.getcwd(),'data', 'raw', 'T1DEXI'))
    out_path = os.path.join(os.getcwd(),'data', 'out', 'T1DEXI')
    study.load_data()
    study.extract_basal_event_history()
    study.extract_bolus_event_history()
    study.extract_cgm_history()
    study.save_basal_event_history_to_file(out_path)