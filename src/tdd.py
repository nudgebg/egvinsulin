import pandas as pd
import numpy as np

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
    #add support points around midnight for forward filling
    supports = pd.date_range(df.datetime.min().date(), df.datetime.max().date() + pd.Timedelta(days=1), freq='D')
    missing_supports = supports[~supports.isin(df.datetime)]
    df = pd.concat([df, pd.DataFrame({'datetime': missing_supports})]).sort_values(by='datetime').reset_index(drop=True)

    df['basal_rate'] = df.basal_rate.ffill()
    
    TDDs  = []
    for (start,end) in zip(supports[:-1], supports[1:]):
        subFrame = df.loc[(df.datetime >= start) & (df.datetime <= end)]
        x = (subFrame.datetime.diff().dt.total_seconds()/3600).values[1:]
        y = subFrame['basal_rate'].values[:-1]
        tdd = np.nansum(x * y)
        TDDs.append(tdd)
    return pd.DataFrame({'date': supports[:-1].date, 'basal': TDDs}).set_index('date')

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
