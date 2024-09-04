import pandas as pd
import pytest
from src.save_data_as import save_data_as


@pytest.fixture
def sample_data_cgm():
    data = pd.DataFrame({
        'patient_id': ['a', 'b', 'c'],
        'datetime': pd.to_datetime(['2022-01-01', '2022-01-02', '2022-01-03']),
        'insulin': [10.0, 20.0, 30.0],
    })
    return data

@pytest.fixture
def sample_data_bolus():
    data = pd.DataFrame({
        'patient_id': ['a', 'b', 'c'],
        'datetime': pd.to_datetime(['2022-01-01', '2022-01-02', '2022-01-03']),
        'egv': [100.0, 200.0, 300.0]
    })
    return data

def test_save_data_cgm(sample_data_cgm, tmpdir):
    temp_file = tmpdir.join('test_save_data_cgm')
    save_data_as(sample_data_cgm, 'CSV', str(temp_file))
    assert tmpdir.join('test_save_data_cgm.csv').exists()

def test_save_data_as_missing_column(sample_data_cgm, tmpdir):
    temp_file = tmpdir.join('test_save_data_as_missing_column')
    data = sample_data_cgm.drop(columns=['patient_id'])
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', str(temp_file))

def test_save_data_as_incorrect_date_type(sample_data_cgm, tmpdir):
    temp_file = tmpdir.join('test_save_data_as_incorrect_date_type')
    data = sample_data_cgm.copy()
    data['datetime'] = data['datetime'].astype(str)
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', str(temp_file))
