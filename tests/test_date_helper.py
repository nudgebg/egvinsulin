# File: test_date_helper.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pytest
import pandas as pd
from datetime import timedelta
from src.date_helper import parse_flair_dates, convert_duration_to_timedelta
import numpy as np
def test_parse_flair_dates():
    dates = pd.Series(['10/02/2021', '10/02/2021 07:30:00 PM', '10/03/2021'])
    
    # Expected results
    expected_dates = pd.Series([
        pd.Timestamp('2021-10-02 00:00:00'),
        pd.Timestamp('2021-10-02 19:30:00'),
        pd.Timestamp('2021-10-03 00:00:00')
    ])
    
    parsed_dates = parse_flair_dates(dates)
    pd.testing.assert_series_equal(parsed_dates, expected_dates, 
                                   obj="The parsed dates are not as expected.")

def test_convert_duration_to_timedelta():
    # Test data
    duration_str = ["2:30:45", "0:0:0", "0:01:0", "0:0:1"]
    
    # Expected result
    expected_timedelta = [timedelta(hours=2, minutes=30, seconds=45),
                          timedelta(hours=0, minutes=0, seconds=0),
                          timedelta(hours=0, minutes=1, seconds=0),
                          timedelta(hours=0, minutes=0, seconds=1)]
    
    # Call the function
    calculated_timedelta = [convert_duration_to_timedelta(s) for s in duration_str]
    
    # Assert the result
    assert np.array_equal(calculated_timedelta, expected_timedelta) , "The calculated are not as expected."
    
if __name__ == "__main__":
    pytest.main()