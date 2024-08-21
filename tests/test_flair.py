import pytest
import pandas as pd
import shutil
import os

if __name__ == "__main__":
    import sys
    # Add the parent directory to the path
    file_dir = os.path.dirname(os.path.realpath(__file__))
    parent_dir = os.path.join(file_dir, '..')
    sys.path.append(parent_dir)

from studies.flair import Flair  # Assuming Flair class is in flair.py
from src import tdd

def store_data_to_files(base_dir, pump_data, cgm_data):
    data_tables_dir = os.path.join(base_dir, "Data Tables")
    os.makedirs(data_tables_dir, exist_ok=True)

    # Store pump data to file
    pump_file = os.path.join(data_tables_dir, "FLAIRDevicePump.txt")
    pump_data.to_csv(pump_file, sep='|', index=False)

    # Store CGM data to file
    cgm_file = os.path.join(data_tables_dir, "FLAIRDeviceCGM.txt")
    cgm_data.to_csv(cgm_file, sep='|', index=False)

@pytest.fixture
def sample_data_dir_basal_simple(tmpdir):
    # Create sample basal rate data for two days, alternating between 0.5 and 1 unit every 4 hours
    times = pd.date_range(start='2023-01-01 00:00:00', end='2023-01-02 23:59:59', freq='4h')
    times = times.strftime('%m/%d/%Y %I:%M:%S %p')

    basal_rates_patient1 = [0.5 if i % 2 == 0 else 1.0 for i in range(len(times))]
    basal_rates_patient2 = [1.0 if i % 2 == 0 else 2.0 for i in range(len(times))]
     
    pump_data = pd.DataFrame({
        'PtID': [1] * len(times) + [2] * len(times),
        'DataDtTm': list(times) + list(times),
        'BasalRt': basal_rates_patient1 + basal_rates_patient2,
    })

    for col in ['TempBasalAmt', 'TempBasalType', 'TempBasalDur', 'BolusDeliv', 'ExtendBolusDuration', 'Suspend', 'AutoModeStatus','TDD']:
        pump_data[col] = None

    # Create sample CGM data with constant values of 100 every 5 minutes
    cgm_times = pd.date_range(start='2023-01-01 00:00:00', end='2023-01-02 23:59:59', freq='5min')
    cgm_times = list(cgm_times.strftime('%m/%d/%Y %I:%M:%S %p'))
    cgm_values = [100] * len(cgm_times)
    cgm_data = pd.DataFrame({
        'PtID': [1] * len(cgm_times) + [2] * len(cgm_times),
        'DataDtTm': cgm_times + cgm_times,
        'CGM': cgm_values + cgm_values
    })
    cgm_data['DataDtTm_adjusted'] = None

    #os.mkdir(tmpdir)
    #temp_folder = tmpdir.mkdir("temp_folder")
    store_data_to_files(tmpdir, pump_data, cgm_data)

    return tmpdir

def test_load_data_basal_only(sample_data_dir_basal_simple):
    flair = Flair(study_name="Test Study", study_path=str(sample_data_dir_basal_simple))
    flair.load_data()

    basal = flair.extract_basal_event_history()
    tdd_basal = basal.groupby('patient_id').apply(tdd.calculate_daily_basal_dose, include_groups=False).reset_index().astype({'date': 'datetime64[ns]'})

    expected_basal = pd.DataFrame({
        'patient_id': [1, 1, 2, 2],
        'date': pd.to_datetime(['2023-01-01', '2023-01-02','2023-01-01', '2023-01-02']),
        'basal': [18.0, 18.0, 36, 36]
    }).astype({'patient_id': str,'date': 'datetime64[ns]'})

    pd.testing.assert_frame_equal(tdd_basal, expected_basal)
    print("Assertion passed: tdd_basal and expected_basal are equal")

if __name__ == "__main__":
    # Create a temporary directory using pathlib for debugging purposes
    temp_folder = os.path.join(os.getcwd(), 'temp_folder')
    os.makedirs(temp_folder, exist_ok=True)

    sample_data_dir_basal_simple(temp_folder)
    test_load_data_basal_only(temp_folder)
    
    shutil.rmtree(temp_folder)