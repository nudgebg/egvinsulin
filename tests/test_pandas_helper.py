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