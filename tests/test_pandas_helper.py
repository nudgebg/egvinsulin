# File: test_pandas_helper.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import numpy as np
import pytest
from src import pandas_helper

def test_get_duplicated_max_indexes():
    # Test data with duplicates
    test = pd.DataFrame({
        'PtID': [1, 1, 1, 2, 2, 2, 3, 3, 3, 1],
        'DataDtTm': [1, 2, 3, 1, 2, 2, 1, 1, 1, 2],
        'CGMValue': [1, 2, 3, 1, 2, 3, 4, 2, 3, 3]
    })
    
    # Expected results
    expected_dup_indexes = np.array([1, 4, 5, 6, 7, 8, 9])
    expected_max_indexes = np.array([9, 5, 6])
    expected_drop_indexes = np.array([1, 4, 7, 8])
    
    # Get actual results from the function
    dup_indexes, max_indexes, drop_indexes = pandas_helper.get_duplicated_max_indexes(test, ['PtID', 'DataDtTm'], 'CGMValue')
    
    # Assert the results
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


def test_drop_repetitive_values():
    # Create a sample DataFrame with unsorted datetime and repetitive values
    data = {
        'datetime': ['2025-04-17 06:00:00', '2025-04-17 07:00:00','2025-04-17 08:00:00', #only last one should be dropped (first ones are interrupted by "4" values)
                     '2025-04-17 10:00:00','2025-04-17 11:00:00','2025-04-17 12:00:00',#all different values, keep
                     '2025-04-18 10:00:00','2025-04-18 11:00:00','2025-04-18 12:00:00',#all equal, drop last two
                     '2025-04-19 10:00:00','2025-04-19 10:00:00',#duplicate should also be dropped
                     '2025-04-17 06:30:00'],# prevents first entry from being dropped
        'value': [1, 1, 1,  10, 20, 30,  1, 1, 1,   3, 3,  4]
    }
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['datetime'])  # Convert datetime column to pandas datetime
    result = pandas_helper.drop_repetitive_values(df, 'datetime', 'value')
    
    # Expected DataFrame after dropping repetitive values
    expected_df = df.loc[[0,1,3,4,5,6,9,11]]

    # Assert that the result matches the expected DataFrame
    pd.testing.assert_frame_equal(result.sort_index(), expected_df.sort_index())

def test_drop_repetitive_values_with_max_gap():
    """
    Test drop_repetitive_values with max_gap. Ensure repetitive values with a gap > max_gap are not removed.
    """
    # Create a sample DataFrame with unsorted datetime and repetitive values
    data = {
        'datetime': [
            '2025-04-17 10:00:00', '2025-04-17 23:00:00', #keep
            '2025-04-18 10:00:00', '2025-04-18 12:00:00', #remove
        ],
        'value': [1, 1, 2,2]
    }
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['datetime'])  # Convert datetime column to pandas datetime
    result = pandas_helper.drop_repetitive_values(df.sample(frac=1), 'datetime', 'value', max_gap=pd.Timedelta(hours=12))

    # Expected DataFrame after dropping repetitive values
    
    expected_df = df.loc[[0,1,2]]
    # Assert that the result matches the expected DataFrame
    pd.testing.assert_frame_equal(result.sort_index(), expected_df.sort_index())