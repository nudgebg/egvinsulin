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
        group_ids (pd.Series): The group IDs.
    
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
        dataframe (pd.DataFrame): A new pandas dataframe containing   

            - The first n rows of the DataFrame.  
            - The last n rows of the DataFrame.
    """
    return pd.concat([df.head(n), df.tail(n)])


def get_min_max_duplicates(df,dup_cols,val_col):
    dups = df[df.duplicated(subset=dup_cols, keep=False)]
    results = dups.groupby(dup_cols)[val_col].agg(['min','max'])
    return results


def overlaps(df, datetime_col, duration_col):
    """
    Check for overlapping intervals in a DataFrame.

    Args:
       df (pd.DataFrame): A DataFrame containing at least two columns:
            - 'datetime_col': Start times of the intervals.
            - 'duration_col': Durations of the intervals.
    Returns:
        pd.Series: A boolean Series indicating whether each interval overlaps
        with the next interval
    """
    assert df[datetime_col].is_monotonic_increasing
    end = df[datetime_col] + df[duration_col]
    next = df[datetime_col].shift(-1)
    overlap = (next < end)
    return overlap


def count_differences_in_duplicates(df, subset):
    """
    Counts the number of differences between duplicated rows for all columns.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
    
    Returns:
        series (pd.Series): A series where the index represents column names and values represent the count of differences.
    """
    duplicated_rows = df[df.duplicated(keep=False, subset=subset)]  # Keep all duplicate occurrences
    
    if duplicated_rows.empty:
        return pd.Series({col: 0 for col in df.columns})
    
    # Group by all columns and compute pairwise differences
    diff_counts = (duplicated_rows.groupby(subset)
                   .apply(lambda group: group.nunique(dropna=False) > 1)
                   .sum())
    
    return diff_counts


def extract_surrounding_rows(df, index, n, sort_by):
    """
    Extracts rows surrounding a given index after sorting the DataFrame by a subset of columns.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
        index (int): The row index to center on.
        n (int): The number of rows before and after the given index to extract (using logical indexing).
        sort_by (list): List of column names to sort the DataFrame by.
    Returns:
        pd.DataFrame: A DataFrame containing the extracted rows.
    """
    if index not in df.index:
        raise ValueError("The provided index is not in the DataFrame.")
    
    sorted_df = df.sort_values(by=sort_by)
    i_loc = sorted_df.index.get_loc(index)
    
    start = max(i_loc - n, 0)
    end = min(i_loc + n + 1, len(sorted_df))
    
    return sorted_df.iloc[start:end]


def grouped_value_counts(df, group_cols, value_cols):
    """
    Count the number of NaN, Non-NaN, and Zero values in each group of a DataFrame.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
        group_cols (str or list): The column(s) to group by.
        value_cols (str or list): The column(s) to count values for.
    
    Returns:
        dataframe (pd.DataFrame): A DataFrame containing the count of NaN, Non-NaN, and Zero values for each group.
    """
    if isinstance(group_cols, str):
        group_cols = [group_cols]
    if isinstance(value_cols, str):
        value_cols = [value_cols]

    def count_values(group):
        nan_count = group[value_cols].isna().sum().sum()  # Sum NaNs for all value columns
        non_nan_count = group[value_cols].notna().sum().sum()  # Sum Non-NaNs for all value columns
        zero_count = (group[value_cols] == 0).sum().sum()  # Sum zeros for all value columns
        return pd.Series({
            'NaN Count': nan_count,
            'Non-NaN Count': non_nan_count,
            'Zero Count': zero_count
        })

    return df.groupby(group_cols).apply(count_values).reset_index()