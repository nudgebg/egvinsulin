import pandas as pd
import numpy as np

def get_duplicated_max_indexes(df, check_cols, max_col):
    """
    Find duplicate indexes, maximum indexes, and indexes to drop in a dataframe.

    Args:
    df (pd.DataFrame): The dataframe to check for duplicates.
    check_cols (list): The columns to check for duplicates.
    max_col (str): The column to use for keeping the maximum value.

    Returns:
    tuple: A tuple containing three elements:
        - duplicated_indexes (np.array): Indexes of duplicated rows.
        - max_indexes (np.array): Indexes of rows with the maximum value in the max_col.
        - drop_indexes (np.array): Indexes of rows to drop.

    Example:
        # Example usage get duplicated max indexes
        df = pd.DataFrame({
            'PtID': [1, 1, 1, 2, 2, 2, 3, 3, 3, 1],
            'DataDtTm': [1, 2, 3, 1, 2, 2, 1, 1, 1, 2],
            'CGMValue': [1, 2, 3, 1, 2, 3, 4, 2, 3, 3]
        })
        dup_indexes, max_indexes, drop_indexes = get_duplicated_max_indexes(df, ['PtID', 'DataDtTm'], 'CGMValue')
        print(df.drop(drop_indexes))
    """
    # Find duplicated rows based on the specified columns
    bDuplicated = df.duplicated(check_cols, keep=False)
    dup_indexes = bDuplicated[bDuplicated].index.values

    # Within the duplciates, find the indexes of the rows with the maximum value in the max_col
    max_indexes = df.loc[dup_indexes].groupby(check_cols)[max_col].idxmax().values

    # The other row indexes are to be dropped
    drop_indexes = np.setdiff1d(dup_indexes, max_indexes)
    
    return dup_indexes, max_indexes, drop_indexes

def split_sequences(df, label_col):
    """ Assigns a unique group ID to each sequence of consecutive labels.

    Args:
      df (pd.DataFrame): The DataFrame containing the data.
      label_col (str): The column name for the labels.

      Returns:
         (pd.Series): The group IDs.
    
    Example:
        df = pd.DataFrame({'label': ['A', 'A', 'B', 'B', 'B', 'A', 'A', 'C', 'C', 'A']})
        df['sequence'] = split_sequences(df, 'label')
        print(df)
        start_ends = df.groupby(['label', 'sequence']).apply(lambda group: pd.Series({
            'idxmin': group.index.min(),
            'idxmax': group.index.max()
        }),include_groups=False).reset_index()
        print(start_ends)
    """
    # Create a column to identify consecutive sequences
    return (df[label_col] != df[label_col].shift()).cumsum()

def split_groups(x: pd.Series, threshold) -> pd.Series:
   """Assigns unique group IDs based on the distance between consecutive values.

   Args:
       x (pd.Series): Series of numerical values.
       threshold : The maximum duration between two consecutive values to consider them in the same group.

   Returns:
       (pd.Series): The Series containing the data.
    
   Example:
    df = pd.DataFrame({'sensor': ['a', 'a', 'b', 'b', 'a', 'a', 'a', 'a', 'b', 'b', 'b', 'b'],
                       'y': [0, 1, 2, 3, 10, 11, 12, 13, 50, 51, 70, 71]})
    df['sensor_session'] = df.groupby('sensor').y.transform(lambda x: split_groups(x, 5))
    start_ends = df.groupby(['sensor', 'sensor_session']).y.agg(['idxmin','idxmax']).reset_index()
   """
   
   return (x.diff()>threshold).cumsum()

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

def get_hour_of_day(datetime_series):
        return datetime_series.dt.hour + datetime_series.dt.minute/60 + datetime_series.dt.second/3600

def _combine_and_forward_fill(basal_df, gap=float('inf')):
    # forward fill, but only if duration between basal values is smaller than the threshold
    durations = _durations_since_previous_valid_value(basal_df['datetime'], basal_df['basal_delivery'])
    bSignificantGap = [True if pd.notna(
                        duration) and duration >= gap else False for duration in np.array(durations)]
    basal_df['basal_delivery'] = basal_df['basal_delivery'].where(
                        bSignificantGap, basal_df['basal_delivery'].ffill())
    return basal_df

def _combine_and_backward_fill(df, date_column, value_column, gap=float('inf')):
    # backward fill, but only if duration between values is smaller than the threshold
    # note: the threshold here must be negative because we are looking backwards
    durations = _durations_since_previous_valid_value(df[date_column][::-1], df[value_column][::-1])[::-1]
    bSignificantGap = [True if pd.notna(duration) and duration <= gap else False for duration in np.array(durations)]
    filled = df[value_column].where(bSignificantGap, df[value_column].bfill())
    return filled


if __name__ == '__main__':
    df = pd.DataFrame({
            'PtID':     [1, 1, 1,  2, 2, 2,  3, 3, 3,  1],
            'DataDtTm': [1, 2, 3,  1, 2, 2,  1, 1, 1,  2],
            'CGMValue': [1, 2, 3,  1, 2, 3,  4, 2, 3,  3]
        })
    dup_indexes, max_indexes, drop_indexes = get_duplicated_max_indexes(df, ['PtID', 'DataDtTm'], 'CGMValue')
    print(df.drop(drop_indexes).sort_values(['PtID', 'DataDtTm']))


def head_tail(df,n=2):
    """
    Returns the first n rows and the last n rows of a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to get the head and tail of.
        n (int): The number of rows to return from the head and tail of the DataFrame.

    Returns:
        tuple: A tuple containing two DataFrames:
            - The first n rows of the DataFrame.
            - The last n rows of the DataFrame.
    """
    return pd.concat([df.head(n), df.tail(n)])