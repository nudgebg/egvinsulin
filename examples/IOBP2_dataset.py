#%%
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import rootpath
rootpath.append('/Users/rachelbrandt/egvinsulin_1')
from studies.studydataset import StudyDataset

class IOBP2StudyData(StudyDataset):
    
    def load_data(self):
        self.df = pd.read_csv(self.filepath, sep="|", low_memory=False,
                           usecols=['PtID', 'DeviceDtTm', 'CGMVal', 'BGTarget', 'InsDelivPrev', 'BasalDelivPrev',
                                    'BolusDelivPrev'])
        """ there are date time strings that do not contain a time and only contain a date. For this reason the datetime strings
            are separated by length and then handled separately. The datetime strings without a time are assumed to be midnight
            of the date.
        """
        b_only_date = (self.df['DeviceDtTm'].str.len() <= 10)
        self.df.loc[b_only_date, 'datetime'] = pd.to_datetime(self.df.loc[b_only_date, 'DeviceDtTm'], format='%m/%d/%Y')
        self.df.loc[~b_only_date, 'datetime'] = pd.to_datetime(self.df.loc[~b_only_date, 'DeviceDtTm'], format='%m/%d/%Y %I:%M:%S %p')
        """ There are no extended bolus capabilities on the iLet. For this reason, all durations of inuslin delivery
        are set to 5 minutes
        """
        self.df['delivery_duration'] = pd.to_timedelta('5 minutes')
        self.df['patient_id'] = self.df['PtID'].astype(str)
        self.df['cgm'] = self.df['CGMVal'].astype(float)
        #missing cgm values are marked by a -1 regaurdless of the reason they are missing.
        self.df['cgm'] = self.df['cgm'].replace(-1,np.nan)
        """The insulin delivery is reported as the pervious amount delivered by the device. All deliveries are shifted
        back by one time step to align with when they were 'anounced' by the algorithm
        """
        self.df['bolus'] = self.df['BolusDelivPrev'].diff(-1)
        self.df['bolus'] = self.df['bolus'].fillna(0)
        """basal delivery is reported as a 5 minute delivery. These reported values were converted from a 5 minute delivery
        to a hourly basal rate"""
        self.df['basal_rate'] = self.df['BasalDelivPrev'].diff(-1) * 12
        self.df['basal_rate'] = self.df['basal_rate'].fillna(0)

    def _extract_bolus_event_history(self):
        bolus_history = self.df[['patient_id', 'datetime', 'bolus', 'delivery_duration']]
        return bolus_history.dropna()

    def _extract_basal_event_history(self):
        basal_history = self.df[['patient_id', 'datetime', 'basal_rate']]
        return basal_history.dropna()

    def _extract_cgm_history(self):
        cgm_history = self.df[['patient_id', 'datetime', 'cgm']]
        return cgm_history.dropna()

def main():
    study = IOBP2StudyData('/Users/rachelbrandt/egvinsulin_1/studies/IOBP2 RCT Public Dataset/Data Tables/IOBP2DeviceiLet.txt')
    study.load_data()
    bolus_history = study.extract_bolus_event_history()
    basal_history = study.extract_basal_event_history()
    cgm_history = study.extract_cgm_history()
    print(cgm_history.head())
    print(basal_history.head())
    print(bolus_history.head())

if 'main' == "main":
    main()

