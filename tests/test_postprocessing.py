import rootpath
import os
cwd = os.getcwd()
rootpath.append(cwd)

import pytest
import pandas as pd

from src.postprocessing import cgm_transform, bolus_transform, basal_transform


@pytest.fixture
def cleaned_bolus():
    return pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        'datetime': pd.to_datetime(['01/01/2023 10:03:30 AM', '01/01/2023 1:10:00 PM', '01/01/2023 11:58:00 PM',
                                    '01/01/2023 9:58:15 AM', '01/01/2023 11:02:45 AM', '01/02/2023 12:07:00 PM', '01/02/2023 4:07:00 PM',
                                    '01/01/2023 10:10:00 AM', '01/01/2023 2:19:50 PM', '01/02/2023 6:25:00 PM', '01/02/2023 8:05:00 PM']),
        'bolus': [10.5, 15.8, 10.1, 8.6, 11.4, 9.9, 8.2, 6.5, 7.3, 8.8, 7.3],
        'delivery_duration': pd.to_timedelta(['5 minutes', '30 minutes', '115 minutes', '5 minutes', '75 minutes', '5 minutes', '15 minutes',
                                              '5 minutes', '8 minutes', '5 minutes', '6 minutes']),
    })

@pytest.fixture
def cleaned_basal():
    return pd.DataFrame({
        'patient_id': ['1', '1', '2', '2', '3', '3', '3','3'],
        'datetime': pd.to_datetime(['01/01/2023 8:00:00 AM', '01/01/2023 12:30:00 PM', 
                                    '01/01/2023 9:00:00 AM', '01/03/2023 4:00:00 PM',
                                    '01/01/2023 10:13:33 AM', '01/01/2023 2:19:22 PM', '01/02/2023 6:12:30 PM', '01/02/2023 8:07:00 PM']),
        'basal_rate': [1.3, 2, 
                       0.7, 1.5, 
                       0.1, 4, 0.75, 0.2]
    })

@pytest.fixture
def cleaned_cgm():
    return pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        'datetime': pd.to_datetime(['01/01/2023 10:08:30 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:02:00 AM',
                                    '01/01/2023 10:03:15 AM', '01/01/2023 11:07:45 AM', '01/02/2023 12:12:00 PM', '01/02/2023 4:12:00 PM',
                                    '01/01/2023 10:15:00 AM', '01/01/2023 2:24:50 PM', '01/02/2023 6:30:00 PM', '01/02/2023 8:10:00 PM']),
        'cgm': [39.0, 110.0, 105.0, 120.0, 130.0, 140.0, 105.0, 150.0, 160.0, 170.0, 401]
    })


def test_cgm_transform(cleaned_cgm):
    transformed_cgm_data = cleaned_cgm.groupby('patient_id').apply(cgm_transform).reset_index(drop=True)
    #check if start and end date are correct for each patient
    for i in transformed_cgm_data['patient_id'].unique():
        patient_data = transformed_cgm_data[transformed_cgm_data['patient_id'] == i]
        assert patient_data['datetime'].iloc[0] == pd.to_datetime('01/01/2023 00:00:00 AM')
        assert patient_data['datetime'].iloc[-1] == pd.to_datetime('01/03/2023 00:00:00 AM')

    #check if cgm values are in the range of 40-400
    assert transformed_cgm_data['cgm'].min() >= 40
    assert transformed_cgm_data['cgm'].max() <= 400

    #check if timestamps were rounded correctly
    cgm_not_null = transformed_cgm_data.dropna()
    expected_rounded = pd.to_datetime(['01/01/2023 10:10:00 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:00:00 AM',
                                       '01/01/2023 10:05:00 AM', '01/01/2023 11:10:00 AM', '01/02/2023 12:10:00 PM', '01/02/2023 4:10:00 PM',
                                       '01/01/2023 10:15:00 AM', '01/01/2023 2:25:00 PM', '01/02/2023 6:30:00 PM', '01/02/2023 8:10:00 PM'])
    assert cgm_not_null['datetime'].to_list() == expected_rounded.to_list()

def test_bolus_transform(cleaned_bolus):
    transformed_bolus_data = cleaned_bolus.groupby('patient_id').apply(bolus_transform).reset_index(drop=True)
    #check if start and end date are correct for each patient
    for i in transformed_bolus_data['patient_id'].unique():
        patient_data = transformed_bolus_data[transformed_bolus_data['patient_id'] == i]
        assert patient_data['datetime'].iloc[0] == pd.to_datetime('01/01/2023 00:00:00 AM')
        assert patient_data['datetime'].iloc[-1] == pd.to_datetime('01/03/2023 00:00:00 AM')
    #check if boluses sum correctly
    assert transformed_bolus_data['bolus'].sum().round(1) == cleaned_bolus['bolus'].sum().round(1)

def test_basal_transform(cleaned_basal):
    transformed_basal_data = cleaned_basal.groupby('patient_id').apply(basal_transform).reset_index(drop=True)
    print(transformed_basal_data)
    #check if basals sum correctly
    assert transformed_basal_data['basal_delivery'].sum().round(1) == 189.6
    

if __name__ == '__main__':
    pytest.main([__file__])
  