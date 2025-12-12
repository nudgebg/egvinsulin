# File: iobp2.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import numpy as np
from datetime import timedelta
from babelbetes.src.pandas_helper import get_df
import os 
from babelbetes.src.date_helper import parse_flair_dates
from babelbetes.studies.studydataset import StudyDataset

class IOBP2(StudyDataset):

    def __init__(self, study_path: str):
        super().__init__(study_path, "IOBP2")
        self._iletFilePath = os.path.join(study_path, 'Data Tables', 'IOBP2DeviceiLet.txt')
        
    def _load_data(self, subset) -> pd.DataFrame:
        self._df = get_df(self._iletFilePath, usecols=['PtID', 'DeviceDtTm', 'CGMVal', 'BasalDelivPrev','BolusDelivPrev',
                                                     'MealBolusDelivPrev'], subset=subset, dtype={'PtID': str, 'CGMVal': float})
        
        self._df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'DeviceDtTm': self.COL_NAME_DATETIME, 'CGMVal': self.COL_NAME_CGM, 
                        'BasalDelivPrev': self.COL_NAME_BASAL_RATE, 'BolusDelivPrev': self.COL_NAME_BOLUS}, inplace=True)
        
        #date time strings without time component are assumed to be midnight
        self._df[self.COL_NAME_DATETIME] = self._df[self.COL_NAME_DATETIME].transform(parse_flair_dates).astype('datetime64[ns]')

        self._df = self._df.sort_values([self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME])

    def _extract_bolus_event_history(self):
        df_bolus = self._df.dropna(subset=[self.COL_NAME_BOLUS, 'MealBolusDelivPrev']).copy()
        
        #Bolus delivery is separated into two different columns: bolus and meal bolus. 
        df_bolus[self.COL_NAME_BOLUS] = df_bolus[self.COL_NAME_BOLUS] + df_bolus['MealBolusDelivPrev'] 
        
        #there are no extended boluses in ilet only standard/micro boluses
        df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION] = pd.Timedelta('0 minutes')
        #df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION] = df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION].astype('timedelta64[ns]')
        
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

if __name__ == '__main__':
    current_dir = os.path.dirname(__file__)
    path = os.path.join(current_dir, 'IOBP2 RCT Public Dataset')
    study = IOBP2(study_path=path)
    
    study.load_data()
    bolus_history = study.extract_bolus_event_history()
    cgm_history = study.extract_cgm_history()
    
