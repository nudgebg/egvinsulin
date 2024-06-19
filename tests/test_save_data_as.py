import pandas as pd
import os
import pytest
from save_data_as import save_data_as

@pytest.fixture
def sample_data():
    data = pd.DataFrame({
        'PtID': ['a', 'b', 'c'],
        'datetime': pd.to_datetime(['2022-01-01', '2022-01-02', '2022-01-03']),
        'insulin': [10.0, 20.0, 30.0],
        'egv': [100.0, 200.0, 300.0]
    })
    return data

def test_save_data_as_csv(sample_data):
    save_data_as(sample_data, 'CSV', 'test')
    assert os.path.exists('test.csv')
    os.remove('test.csv')

def test_save_data_as_missing_column(sample_data):
    data = sample_data.drop(columns=['PtID'])
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', 'test')

def test_save_data_as_incorrect_type(sample_data):
    data = sample_data.copy()
    data['datetime'] = data['datetime'].astype(str)
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', 'test')

def test_save_data_as_correct_data(sample_data):
    save_data_as(sample_data, 'CSV', 'test')
    loaded_data = pd.read_csv('test.csv')
    loaded_data['datetime'] = pd.to_datetime(loaded_data['datetime'])
    loaded_data['insulin'] = loaded_data['insulin'].astype(float)
    loaded_data['egv'] = loaded_data['egv'].astype(float)
    assert sample_data.equals(loaded_data)
    os.remove('test.csv')
