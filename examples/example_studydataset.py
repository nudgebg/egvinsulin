#%%
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from studies.studydataset import StudyDataset

# Define a new study class that inherits from StudyDataset
class SampleStudy(StudyDataset):
    def load_data(self):
        self.df = pd.read_csv(self.filepath)
        self.df['datetime'] = pd.to_datetime(self.df['datetime'])
        self.df['delivery_duration'] = pd.to_timedelta(self.df['delivery_duration'])

    def _extract_bolus_event_history(self):
        bolus_history = self.df[['patient_id', 'datetime', 'bolus', 'delivery_duration']]
        return bolus_history.dropna()

    def _extract_basal_event_history(self):
        basal_history = self.df[['patient_id', 'datetime', 'basal_rate']]
        return basal_history.dropna()

    def _extract_cgm_history(self):
        cgm_history = self.df[['patient_id', 'datetime', 'cgm']]
        return cgm_history.dropna()



# Create separate date ranges for each type of event
date_range = pd.date_range(start='1/1/2022', end='1/10/2022', freq='H')
bolus_date_range = pd.date_range(start='1/1/2022', periods=len(date_range)//3, freq='3H')
basal_date_range = pd.date_range(start='1/1/2022 01:00:00', periods=len(date_range)//3, freq='3H')
cgm_date_range = pd.date_range(start='1/1/2022 02:00:00', periods=len(date_range)//3, freq='3H')

# Create separate DataFrames for each type of event
bolus_df = pd.DataFrame({
    'patient_id': 'patient_1',
    'datetime': bolus_date_range,
    'bolus': np.random.uniform(0, 10, len(bolus_date_range)),
    'delivery_duration': pd.to_timedelta(np.random.randint(0, 60, len(bolus_date_range)), unit='m'),
    'basal_rate': np.nan,
    'cgm': np.nan
})
basal_df = pd.DataFrame({
    'patient_id': 'patient_1',
    'datetime': basal_date_range,
    'bolus': np.nan,
    'delivery_duration': np.nan,
    'basal_rate': np.random.uniform(0, 2, len(basal_date_range)),
    'cgm': np.nan
})
cgm_df = pd.DataFrame({
    'patient_id': 'patient_1',
    'datetime': cgm_date_range,
    'bolus': np.nan,
    'delivery_duration': np.nan,
    'basal_rate': np.nan,
    'cgm': np.random.uniform(70, 180, len(cgm_date_range))
})

# Concatenate and save the file
df = pd.concat([bolus_df, basal_df, cgm_df]).sort_values('datetime')
df.to_csv('sample_dataset.csv', index=False)
print(df.head())


#use the class to load the data
print('--> Testing SampleStudy')
study = SampleStudy('sample_dataset.csv')
study.load_data()
bolus_history = study.extract_bolus_event_history()
basal_history = study.extract_basal_event_history()
cgm_history = study.extract_cgm_history()
print(cgm_history.head())
print(basal_history.head())
print(bolus_history.head())


#derive from SampleStudy and override the extract_bolus_event_history method to return the wrong columns
class SampleStudy2(SampleStudy):
    def _extract_bolus_event_history(self):
        return self.df[['patient_id', 'datetime']] # missing 'bolus' and 'delivery_duration' columns

    def _extract_basal_event_history(self):
        basal_history = self.df[['patient_id', 'datetime', 'basal_rate']]
        #change the column names to something else
        basal_history.columns = ['patient_id', 'datetime', 'rate']
        return basal_history.dropna()

    def _extract_cgm_history(self):
        cgm_history = self.df[['patient_id', 'datetime', 'cgm']].copy()
        #convert the datetime column to a string
        cgm_history['datetime'] = cgm_history['datetime'].astype(str)
        return cgm_history.dropna()

#use the class to load the data
print('\n\n--> Testing SampleStudy2 (this includes wrong output formats)')
study2 = SampleStudy2('sample_dataset.csv')
study2.load_data()
try:
    study2.extract_cgm_history()
except ValueError as e:
    print(f'Error in extract_cgm_history: {e}')
try:
    study2.extract_basal_event_history()
except ValueError as e:
    print(f'Error in extract_basal_event_history: {e}')
try:
    study2.extract_bolus_event_history()
except ValueError as e:
    print(f'Error in extract_bolus_event_history: {e}')
