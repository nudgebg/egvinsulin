import pandas as pd
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

def test_save_data_as_csv(sample_data, tmpdir):
    temp_file = tmpdir.join('test')
    save_data_as(sample_data, 'CSV', str(temp_file))
    assert tmpdir.join('test.csv').exists()

def test_save_data_as_missing_column(sample_data, tmpdir):
    temp_file = tmpdir.join('test')
    data = sample_data.drop(columns=['PtID'])
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', str(temp_file))

def test_save_data_as_incorrect_type(sample_data, tmpdir):
    temp_file = tmpdir.join('test')
    data = sample_data.copy()
    data['datetime'] = data['datetime'].astype(str)
    with pytest.raises(ValueError):
        save_data_as(data, 'CSV', str(temp_file))

def test_save_data_as_correct_data(sample_data, tmpdir):
    temp_file = tmpdir.join('test')
    save_data_as(sample_data, 'CSV', str(temp_file))
    loaded_data = pd.read_csv(tmpdir.join('test.csv'), parse_dates=['datetime'])
    pd.testing.assert_frame_equal(sample_data, loaded_data)