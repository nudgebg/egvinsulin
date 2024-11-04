import pandas as pd
import numpy as np
from collections import namedtuple

Period = namedtuple('Period', ['index_start', 'index_end', 'time_start', 'time_end'])

def find_periods(df, value_col, time_col, start_trigger_fun, stop_trigger_fun, 
                 use_last_start_occurence=False,
                 use_last_stop_occurence=False):
    """
    Find periods in a DataFrame based on start and stop triggers.

    Args:
        df (pandas.DataFrame): The DataFrame to search for periods.
        value_col (str): The name of the column containing the trigger values.
        time_col (str): The name of the column containing the time values.
        start_trigger: The value that indicates the start of a period.
        stop_trigger: The value that indicates the end of a period.
        use_last_start_occurence (bool): If True, the last occurrence of the start trigger will be used.

    Returns:
        list: A list of namedtuples representing the periods found. Each namedtuple contains the following attributes:
            - start_index (int): The index of the start trigger in the DataFrame.
            - end_index (int): The index of the stop trigger in the DataFrame.
            - start_time: The time value of the start trigger.
            - end_time: The time value of the stop trigger.
    """
    # Define the named tuple
    #if there is nan values in either column, print a warning
    if df[value_col].isnull().sum() > 0:
        print("Warning: NaN values in the value column, rows will be dropped")
    if df[time_col].isnull().sum() > 0:
        print("Warning: NaN values in the time column, rows will be dropped")
    df = df.dropna(subset=[time_col, value_col], how='any')
    
    # Sort the DataFrame by time
    df = df.sort_values(by=time_col)
    
    # Initialize variables to track periods
    periods = []
    start_index = None
    start_time = None
    
    # Iterate through the DataFrame rows to find periods
    for index, row in df.iterrows():
        print(index)
        if start_trigger_fun(row[value_col]) and ((start_index is None) or use_last_start_occurence):
            start_index = index
            start_time = row[time_col]
        elif stop_trigger_fun(row[value_col]) and start_index is not None:
            end_index = index
            end_time = row[time_col]
            duration = (end_time - start_time).total_seconds() if isinstance(end_time, pd.Timestamp) else end_time - start_time
            new_period = Period(start_index, end_index, start_time, end_time)
            periods.append(new_period)
            start_index = None  # Reset start_index to find the next period
    
    return periods


if __name__ == "__main__":
    temp = pd.DataFrame({
        'AutoModeStatus': ['off', 'on', 'on', 'off', 'off', 'on', 'off', 'on', 'on', 'off'],
        'Time': [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    })
    temp.index = np.arange(len(temp))+1000
    print(temp)
    periods = find_periods(temp, 'AutoModeStatus', 'Time', lambda x: x=='on', lambda x: x=='off', use_last_start_occurence=True)
    expected = [Period(index_start=1001, index_end=1003, time_start=1.0, time_end=3.0),
                Period(index_start=1007, index_end=1009, time_start=7.0, time_end=9.0)]
    print("Identified Periods:")
    for period in periods:
        print(period)
    print("Expected Periods:")
    for period in expected:
        print(period)
    
    # for period, expected_period in zip(periods, expected):
    #     print(period)
    #     print(expected_period)
    #assert periods == expected