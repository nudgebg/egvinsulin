import pandas as pd
import numpy as np
from datetime import timedelta
from src.logger import Logger
logger = Logger().get_logger(__name__)

def durations_since_previous_valid_value(dates, values):
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
        duration = np.nan
        if last_valid_date is not None:
            duration = date - last_valid_date
        if not np.isnan(value):
            last_valid_date = date
        durations.append(duration)
    return durations

def combine_and_forward_fill(df, colname_date, col_name_value, gap: timedelta):
    #forward fill, but only if duration between values is smaller than the threshold
    combined_df = df.copy() 
    combined_df['temp'] = df[col_name_value].ffill()
    durations = pd.Series(durations_since_previous_valid_value(combined_df[colname_date], combined_df[col_name_value])) 
    bSmallGap = durations <=  gap
    combined_df.loc[bSmallGap, col_name_value] = combined_df.temp
    return combined_df.drop(columns=['temp'])


def calculate_daily_basal_dose(df):
    """
    Calculate the Total Daily Dose (TDD) of basal insulin for each day in the given DataFrame.
    
    Args:
        df (pandas.DataFrame): The DataFrame containing the insulin data.
    
    Returns:
        pandas.DataFrame: The daily basal rates DataFrame with two columns: 'date' and 'basal'. 
        The 'date' column contains the dates of each day, and the 'basal' column contains the calculated TDDs.
    
    Required Column Names:
        - datetime: The timestamp of each basal insulin rate event.
        - basal_rate: The basal insulin rate event [U/hr].
    """ 
    
    if df.empty:
        logger.error('Empty dataframe passed to calculate daily basal dose')
        raise ValueError('Empty dataframe passed to calculate daily basal dose')

    valid_days = df.groupby(df.datetime.dt.date).datetime.count()>0
    valid_days = valid_days.reindex(pd.date_range(df.datetime.min().date(), df.datetime.max().date(), freq='D'), fill_value=False)


    #forward fill
    #add support points around midnight for forward filling
    supports = pd.date_range(df.datetime.min().date(), df.datetime.max().date() + pd.Timedelta(days=1), freq='D')
    missing_supports = supports[~supports.isin(df.datetime)]
    copy = df.copy()
    copy = pd.concat([copy, pd.DataFrame({'datetime': missing_supports})]).sort_values(by='datetime').reset_index(drop=True)
    copy['basal_rate'] = copy['basal_rate'].ffill()

    #display(copy)
    #make sure midnights are included for both days
    daydelta= pd.Timedelta(days=1)
    copy['date'] = copy.datetime.dt.date
    copy['date_before'] = copy.datetime.dt.date-daydelta
    copy['midnight'] = copy.date == copy.datetime
    copy['date'] = copy.apply(lambda row: {row['date']} if not row['midnight'] else {row['date'], row['date']-daydelta}, axis=1)
    copy = copy.drop(columns=['date_before','midnight'])
    copy = copy.explode('date')
    #this results in an additional day group before/after the first/last date which we don't want
    copy = copy.loc[~copy.date.isin([copy.date.max(),copy.date.min()])]
    #display(copy)

    #calcualte tdd
    def tdd(df):
        x = (df.datetime.diff().dt.total_seconds()/3600)[1:]
        y = df['basal_rate'][:-1]
        if len(x) == 0:
            r= np.nan
        else:
            r = np.sum(x.values * y.values)
        return r

    tdds = copy.groupby('date').apply(tdd).to_frame().rename(columns={0:'basal'})

    #exclude invalid days
    tdds.loc[valid_days.index[~valid_days]] = np.nan
    return tdds

def calculate_daily_bolus_dose(df):
    """
    Calculate the daily bolus dose for each patient.
    Parameters:
        df (pandas.DataFrame): The input DataFrame containing the following columns:
            - datetime (datetime): The date and time of the bolus dose.
            - bolus (float): The amount of bolus dose.
    Returns:
        pandas.DataFrame: A DataFrame with the daily bolus dose for each patient, grouped by patient_id and date.
    """
    return df.groupby(df.datetime.dt.date).agg({'bolus': 'sum'}).rename_axis('date')

def calculate_tdd(df_bolus, df_basal):
    """
    Calculates the total daily dose (TDD) by merging the daily basal dose and daily bolus dose.
    Parameters:
    df_bolus (DataFrame): DataFrame containing the bolus dose data.
        - patient_id (int): The ID of the patient.
        - datetime (datetime): The date and time of the bolus dose.
        - bolus (float): The amount of bolus dose.
    df_basal (DataFrame): DataFrame containing the basal dose data.
        - patient_id (int): The ID of the patient.
        - datetime (datetime): The date and time of the basal dose.
        - basal_rate (float): The basal insulin rate event [U/hr].
    Returns:
    DataFrame: DataFrame containing the merged TDD data.
    """
    daily_basals = df_basal.groupby('patient_id').apply(calculate_daily_basal_dose, include_groups=False )
    daily_bolus = df_bolus.groupby('patient_id').apply(calculate_daily_bolus_dose, include_groups=False)
    return daily_basals.merge(daily_bolus, how='outer', on=['patient_id', 'date'])
