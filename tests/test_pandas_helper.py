# File: test_pandas_helper.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import numpy as np
import pytest
from babelbetes.src import pandas_helper

def test_get_duplicated_max_indexes():
    test = pd.DataFrame({
        'PtID': [1, 1, 1, 2, 2, 2, 3, 3, 3, 1],
        'DataDtTm': [1, 2, 3, 1, 2, 2, 1, 1, 1, 2],
        'CGMValue': [1, 2, 3, 1, 2, 3, 4, 2, 3, 3]
    })
    expected_dup_indexes = np.array([1, 4, 5, 6, 7, 8, 9])
    expected_max_indexes = np.array([9, 5, 6])
    expected_drop_indexes = np.array([1, 4, 7, 8])
    dup_indexes, max_indexes, drop_indexes = pandas_helper.get_duplicated_max_indexes(test, ['PtID', 'DataDtTm'], 'CGMValue')
    np.testing.assert_array_equal(dup_indexes, expected_dup_indexes)
    np.testing.assert_array_equal(max_indexes, expected_max_indexes)
    np.testing.assert_array_equal(drop_indexes, expected_drop_indexes)


def test_split_groups():
    df = pd.DataFrame({'x': [0, 1, 2, 3, 10, 11, 12, 13, 50, 51, 70, 71]})
    actual_groups = pandas_helper.split_groups(df['x'], 5) 
    pd.testing.assert_series_equal(actual_groups, pd.Series([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 3, 3], name='x'))


def test_split_sequences():
    df = pd.DataFrame({'label': ['A', 'A', 'B', 'B', 'B', 'A', 'A', 'C', 'C', 'A']})
    actual_sequences = pandas_helper.split_sequences(df, 'label')
    pd.testing.assert_series_equal(actual_sequences, pd.Series([1, 1, 2, 2, 2, 3, 3, 4, 4, 5], name='label'))
    
def test_repetitive():
    data = {
            'datetime': ['2025-04-17 06:00:00', '2025-04-17 07:00:00','2025-04-17 08:00:00', #only last one should be dropped (first ones are interrupted by "4" value that interrupts 1 streak)
                        '2025-04-17 10:00:00','2025-04-17 11:00:00','2025-04-17 12:00:00',#all different values, keep
                        '2025-04-18 10:00:00','2025-04-18 11:00:00','2025-04-18 12:00:00',#all equal, drop last two
                        '2025-04-19 10:00:00','2025-04-19 10:00:00','2025-04-19 11:00:00',#duplicate should also be dropped, last one should be always kept
                        '2025-04-17 06:30:00'],# prevents first entry from being dropped
            'value': [1, 1, 1,  10, 20, 30,  1, 1, 1,   3, 3, 3,  4]
        }
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['datetime'])  # Convert datetime column to pandas datetime
    i_all_repetitives, i_keep, i_drop = pandas_helper.repetitive(df, 'datetime', 'value', None)
    np.testing.assert_array_equal(i_all_repetitives, [1,2,6,7,8,9,10,11])
    np.testing.assert_array_equal(i_keep, [0,12,1,3,4,5,6,9,11])
    np.testing.assert_array_equal(i_drop, [2,7,8,10])

def test_repetitive_max_gap():
    #test if it behaves the same as the original function
    df = pd.DataFrame({"value":[1]*10,'datetime':pd.date_range('2025-04-17', periods=10, freq='1h')})
    df = df.sample(frac=1)
    i_all_repetitives, i_keep, i_drop = pandas_helper.repetitive(df, 'datetime', 'value', pd.Timedelta(hours=10))
    
    expected_all = np.arange(0, 10)
    expected_keep = [0,9]
    expected_drop = np.setdiff1d(expected_all, expected_keep)
    
    np.testing.assert_array_equal(i_all_repetitives, expected_all)
    np.testing.assert_array_equal(i_keep, expected_keep)
    np.testing.assert_array_equal(i_drop, expected_drop)

def test_repetitive_using_max_gap_simple():
    #using max gap intermediate points should be kept
    df = pd.DataFrame({"value":[1]*10,'datetime':pd.date_range('2025-04-17', periods=10, freq='1h')})
    df = df.sample(frac=1)
    i_all_repetitives, i_keep, i_drop = pandas_helper.repetitive(df, 'datetime', 'value', pd.Timedelta(hours=4))
    
    expected_all = np.arange(0, 10)
    expected_keep = [0,4,8,9]
    expected_drop = np.setdiff1d(expected_all, expected_keep)
    
    np.testing.assert_array_equal(i_all_repetitives, expected_all)
    np.testing.assert_array_equal(i_keep, expected_keep)
    np.testing.assert_array_equal(i_drop, expected_drop)

def test_repetitive_using_max_gap_simple_shuffled():
    #using max gap intermediate points should be kept
    df = pd.DataFrame({"value":[1]*10,
                       'datetime':pd.date_range('2025-04-17', periods=10, freq='1h')})
    df_expected = df.loc[[0, 4, 8, 9]].reset_index(drop=True)

    df = df.sample(frac=1).reset_index(drop=True)
    _, i_keep, _ = pandas_helper.repetitive(df, 'datetime', 'value', pd.Timedelta(hours=4))
    
    df_kept = df.loc[i_keep].sort_values('datetime').reset_index(drop=True)

    pd.testing.assert_frame_equal(df_kept, df_expected)

def test_repetitivtest_repetitive_using_max_gap_keepall():
    start_date = '2023-01-01'
    values = (
        [0,1,0,1] * 1 + 
        [0] * 4 + 
        [0.5] * 4 + 
        [1] * 4 + 
        [np.nan] * 10 + 
        [0.5] * 20 + 
        [1]*10+
        [0.5]*1+
        [np.nan] * 10 +
        [0.5]*1
    )
    date_range = pd.date_range(start=start_date, periods=len(values), freq='1h')

    df = pd.DataFrame({
        'datetime': date_range,
        'basal_rate': values
    }).dropna()
    df = df.sample(frac=1)
    _, i_keep, i_drop = pandas_helper.repetitive(df, 'datetime', 'basal_rate', pd.Timedelta(hours=8))
    expected_keep = [0,1,2,3,4,8,12,26,34,42,46,54,56,67]
    np.testing.assert_array_equal(i_keep, expected_keep)
