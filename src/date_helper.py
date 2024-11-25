import pandas as pd
from datetime import timedelta

def parse_flair_dates(dates, format_date = '%m/%d/%Y', format_time = '%I:%M:%S %p'):
    """Parse date strings separately for those with/without time component, interpret those without as midnight (00AM)
    Args:
        dates (pd.DataFrame): datetimes (string) either in in the %m/%d/%Y or %m/%d/%Y %I:%M:%S %p format
    Returns:
        pandas series: with parsed dates
    """
    #make sure to only parse dates if the value is not null
    only_date = dates.apply(len) <=10
    dates_copy = dates.copy()
    dates_copy.loc[only_date] = pd.to_datetime(dates.loc[only_date], format=format_date)
    dates_copy.loc[~only_date] = pd.to_datetime(dates.loc[~only_date], format=f'{format_date} {format_time}')
    return dates_copy.astype('datetime64[ns]')

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