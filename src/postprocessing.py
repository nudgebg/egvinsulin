# File: postprocessing.py
# Author Rachel Brandt, Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import time
from datetime import timedelta
import numpy as np

import pandas as pd
import numpy as np
from datetime import timedelta
from src.logger import Logger
logger = Logger.get_logger(__name__)

# Function to split the bolus into multiple deliveries
def split_bolus(datetime, bolus, duration, sampling_frequency):
    steps = max(1, np.ceil(duration / sampling_frequency))
    delivery_per_interval = bolus / steps
    times = datetime+np.arange(steps)*sampling_frequency
    deliveries = [delivery_per_interval] * len(times)
    return {'datetime': times, 'delivery': deliveries}

#functions for time alignment and transformation of basal, bolus, and cgm event data. These functions can be used for any study dataset.
def bolus_transform(df):
    """
    Transform the bolus data by aligning timestamps, handling duplicates, and extending boluses based on durations.

    Parameters:
        df (DataFrame): The input is a bolus data dataframe containing columns 'datetime', 'bolus', and 'delivery_duration'.

    Returns:
        bolus_data (DataFrame): 5 Minute resampled and time aligned at midnight bolus data with columns: datetime, delivery
    """

    sampling_frequency = '5min'
    sampling_frequency = pd.to_timedelta(sampling_frequency)

    expanded_rows = [split_bolus(row['datetime'], row['bolus'], row['delivery_duration'], sampling_frequency) for _, row in df.iterrows()]
    
    # Concatenate the lists of datetimes and deliveries
    datetimes = np.concatenate([item['datetime'] for item in expanded_rows])
    deliveries = np.concatenate([item['delivery'] for item in expanded_rows])
    expanded_events = pd.DataFrame({'datetime': datetimes, 'bolus': deliveries})
    
    # Round down to the nearest floored interval
    expanded_events['datetime'] = expanded_events['datetime'].dt.floor(sampling_frequency)
    
    # Sum up multiple entries for the same time
    expanded_events = expanded_events.groupby('datetime').sum().reset_index()
    
    # Resample to ensure all intervals are present (Start/End midnight of the first/last day)
    expanded_events = expanded_events.sort_values('datetime')
    start_time = df['datetime'].min().floor('D')  
    end_time = (df['datetime'] + df['delivery_duration']).max().ceil('D') 
    all_times = pd.date_range(start=start_time, end=end_time, freq=sampling_frequency, inclusive='left')
    resampled_deliveries = expanded_events.set_index('datetime').reindex(all_times, fill_value=0).reset_index(drop=False, names =['datetime'])
    
    return resampled_deliveries

def resample_closest(series: pd.Series, freq='5min'):
    
    #add midnight supports
    # midnight_first_day = series.index.min().normalize()
    # midnight_last_day = series.index.max().normalize() + timedelta(days=1)
    # if not midnight_first_day in series.index:
    #     series.loc[pd.Timestamp(midnight_first_day)] = np.nan
    # if not midnight_last_day in series.index:
    #     series.loc[pd.Timestamp(midnight_last_day)] = np.nan

    assert series.index.is_monotonic_increasing, "The datetime index must be sorted"

    series = series.reset_index()
    resampled = series.assign(datetime=series.datetime.dt.round(freq)).drop_duplicates(subset='datetime').set_index('datetime').resample(freq)
    return resampled

def cgm_transform(cgm_data):
    """
    Time aligns the cgm data to midnight with a 5 minute sampling rate.

    Parameters:
        cgm_data (DataFrame): The input is a cgm data dataframe containing columns 'datetime', and 'cgm'.

    Returns:
        cgm_data (DataFrame): The transformed cgm data with aligned timestamps.
    """
    series = cgm_data = cgm_data.copy().set_index('datetime')
    if not series.index.is_monotonic_increasing:
        logger.warning('The index is not sorted. Sorting the index.')
        series = series.sort_index()
    
    resampled = resample_closest(series, '5min')
    return resampled.asfreq().reset_index()

def basal_transform(basal_data):
    """
    Transform the basal data by aligning timestamps and handling duplicates.

    Parameters:
        basal_data (DataFrame): The input is a basal data dataframe containing columns 'datetime', and 'basal_rate'.

    Returns:
        basal_data (DataFrame): The transformed basal equivalent deliveries with aligned timestamps and duplicates removed.
    """
    series = basal_data.set_index('datetime').basal_rate
    if not series.index.is_monotonic_increasing:
        logger.warning('The index is not sorted. Sorting the index.')
        series = series.sort_index()
    
    resampled = resample_closest(series)
    resampled = resampled.ffill(limit=24*12-1).rename(columns={'basal_rate':'basal_delivery'}) / 12.0
    return resampled.reset_index()
