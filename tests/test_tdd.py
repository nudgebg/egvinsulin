import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.tdd import calculate_daily_basal_dose, calculate_daily_bolus_dose, calculate_tdd

#calculate_tdd_basals
def test_case_single_event():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1)], 'basal_rate': [1]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [24.0]})
    calculated_tdd = calculate_daily_basal_dose(test)
    assert np.all(calculated_tdd['basal'].values == expected['basal'].values)

def test_case_single_day():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1), datetime(2019, 1, 1, 6), datetime(2019, 1, 1, 12)], 'basal_rate': [0, 1, 2]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [30.0]})
    calculated_tdd = calculate_daily_basal_dose(test)
    assert np.all(calculated_tdd['basal'].values == expected['basal'].values)

def test_case_half_day():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1, 12)], 'basal_rate': [1]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [12.0]})
    calculated_tdd = calculate_daily_basal_dose(test)
    assert np.all(calculated_tdd['basal'].values == expected['basal'].values)

def test_case_multiple_days():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1), datetime(2019, 1, 3)], 'basal_rate': [1, 2]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date(), datetime(2019, 1, 2).date(), datetime(2019, 1, 3).date()], 'basal': [24, 24, 48]})
    calculated_tdd = calculate_daily_basal_dose(test)
    assert np.all(calculated_tdd['basal'].values == expected['basal'].values)


# calculate_daily_bolus_dose
def test_calculate_daily_bolus_dose_single_entry():
    boluses = pd.DataFrame({'datetime': [datetime(2023, 1, 1, 8)], 'bolus': [5.0]})
    result = calculate_daily_bolus_dose(boluses)
    expected = pd.DataFrame({'date': [datetime(2023, 1, 1).date()], 'bolus': [5.0]}).set_index('date')
    pd.testing.assert_frame_equal(result, expected)

def test_calculate_daily_bolus_dose_multiple_entries():
    boluses = pd.DataFrame([
        {'datetime': datetime(2023, 1, 1, 8), 'bolus': 5.0},
        {'datetime': datetime(2023, 1, 1, 12), 'bolus': 10.0},
        {'datetime': datetime(2023, 1, 1, 18), 'bolus': 15.0}
    ])
    result = calculate_daily_bolus_dose(boluses)
    expected = pd.DataFrame({'date': [datetime(2023, 1, 1).date()],'bolus': [30]}).astype({'bolus': float}).set_index('date')

    print(result)
    print(expected)
    pd.testing.assert_frame_equal(result, expected)

#calculate_tdd
def test_calculate_tdd_multiple_patient_ids():
    df_basal = pd.DataFrame({
        'patient_id': [1, 1, 2, 2],
        'datetime': [datetime(2023, 1, 1, 12), datetime(2023, 1, 2, 12),datetime(2023, 1, 1, 12),datetime(2023, 1, 2, 12)],
        'basal_rate': [1,2,1,2]
    }).astype({'basal_rate': float})
    df_bolus = pd.DataFrame({
        'patient_id': [1, 1, 2, 2],
        'datetime': [datetime(2023, 1, 1, 1), datetime(2023, 1, 2, 1),datetime(2023, 1, 1, 1),datetime(2023, 1, 2, 1)],
        'bolus': [5, 10, 5, 10]
    }).astype({'bolus': float})
    result = calculate_tdd(df_bolus, df_basal)
    
    expected = pd.DataFrame({
        'patient_id': [1, 1, 2 ,2],
        'date': [datetime(2023, 1, 1).date(), datetime(2023, 1, 2).date(),datetime(2023, 1, 1).date(),datetime(2023, 1, 2).date()],
        'bolus': [5.0, 10.0, 5.0, 10.0],
        'basal': [12.0, 36.0,12.0,36.0],
    }).astype({'bolus': float, 'basal': float}).set_index(['patient_id', 'date'])
    pd.testing.assert_frame_equal(result[expected.columns].sort_index(), expected.sort_index())

    
if __name__ == '__main__':
    pytest.main()