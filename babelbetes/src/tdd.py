# File: tdd.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import numpy as np
from datetime import timedelta
from babelbetes.src.logger import Logger
logger = Logger().get_logger(__name__)

def total_delivered(df, datetime_col, rate_col):
    """Calculate the total delivered insulin over the time intervals in the given DataFrame."""
    x = (df[datetime_col].diff().dt.total_seconds()/3600)[1:]
    y = df[rate_col][:-1]
    if len(x) == 0:
        r= np.nan
    else:
        r = np.sum(x.values * y.values)
    return r


def calculate_daily_basal_dose(df):
    """
    Calculate the Total Daily Dose (TDD) of basal insulin for each day in the given DataFrame.
    
    Args:
        df (pandas.DataFrame): The DataFrame containing the insulin data.
    
    Returns:
        tdds (pandas.DataFrame):  dataframe with two columns: `date` and `dose` golding the daily total basal dose. 
    
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
    copy['date'] = copy.datetime.dt.date
    
    
    #make sure midnights are included for both days
    midnight_mask = copy.datetime.isin(supports)
    copy.loc[midnight_mask, 'date'] = copy.loc[midnight_mask, 'datetime'].dt.date.apply(lambda x: (x,x-pd.Timedelta(days=1)))  # or .dt.normalize() if you want Timestamps
    copy = copy.explode('date')

    #this results in an additional day group before/after the first/last date which we don't want
    copy = copy.loc[~copy.date.isin([copy.date.max(),copy.date.min()])]
    #display(copy)

    tdds = copy.groupby('date').apply(total_delivered,'datetime','basal_rate').to_frame().rename(columns={0:'basal'})

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
        tdd (DataFrame): DataFrame containing both the bolus and basal tdd data.
    """
    daily_basals = df_basal.groupby('patient_id').apply(calculate_daily_basal_dose, include_groups=False )
    daily_bolus = df_bolus.groupby('patient_id').apply(calculate_daily_bolus_dose, include_groups=False)
    return daily_basals.merge(daily_bolus, how='outer', on=['patient_id', 'date'])
