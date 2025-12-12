# File: test_find_periods.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import numpy as np
from babelbetes.src.find_periods import find_periods, Period

def test_find_periods():
    df = pd.DataFrame({
        'AutoModeStatus': ['off', 'on', 'on', 'off', 'off', 'off', 'off', 'on', 'on', 'off'],
        'Time': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    })
    df.index = np.arange(len(df)) + 1000

    def start_trigger_fun(value):
        return value == 'on'

    def stop_trigger_fun(value):
        return value == 'off'

    periods = find_periods(df, 'AutoModeStatus', 'Time', start_trigger_fun, stop_trigger_fun)

    expected = [
        Period(index_start=1001, index_end=1003, time_start=1.0, time_end=3.0),
        Period(index_start=1007, index_end=1009, time_start=7.0, time_end=9.0)
    ]

    assert periods == expected

if __name__ == '__main__':
    pytest.main()