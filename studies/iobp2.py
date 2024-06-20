import pandas as pd
import numpy as np
from datetime import timedelta
import os 
from studydataset import StudyDataset

class IOBP2StudyData(StudyDataset):

    def __init__(self, study_name: str, study_path: str):
        super().__init__(study_path, study_name)
        self.iletFilePath = os.path.join(self.study_path, 'Data Tables', 'IOBP2DeviceiLet.txt')
        if not os.path.exists(self.iletFilePath):
            raise FileNotFoundError(f"File not found: {self.iletFilePath}")
    
    def load_data(self) -> pd.DataFrame:
        
        self.df = pd.read_csv(self.iletFilePath, sep="|", low_memory=False,
               usecols=['PtID', 'DeviceDtTm', 'CGMVal', 'BGTarget', 'BasalDelivPrev',
                'BolusDelivPrev','MealBolusDelivPrev'],
               dtype={'PtID': str, 'CGMVal': float})
        
        self.df.rename(columns={'PtID': 'patient_id', 'DeviceDtTm': 'datetime', 'CGMVal': 'cgm', 
                        'BGTarget': 'bg_target', 'BasalDelivPrev': 'basal_rate', 
                        'BolusDelivPrev': 'bolus', 'MealBolusDelivPrev': 'meal_bolus'}, inplace=True)
        
        #date time strings wiithout time component are assumed to be midnight
        b_only_date = (self.df['datetime'].str.len() <= 10)
        self.df.loc[b_only_date, 'datetime'] = pd.to_datetime(self.df.loc[b_only_date, 'datetime'], format='%m/%d/%Y')
        self.df.loc[~b_only_date, 'datetime'] = pd.to_datetime(self.df.loc[~b_only_date, 'datetime'], format='%m/%d/%Y %I:%M:%S %p')
        
        #There are no extended bolus capabilities on the iLet, therefore all durations of inuslin delivery are set to 5 minutes
        self.df['delivery_duration'] = pd.to_timedelta('5 minutes')
        
        #Bolus delivery is separated into two different columns: bolus and meal bolus. These two columns are combined to give a single bolus column
        self.df['bolus'] = self.df['bolus'] + self.df['meal_bolus']

    def _extract_bolus_event_history(self):
        bolus_history = self.df[['patient_id', 'datetime', 'bolus', 'delivery_duration']]
        
        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        bolus_history['datetime'] = bolus_history['datetime'] - timedelta(minutes=5)
        bolus_history['bolus'] = bolus_history['bolus'].fillna(0)

        return bolus_history.dropna()

    def _extract_basal_event_history(self):
        basal_history = self.df[['patient_id', 'datetime', 'basal_rate']]
        
        #insulin delivery is reported as the previous amount delivered. Therefore data is shifted to to align with algorithm announcement
        basal_history['datetime'] = basal_history['datetime'] - timedelta(minutes=5)
        
        #convert 5 minute basal deliveries to a hourly basal rate
        basal_history['basal_rate'] = basal_history.df['basal_rate'] * 12
        basal_history['basal_rate'] = basal_history.df['basal_rate'].fillna(0)
        
        return basal_history.dropna()

    def _extract_cgm_history(self):
        cgm_history = self.df[['patient_id', 'datetime', 'cgm']]
        cgm_history.columns = ['patient_id', 'datetime', 'cgm']
        
        #missing cgm values are marked by a -1 regardless of the reason they are missing.
        cgm_history['cgm'] = cgm_history['cgm'].replace(-1,np.nan, inplace=True)

        return cgm_history.dropna()



if __name__ == '__main__':
    current_dir = os.path.dirname(__file__)
    path = os.path.join(current_dir, '..', 'data/test', 'IOBP2 RCT Public Dataset')
    
    study = IOBP2StudyData(study_name='IOBP2', study_path=path)
    study.load_data()
    bolus_history = study.extract_bolus_event_history()
    basal_history = study.extract_basal_event_history()
    cgm_history = study.extract_cgm_history()
    print(cgm_history.head())
    print(basal_history.head())
    print(bolus_history.head())
