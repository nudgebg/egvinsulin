# File: date_helper.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from datetime import timedelta

def get_hour_of_day(datetime_series):
        return datetime_series.dt.hour + datetime_series.dt.minute/60 + datetime_series.dt.second/3600

def parse_flair_dates(dates, format_date='%m/%d/%Y', format_time='%I:%M:%S %p'):
    """Optimized parsing of date strings with or without time components."""
    # Try parsing with the full datetime format first
    parsed_dates = pd.to_datetime(dates, format=f'{format_date} {format_time}', errors='coerce')
    
    # Fill in the remaining unparsed dates using the date-only format
    missing_dates = parsed_dates.isna()
    parsed_dates[missing_dates] = pd.to_datetime(dates[missing_dates], format=format_date, errors='coerce')
    
    return parsed_dates.astype('datetime64[ns]')

def convert_duration_to_timedelta(duration):
    """
    Parse a duration string in the format "hours:minutes:seconds" and return a timedelta object.
    Args:
        duration_str (str): The duration string to parse in the form of "hours:minutes:seconds".
    Returns:
        timedelta: A timedelta object representing the parsed duration.
    """
    hours, minutes, seconds = map(int, duration.split(':'))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)