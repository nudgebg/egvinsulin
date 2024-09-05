import pandas as pd
import time
from datetime import timedelta
import numpy as np

def _durations_since_previous_valid_value(dates, values):
    """
    Calculate the durations between each date and the previous date with a valid value (non NaN).

    Parameters:
    dates (list): A list of dates.
    values (list): A list of values.

    Returns:
    list: A list of durations between each date and the previous valid date. NaN if there is no previous valid date.
    """
    last_valid_date = None
    durations = []
    for (date, value) in zip(dates, values):
        duration = np.NaN
        if last_valid_date is not None:
            duration = date - last_valid_date
        if not np.isnan(value):
            last_valid_date = date
        durations.append(duration)
    return durations

def _combine_and_forward_fill(basal_df, gap=float('inf')):
    # forward fill, but only if duration between basal values is smaller than the threshold
    durations = _durations_since_previous_valid_value(basal_df['datetime'], basal_df['basal_delivery'])
    bSignificantGap = [True if pd.notna(
                        duration) and duration >= gap else False for duration in np.array(durations)]
    basal_df['basal_delivery'] = basal_df['basal_delivery'].where(
                        bSignificantGap, basal_df['basal_delivery'].ffill())
    return basal_df

import pandas as pd
import numpy as np
from datetime import timedelta

F = '1H'

# Function to split the bolus into multiple deliveries
def split_bolus(datetime, bolus, duration, sampling_frequency):
    steps = max(1, np.ceil(duration / pd.to_timedelta(sampling_frequency)))
    delivery_per_interval = bolus / steps
    times = pd.date_range(start=datetime, end=datetime + duration, freq=sampling_frequency, inclusive='left')
    deliveries = [delivery_per_interval] * len(times)
    return {'datetime': times, 'delivery': deliveries}


#functions for time alignment and transformation of basal, bolus, and cgm event data. These functions can be used for any study dataset.
def bolus_transform(df):
    """
    Transform the bolus data by aligning timestamps, handling duplicates, and extending boluses based on durations.

    Parameters:
    - bolus_data (DataFrame): The input is a bolus data dataframe containing columns 'datetime', 'bolus', and 'delivery_duration'.

    Returns:
    - bolus_data (DataFrame): 5 Minute resampled and time aligned at midnight bolus data with columns: datetime, delivery
    """

    sampling_frequency = '5min'

    expanded_rows = [split_bolus(row['datetime'], row['bolus'], row['delivery_duration'], sampling_frequency) for _, row in df.iterrows()]
    
    # Concatenate the lists of datetimes and deliveries
    datetimes = np.concatenate([item['datetime'] for item in expanded_rows])
    deliveries = np.concatenate([item['delivery'] for item in expanded_rows])
    expanded_events = pd.DataFrame({'datetime': datetimes, 'bolus': deliveries})
    
    # Round down to the nearest floored interval
    expanded_events['datetime'] = expanded_events['datetime'].dt.floor(sampling_frequency)
    
    # Sum up multiple entries for the same time
    expanded_events = expanded_events.groupby('datetime').sum().reset_index()
    
    # Resample to ensure all intervals are present
    start_time = df['datetime'].min().floor('D')  # Starting midnight
    end_time = (df['datetime'] + df['delivery_duration']).max().ceil('D')  # Ending at midnight next day
    all_times = pd.date_range(start=start_time, end=end_time, freq=sampling_frequency, inclusive='left')
    resampled_deliveries = expanded_events.set_index('datetime').reindex(all_times, fill_value=0).reset_index(drop=False, names =['datetime'])
    
    return resampled_deliveries

def cgm_transform(cgm_data):
    """
    time aligns the cgm data to midnight with a 5 minute sampling rate.

    Parameters:
    - cgm_data (DataFrame): The input is a cgm data dataframe containing columns 'patient_id, 'datetime', and 'cgm'.

    Returns:
    - cgm_data (DataFrame): The transformed cgm data with aligned timestamps.
    """
    #start data from midnight
    cgm_data = cgm_data.sort_values(by='datetime').reset_index(drop=True)
    cgm_data['datetime'] = cgm_data['datetime'].dt.round("5min")
    cgm_data['UnixTime'] = [int(time.mktime(cgm_data.datetime[x].timetuple())) for x in cgm_data.index]

    start_date = cgm_data['datetime'].iloc[0].date()
    end_date = cgm_data['datetime'].iloc[-1].date() + timedelta(days=1)
    
    cgm_from_mid = pd.DataFrame(columns=['datetime_adj'])
    cgm_from_mid['datetime_adj'] = pd.date_range(start = start_date, end = end_date, freq="5min").values

    cgm_from_mid['UnixTime'] = [int(time.mktime(cgm_from_mid.datetime_adj[x].timetuple())) for x in cgm_from_mid.index]
    cgm_from_mid = cgm_from_mid.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
    cgm_data = cgm_data.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')

    #merge new time with cgm data
    cgm_merged = pd.merge_asof(cgm_from_mid, cgm_data, on="UnixTime",direction="nearest",tolerance=149)

    cgm_data = cgm_merged.filter(items=['datetime_adj','cgm'])
    cgm_data = cgm_data.rename(columns={"datetime_adj": "datetime"}) 
    
    #replace not null values outside of 40-400 range with 40 or 400
    cgm_data.loc[cgm_data['cgm'] < 40, 'cgm'] = 40
    cgm_data.loc[cgm_data['cgm'] > 400, 'cgm'] = 400
    
    return cgm_data

def basal_transform(basal_data):
    """
    Transform the basal data by aligning timestamps and handling duplicates.

    Parameters:
    - basal_data (DataFrame): The input is a basal data dataframe containing columns 'patient_id, 'datetime', and 'basal_rate'.

    Returns:
    - basal_data (DataFrame): The transformed basal data with aligned timestamps and duplicates removed.
    """
    #start data from midnight
    basal_data = basal_data.sort_values(by='datetime').reset_index(drop=True)
    basal_data['datetime'] = basal_data['datetime'].dt.round("5min")
    basal_data['UnixTime'] = [int(time.mktime(basal_data.datetime[x].timetuple())) for x in basal_data.index]

    start_date = basal_data['datetime'].iloc[0].date()
    end_date = basal_data['datetime'].iloc[-1].date() + timedelta(days=1)
    
    basal_from_mid = pd.DataFrame(columns=['datetime_adj'])
    basal_from_mid['datetime_adj'] = pd.date_range(start = start_date, end = end_date, freq="5min").values

    basal_from_mid['UnixTime'] = [int(time.mktime(basal_from_mid.datetime_adj[x].timetuple())) for x in basal_from_mid.index]
    basal_from_mid = basal_from_mid.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
    #keep last basal rate if there is a duplicate time
    basal_data = basal_data.drop_duplicates(subset='UnixTime',keep='last')
    #merge new time with basal data
    basal_data = basal_data.sort_values(by='UnixTime')
    basal_merged = pd.merge_asof(basal_from_mid, basal_data, on="UnixTime", direction="nearest", tolerance=149)

    basal_data = basal_merged.filter(items=['datetime_adj','basal_rate'])
    basal_data = basal_data.rename(columns={"datetime_adj": "datetime"}) 

    #convert basal rate to 5 minute deliveries
    basal_data['basal_delivery'] = basal_data.basal_rate/12
    
    # forward fill (only up to 24 hours)
    basal_data = _combine_and_forward_fill(basal_data, gap=timedelta(hours=24))
    
    return basal_data
