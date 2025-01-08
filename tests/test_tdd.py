import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.tdd import calculate_daily_basal_dose, calculate_daily_bolus_dose, calculate_tdd

#calculate_tdd_basals
def test_case_single_event():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1)], 'basal_rate': [1]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [24.0]})
    calculated = calculate_daily_basal_dose(test).reset_index()
    print(expected)
    print(calculated)
    pd.testing.assert_frame_equal(calculated, expected)

# def test_case_single_event_missing_start():
#     test = pd.DataFrame({'datetime': [datetime(2019, 1, 1,12)], 'basal_rate': [1]})
#     expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [np.nan]})
#     calculated_tdd = calculate_daily_basal_dose(test).reset_index()
#     pd.testing.assert_frame_equal(calculated_tdd, expected)

def test_case_single_day():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1), datetime(2019, 1, 1, 6), datetime(2019, 1, 1, 12)], 
                         'basal_rate': [0, 1, 2]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [30.0]})
    calculated_tdd = calculate_daily_basal_dose(test).reset_index()
    pd.testing.assert_frame_equal(calculated_tdd, expected)

#     #the gap is exactly 12 hours, should be filled
#     calculated_tdd = calculate_daily_basal_dose(test, ffill_thresh_hours=12).reset_index()
#     pd.testing.assert_frame_equal(calculated_tdd, expected)

#     #the gap can't be closed, tdd should be NaN
#     calculated_tdd = calculate_daily_basal_dose(test, ffill_thresh_hours=10).reset_index()
#     expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date()], 'basal': [np.nan]})
#     pd.testing.assert_frame_equal(calculated_tdd, expected)

# def test_one_day_filled():
#     test = pd.DataFrame({'datetime': [datetime(2019, 1, 1, 20), 
#                                       datetime(2019, 1, 2, 12), 
#                                       datetime(2019, 1, 3, 2)], 
#                         'basal_rate': [1, 2, 3]})
    
    # calculated_tdd = calculate_daily_basal_dose(test).reset_index()
    # expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date(), datetime(2019, 1, 2).date(), datetime(2019, 1, 3).date()], 
    #                          'basal': [np.nan,36.0,70.0]})
    # pd.testing.assert_frame_equal(calculated_tdd, expected)

    #with thresh set to 16 hours, the last day can't be forward filled
    # calculated_tdd = calculate_daily_basal_dose(test, ffill_thresh_hours=15).reset_index()
    # expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date(), datetime(2019, 1, 2).date(), datetime(2019, 1, 3).date()], 
    #                          'basal': [np.nan, 36.0, np.nan]})
    # pd.testing.assert_frame_equal(calculated_tdd, expected)

def test_two_days_filled():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1), datetime(2019, 1, 2)], 'basal_rate': [1, 2]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date(), datetime(2019, 1, 2).date()], 
                             'basal': [24.0, 48.0]})
    calculated_tdd = calculate_daily_basal_dose(test).reset_index()

    pd.testing.assert_frame_equal(calculated_tdd, expected)

def test_two_days_with_gap_day():
    test = pd.DataFrame({'datetime': [datetime(2019, 1, 1),datetime(2019, 1, 3)], 'basal_rate': [1, 2]})
    expected = pd.DataFrame({'date': [datetime(2019, 1, 1).date(), datetime(2019, 1, 2).date(),datetime(2019, 1, 3).date()], 
                             'basal': [24.0, np.nan, 48.0]})
    calculated_tdd = calculate_daily_basal_dose(test).reset_index()

    pd.testing.assert_frame_equal(calculated_tdd, expected)

def test_empty_data():
    test = pd.DataFrame({'datetime': [], 'basal_rate': []})
    pytest.raises(ValueError, calculate_daily_basal_dose, test)
    

def test_calculate_daily_bolus_dose_multiple_entries():
    boluses = pd.DataFrame([
        {'datetime': datetime(2023, 1, 1, 8), 'bolus': 5.0},
        {'datetime': datetime(2023, 1, 1, 12), 'bolus': 10.0},
        {'datetime': datetime(2023, 1, 1, 18), 'bolus': 15.0}
    ])
    result = calculate_daily_bolus_dose(boluses).reset_index()
    expected = pd.DataFrame({'date': [datetime(2023, 1, 1).date()],'bolus': [30]}).astype({'bolus': float})
    pd.testing.assert_frame_equal(result, expected)

#calculate_tdd
def test_calculate_tdd_multiple_patient_ids():
    df_basal = pd.DataFrame({
        'patient_id': [1, 1, 2, 2],
        'datetime': [datetime(2023, 1, 1, 0), datetime(2023, 1, 2, 0),datetime(2023, 1, 1, 0),datetime(2023, 1, 2, 0)],
        'basal_rate': [1,2,3,4]
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
        'basal': [24.0, 48.0, 72.0, 96.0],
    }).astype({'bolus': float, 'basal': float}).set_index(['patient_id', 'date'])
    pd.testing.assert_frame_equal(result[expected.columns].sort_index(), expected.sort_index())

    
if __name__ == '__main__':
    pytest.main(["-v", __file__])