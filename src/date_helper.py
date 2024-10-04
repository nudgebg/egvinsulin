import pandas as pd
from datetime import timedelta

def parse_flair_dates(dates):
    """Parse date strings separately for those with/without time component, interpret those without as midnight (00AM)
    Args:
        dates (pd.DataFrame): datetimes (string) either in in the %m/%d/%Y or %m/%d/%Y %I:%M:%S %p format
    Returns:
        pandas series: with parsed dates
    """
    #make sure to only parse dates if the value is not null
    only_date = dates.apply(len) <=10
    dates_copy = dates.copy()
    dates_copy.loc[only_date] = pd.to_datetime(dates.loc[only_date], format='%m/%d/%Y')
    dates_copy.loc[~only_date] = pd.to_datetime(dates.loc[~only_date], format='%m/%d/%Y %I:%M:%S %p')
    return dates_copy

def convert_duration_to_timedelta(duration):
    """
    Parse a duration string in the format "hours:minutes:seconds" and return a timedelta object.
    Args:
        duration_str (str): The duration string to parse.
    Returns:
        timedelta: A timedelta object representing the parsed duration.
    """
    hours, minutes, seconds = map(int, duration.split(':'))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)