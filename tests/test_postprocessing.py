# import rootpath
# import os
# cwd = os.getcwd()
# rootpath.append(cwd)

import pytest
import pandas as pd

from src.postprocessing import cgm_transform, bolus_transform, basal_transform


@pytest.fixture
def cleaned_basal():
    return pd.DataFrame({
        'patient_id': ['1', '1', '2', '2', '3', '3', '3','3'],
        'datetime': pd.to_datetime(['01/01/2023 8:00:00 AM', '01/02/2023 12:30:00 PM', 
                                    '01/01/2023 9:00:00 AM', '01/03/2023 4:00:00 PM',
                                    '01/01/2023 10:13:33 AM', '01/01/2023 2:13:22 PM', '01/02/2023 6:02:30 PM', '01/02/2023 8:03:00 PM']),
        'basal_rate': [1.2, 2.4, 
                       0.75, 1.5, 
                       0.12, 4.2, 0.75, 0.24]
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
    transformed_cgm_data = cleaned_cgm.groupby('patient_id').apply(cgm_transform, include_groups=False).reset_index(level=0)
    #check if start and end date are correct for each patient
    for i in transformed_cgm_data['patient_id'].unique():
        patient_data = transformed_cgm_data[transformed_cgm_data['patient_id'] == i]
        assert patient_data['datetime'].iloc[0] == pd.to_datetime('01/01/2023 00:00:00 AM')
        assert patient_data['datetime'].iloc[-1] == pd.to_datetime('01/03/2023 00:00:00 AM')

    #check if timestamps were rounded correctly
    cgm_not_null = transformed_cgm_data.dropna()
    expected_rounded = pd.to_datetime(['01/01/2023 10:10:00 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:00:00 AM',
                                       '01/01/2023 10:05:00 AM', '01/01/2023 11:10:00 AM', '01/02/2023 12:10:00 PM', '01/02/2023 4:10:00 PM',
                                       '01/01/2023 10:15:00 AM', '01/01/2023 2:25:00 PM', '01/02/2023 6:30:00 PM', '01/02/2023 8:10:00 PM'])
    assert cgm_not_null['datetime'].to_list() == expected_rounded.to_list()

def test_boluses_multiple_patients():
    #bolus transform should resample to correct time intervals and sum correctly
    df = pd.DataFrame({
        'patient_id': ['1', '1', '2', '2', '3', '3'],
        'datetime': pd.to_datetime(['01/01/2023 10:00:00 AM', '01/01/2023 12:00:00 PM',
                                    '01/01/2023 10:00:00 AM', '01/01/2023 12:00:00 PM',
                                    '01/01/2023 10:00:00 AM', '01/01/2023 12:00:00 PM']),
        'bolus': [2, 8, 5, 15, 10, 20],
        'delivery_duration': pd.to_timedelta(['3 hours', '30 minutes','30 minutes', '2 hours', '3 hours', '0 minutes'])})
    transformed_bolus_data = df.groupby('patient_id').apply(bolus_transform,include_groups=False).reset_index(level=0)
    
    #check if start and end date are correct for each patient
    for i in transformed_bolus_data['patient_id'].unique():
        patient_data = transformed_bolus_data[transformed_bolus_data['patient_id'] == i]
        assert patient_data['datetime'].iloc[0] == pd.to_datetime('01/01/2023 00:00:00 AM')
        assert patient_data['datetime'].iloc[-1] == pd.to_datetime('01/01/2023 11:55:00 PM')
    #check if boluses sum correctly
    result = transformed_bolus_data.groupby('patient_id')['bolus'].sum().tolist()
    assert result == pytest.approx([10, 20, 30])

def test_correct_splitting_single_dose():
    #bolus transform should resample to correct time intervals and sum correctly
    df = pd.DataFrame({
        'patient_id': ['1'],
        'datetime': pd.to_datetime(['01/01/2023 11:50:00 PM']),
        'bolus': [4],
        'delivery_duration': pd.to_timedelta(['20 minutes'])})
    
    transformed_bolus_data = df.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    non_zeros = transformed_bolus_data[transformed_bolus_data['bolus'] > 0].reset_index(drop=True)
    pd.testing.assert_frame_equal(non_zeros, pd.DataFrame({
        'patient_id': ['1','1','1','1'],
        'datetime': pd.to_datetime(['2023-01-01 23:50:00', '2023-01-01 23:55:00', '2023-01-02 00:00:00', '2023-01-02 00:05:00']),
        'bolus': [1.0, 1.0, 1.0, 1.0],}))

def test_correct_splitting_two_doses():
    #bolus transform should resample to correct time intervals and sum correctly
    df = pd.DataFrame({
        'patient_id': ['1','1'],
        'datetime': pd.to_datetime(['01/01/2023 23:50:00','01/02/2023 00:00:00',]),
        'bolus': [4,4],
        'delivery_duration': pd.to_timedelta(['20 minutes','10 minutes'])})
    
    transformed_bolus_data = df.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    non_zeros = transformed_bolus_data[transformed_bolus_data['bolus'] > 0].reset_index(drop=True)
    pd.testing.assert_frame_equal(non_zeros, pd.DataFrame({
        'patient_id': ['1','1','1','1'],
        'datetime': pd.to_datetime(['01/01/2023 23:50:00','01/01/2023 23:55:00','01/02/2023 00:00:00','01/02/2023 00:05:00']),
        'bolus': [1.0, 1.0, 3.0, 3.0],}))

def test_single_extended_bolus():
    #single extended bolus that overspans midnight should split into two days and sum correctly
    data = pd.DataFrame({
        'patient_id': ['1'],
        'datetime': pd.to_datetime(['01/02/2023 22:00:00']),
        'bolus': [10.0],
        'delivery_duration': pd.to_timedelta(['4 hours']),
    })
    transformed_bolus_data = data.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    transformed_bolus_data['date'] = transformed_bolus_data['datetime'].dt.date
    daily_bolus = transformed_bolus_data.groupby('date').bolus.apply('sum').reset_index().astype({'date': 'datetime64[ns]'})

    expected_bolus_sum = transformed_bolus_data['bolus'].sum()
    assert expected_bolus_sum == pytest.approx(10), "The sum of bolus values is not close to 10."
    pd.testing.assert_frame_equal(daily_bolus, pd.DataFrame({'date': [pd.to_datetime('01/02/2023'), pd.to_datetime('01/03/2023'),], 
                                                             'bolus': [5.0, 5.0]}))
    
    
def test_overlapping_boluses():
    #two overlapping extended boluses, spanning midnight should split into two days and sum correctly
    data = pd.DataFrame({
        'patient_id': ['1','1'],
        'datetime': pd.to_datetime(['01/02/2023 22:00:00', '01/03/2023 00:00:00']),
        'bolus': [10.0,10.0],
        'delivery_duration': pd.to_timedelta(['4 hours', '4 hours']),
    })
    transformed_bolus_data = data.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    assert transformed_bolus_data['bolus'].sum() == pytest.approx(20), "The sum of bolus values is not close to 10."

    transformed_bolus_data['date'] = transformed_bolus_data['datetime'].dt.date
    daily_bolus = transformed_bolus_data.groupby('date').bolus.apply('sum').reset_index().astype({'date': 'datetime64[ns]'})
    pd.testing.assert_frame_equal(daily_bolus, pd.DataFrame({'date': [pd.to_datetime('01/02/2023'), pd.to_datetime('01/03/2023'),], 
                                                             'bolus': [5.0, 15.0]}))
    
def test_overlapping_with_immediate_bolus():
    #extended bolus that overlaps immediate bolus should sum correctly
    data = pd.DataFrame({
        'patient_id': ['1','1'],
        'datetime': pd.to_datetime(['01/02/2023 10:00:00', '01/03/2023 12:00:00']),
        'bolus': [10.0, 12.0],
        'delivery_duration': pd.to_timedelta(['4 hours', '0 hours']),
    })
    transformed_bolus_data = data.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    assert transformed_bolus_data['bolus'].sum() == pytest.approx(22), "The sum of bolus values is not close to 10."

def test_bolus_transform_single_immediate():
    #single immediate bolus should be unchanged
    data = pd.DataFrame({
        'patient_id': ['1'],
        'datetime': pd.to_datetime(['01/02/2023 10:00:00']),
        'bolus': [12.0],
        'delivery_duration': pd.to_timedelta(['0 hours']),
    })
    transformed_bolus_data = data.groupby('patient_id').apply(bolus_transform, include_groups=False).reset_index(level=0)
    assert transformed_bolus_data['bolus'].sum() == pytest.approx(12), "The sum of bolus values is not close to 10."
    
    pd.testing.assert_frame_equal(transformed_bolus_data.loc[transformed_bolus_data.bolus>0].reset_index(drop=True), pd.DataFrame({
        'patient_id': ['1'],
        'datetime': pd.to_datetime(['01/02/2023 10:00:00']),
        'bolus': [12.0]}))
    
def test_basal_transform(cleaned_basal):
    transformed_basal_data = cleaned_basal.groupby('patient_id').apply(basal_transform, include_groups=False).reset_index(level=0)
    transformed_basal_data.to_csv('basal.csv')
    print(transformed_basal_data)
    #check if basals sum correctly
    assert transformed_basal_data['basal_delivery'].sum().round(1) == 190.5
    
if __name__ == '__main__':
    pytest.main([__file__])
  