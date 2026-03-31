# File: example_studydataset.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
#%%
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from babelbetes.studies.studydataset import StudyDataset

# Define a new study class that inherits from StudyDataset
class SampleStudy(StudyDataset):
    def _load_data(self, subset=False):
        self.df = pd.read_csv(self.study_path)
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

    def _extract_age_data(self):
        age_data = self.df[['patient_id', 'age']]
        return age_data.dropna().drop_duplicates()



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
    'cgm': np.nan,
    'age': 45  # Patient age at study enrollment
})
basal_df = pd.DataFrame({
    'patient_id': 'patient_1',
    'datetime': basal_date_range,
    'bolus': np.nan,
    'delivery_duration': np.nan,
    'basal_rate': np.random.uniform(0, 2, len(basal_date_range)),
    'cgm': np.nan,
    'age': 45  # Patient age at study enrollment
})
cgm_df = pd.DataFrame({
    'patient_id': 'patient_1',
    'datetime': cgm_date_range,
    'bolus': np.nan,
    'delivery_duration': np.nan,
    'basal_rate': np.nan,
    'cgm': np.random.uniform(70, 180, len(cgm_date_range)),
    'age': 45  # Patient age at study enrollment
})

# Concatenate and save the file
df = pd.concat([bolus_df, basal_df, cgm_df]).sort_values('datetime')
df.to_csv('sample_dataset.csv', index=False)
print(df.head())


#use the class to load the data
print('--> Testing SampleStudy')
study = SampleStudy('sample_dataset.csv')
bolus_history = study.bolus
basal_history = study.basal
cgm_history = study.cgm
age_data = study.age
print(cgm_history.head())
print(basal_history.head())
print(bolus_history.head())
print(age_data.head())


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

    def _extract_age_data(self):
        age_data = self.df[['patient_id', 'age']].copy()
        #convert the age column to a string to cause validation error
        age_data['age'] = age_data['age'].astype(str)
        return age_data.dropna().drop_duplicates()

#use the class to load the data
print('\n\n--> Testing SampleStudy2 (this includes wrong output formats)')
study2 = SampleStudy2('sample_dataset.csv')
try:
    study2.cgm
except Exception as e:
    print(f'Error in cgm: {e}')
try:
    study2.basal
except Exception as e:
    print(f'Error in basal: {e}')
try:
    study2.bolus
except Exception as e:
    print(f'Error in bolus: {e}')
try:
    study2.age
except Exception as e:
    print(f'Error in age: {e}')
