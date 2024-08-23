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
    store_data_to_files(tmpdir, pump_data, cgm_data)
    return tmpdir


@pytest.fixture
def sample_data_closed_loop(tmpdir):
    # Create sample basal rate data for two days, alternating between 0.5 and 1 unit every 4 hours
    times = pd.date_range(start='2023-01-01 00:00:00', end='2023-01-02 23:59:59', freq='4h')
    times = times.strftime('%m/%d/%Y %I:%M:%S %p')

    basal_rates_patient1 = [0.6 if i % 2 == 0 else 1.2 for i in range(len(times))]
    basal_rates_patient2 = [1.2 if i % 2 == 0 else 2.4 for i in range(len(times))]
     
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
    store_data_to_files(tmpdir, pump_data, cgm_data)
    return tmpdir



@pytest.fixture
def sample_data_closed_loop(tmpdir):
    start = pd.to_datetime('2023-01-01 00:00:00')
    end = pd.to_datetime('2023-01-02 00:00:00')
    
    # Basal Rate
    pump_data = pd.DataFrame({
        'PtID': [1,2],
        'DataDtTm': [start.strftime('%m/%d/%Y %I:%M:%S %p'), 
                     start.strftime('%m/%d/%Y %I:%M:%S %p')],
        'BasalRt': [0, 1],
    })

    # Closed loop active from noon to noon the next day
    auto_mode_start = start + pd.Timedelta(hours=6)
    auto_mode_end = start + pd.Timedelta(hours=18)
    auto_mode_data = pd.DataFrame({
        'PtID': [1, 1, 2, 2],
        'DataDtTm': [x.strftime('%m/%d/%Y %I:%M:%S %p') for x in [auto_mode_start, auto_mode_end, auto_mode_start, auto_mode_end]],
        'AutoModeStatus': [True, False, True, False]
    })
    pump_data = pd.concat([pump_data, auto_mode_data], ignore_index=True)

    # Add micro bolus deliveries
    micro_bolus_times = pd.date_range(auto_mode_start, auto_mode_end, freq='10min',inclusive='left')
    micro_bolus_times = list(micro_bolus_times.strftime('%m/%d/%Y %I:%M:%S %p'))
    micro_bolus_p1 = [0.1 for i in range(len(micro_bolus_times))]
    micro_bolus_p2 = [0.2 for i in range(len(micro_bolus_times))]
    micro_bolus_data = pd.DataFrame({
        'PtID': [1] * len(micro_bolus_times) + [2] * len(micro_bolus_times),
        'DataDtTm': list(micro_bolus_times) + list(micro_bolus_times),
        'BolusDeliv': micro_bolus_p1 + micro_bolus_p2
    })
    pump_data = pd.concat([pump_data, micro_bolus_data], ignore_index=True)

    for col in ['TempBasalAmt', 'TempBasalType', 'TempBasalDur', 'ExtendBolusDuration', 'Suspend', 'TDD']:
        pump_data[col] = None


    # Create sample CGM data with constant values of 100 every 5 minutes
    cgm_times = pd.date_range(start, end, freq='5min')
    cgm_times = list(cgm_times.strftime('%m/%d/%Y %I:%M:%S %p'))
    cgm_values = [100] * len(cgm_times)
    cgm_data = pd.DataFrame({
        'PtID': [1] * len(cgm_times) + [2] * len(cgm_times),
        'DataDtTm': cgm_times + cgm_times,
        'CGM': cgm_values + cgm_values
    })
    cgm_data['DataDtTm_adjusted'] = None

    store_data_to_files(tmpdir, pump_data, cgm_data)

    return tmpdir

def test_sample_data_closed_loop(sample_data_closed_loop):
    flair = Flair(study_name="Test Study", study_path=str(sample_data_closed_loop))
    flair.load_data()

    basal = flair.extract_basal_event_history()
    tdd_basal = basal.groupby('patient_id').apply(tdd.calculate_daily_basal_dose, include_groups=False).reset_index().astype({'date': 'datetime64[ns]'})

    expected_basal = pd.DataFrame({
        'patient_id': [1, 2],
        'date': pd.to_datetime(['2023-01-01', '2023-01-01']),
        'basal': [0.0, 6.0]
    }).astype({'patient_id': str,'date': 'datetime64[ns]'})
    print(tdd_basal)
    print(expected_basal)
    pd.testing.assert_frame_equal(tdd_basal, expected_basal)

    bolus = flair.extract_bolus_event_history()
    tdd_bolus = bolus.groupby('patient_id').apply(tdd.calculate_daily_bolus_dose, include_groups=False).reset_index().astype({'date': 'datetime64[ns]'})
    expected_bolus = pd.DataFrame({
        'patient_id': [1, 2],
        'date': pd.to_datetime(['2023-01-01', '2023-01-01']),
        'bolus': [7.2, 14.4]
    }).astype({'patient_id': str,'date': 'datetime64[ns]'})
    print(tdd_bolus)
    print(expected_bolus)
    pd.testing.assert_frame_equal(tdd_bolus, expected_bolus)
    

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

    sample_data_closed_loop(temp_folder)
    test_sample_data_closed_loop(temp_folder)
    
    shutil.rmtree(temp_folder)