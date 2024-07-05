from studydataset import StudyDataset
import pandas as pd
import os
import numpy as np
from datetime import timedelta

def parse_flair_dates(dates):
    """Parse date strings separately for those with/without time component, interpret those without as midnight (00AM)
    Args:
        df (pandas DataFrame): data frame holding data date_column (string): 
        column name that holds date time strings to be used for parsing
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

def merge_basal_and_temp_basal(df):
    """
    Calculates the absolute basal rates based on the provided DataFrame.

    Parameters:
    - df: DataFrame
        The input DataFrame containing the basal rates and temp basal information.

    Returns:
    - absolute_basal: Series
        The calculated absolute basal rates.

    Algorithm:
     
    1. Start with the Standard Basal Rates.
    2. Iterate over the rows in the DataFrame containing temp basal information.
    3. Get the basal events within the temp basal active duration.
    4. Multiply the basal rates by the temp basal amount if the temp basal type is 'Percent'. Here, we make use of the fact that standard basal rates are reported after temp basal 
    rates start and stop (only if TempBasalType='Percent').
    5. Set the basal rate to the to the temp basal amount if the temp basal type is 'Rate'. 
    Here, we can not just override the reported basal rates because standard basal rates are not reported after the temp basal starts.
    Therefore, we set the BasalRt value for the row of the temp basal event which would usually be NaN.
    6. Set basal rates that are reporeted during temp basal of type 'Rate' is active to NaN.
    7. Return the calculated absolute basal rates.
    """
    
    adjusted_basal = df.BasalRt.copy() #start with the Standard Basal Rates
    df_sub_temp_basals = df.loc[df.TempBasalAmt.notna()]
    df_sub_basals = df.loc[df.BasalRt.notna()]

    for index, row in df_sub_temp_basals.iterrows():
        #get basal events within temp basal active duration
        temp_basal_interval = pd.Interval(row.DateTime, row.DateTime + convert_duration_to_timedelta(row.TempBasalDur))
        affected_basal_indexes = df_sub_basals.index[df_sub_basals.DateTime.apply(lambda x: x in temp_basal_interval)]
        
        #multiply if Percent
        if row.TempBasalType == 'Percent':
            adjusted_basal.loc[affected_basal_indexes] = df_sub_basals.BasalRt.loc[affected_basal_indexes]*row.TempBasalAmt/100
        #set BasalRate to TempBasal Rate
        else:
            adjusted_basal.loc[index] = row.TempBasalAmt
            adjusted_basal[affected_basal_indexes] = np.NaN
    return adjusted_basal

def adjust_basal_for_pump_suspends(df):
    assert df.DateTime.is_monotonic_increasing, 'Data must be sorted by DateTime'

    basals = df.dropna(subset=['BasalRt'])
    adjusted_basals = df.BasalRt.copy() # we start with absolute basals

    #combine pump suspend start and end events
    suspends = df.loc[df['Suspend'].notna(), ['Suspend', 'DateTime']]
    suspends['SuspendEndIndex'] = suspends.index
    suspends['SuspendEndIndex'] = suspends.SuspendEndIndex.shift(-1)
    suspends['SuspendEndEvent'] = suspends['Suspend'].shift(-1)
    suspends['SuspendEndDateTime'] = suspends['DateTime'].shift(-1)
    #we select pairs that start with a suspend event and end with a normal pumping event
    suspends = suspends.loc[(suspends['Suspend'] != 'NORMAL_PUMPING') & (suspends['SuspendEndEvent'] == 'NORMAL_PUMPING')]
    suspends =  suspends.reset_index().rename(columns={'index': 'SuspendIndex'})

    # Iterate over each suspend period
    for _, suspend in suspends.iterrows():
        
        #find the last reported basal value before suspend ends
        previous_basal_rows = basals[basals.DateTime <= suspend.SuspendEndDateTime]
        if not previous_basal_rows.empty:
            #for the suspend end event, reset basal to the last reported basal rate
            adjusted_basals.loc[suspend.SuspendEndIndex] = previous_basal_rows.iloc[-1]['BasalRt']

            #for the suspend start event, set the basal rate to zero
            adjusted_basals.loc[suspend.SuspendIndex] = 0
        
            #set affected existing basal rates to zero 
            indexes = basals[(basals.DateTime >= suspend.DateTime) & (basals.DateTime <= suspend.SuspendEndDateTime)].index
            adjusted_basals[indexes] = 0
    return adjusted_basals

class Flair(StudyDataset):
    def __init__(self, study_name: str, study_path: str):
        super().__init__(study_path, study_name)
        self.pump_file = os.path.join(
            self.study_path, 'Data Tables', 'FLAIRDevicePump.txt')
        
        self.cgm_file = os.path.join(self.study_path, 'Data Tables', 'FLAIRDeviceCGM.txt')
        if not os.path.exists(self.pump_file):
            raise FileNotFoundError(f"File not found: {self.study_path}")
        if not os.path.exists(self.cgm_file):
            raise FileNotFoundError(f"File not found: {self.study_path}")

    def load_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        df_cgm = pd.read_csv(self.cgm_file, sep="|", low_memory=False, usecols=['PtID', 'DataDtTm', 'DataDtTm_adjusted', 'CGM'])
        df_cgm['DateTime'] = df_cgm.loc[df_cgm.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates)
        df_cgm['DateTimeAdjusted'] = df_cgm.loc[df_cgm.DataDtTm_adjusted.notna(), 'DataDtTm_adjusted'].transform(parse_flair_dates)
        self.df_cgm = df_cgm

        df_pump = pd.read_csv(self.pump_file, sep="|", low_memory=False, usecols=['PtID', 'DataDtTm', 'NewDeviceDtTm', 'BasalRt',
                                                                                  'TempBasalAmt', 'TempBasalType', 'TempBasalDur', 'BolusType',
                                                                                  'BolusSource', 'BolusDeliv', 'BolusSelected', 'ExtendBolusDuration', 'BasalRtUnKnown',
                                                                                  'Suspend', 'PrimeVolumeDeliv', 'Rewind', 'TDD'])
        
        df_pump['DateTime'] = df_pump.loc[df_pump.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates)
        #to datetime required because otherwise pandas provides a Object type which will fail the studydataset validation
        df_pump['DateTime'] = pd.to_datetime(df_pump['DateTime'])
        self.df_pump = df_pump.sort_values('DateTime')

        return self.df_cgm, self.df_pump
    
    def _extract_bolus_event_history(self):
        subFrame = self.df_pump.dropna(subset=['BolusDeliv'])
        boluses = pd.DataFrame({'patient_id': subFrame['PtID'].astype(str), 
                                'datetime': subFrame['DateTime'], 
                                'bolus': subFrame['BolusDeliv'],
                                'delivery_duration': subFrame.ExtendBolusDuration.apply(lambda x: convert_duration_to_timedelta(x) if pd.notnull(x) else pd.Timedelta(0))})
        return boluses
    
    def _extract_basal_event_history(self):
        print('called')
        #merge basal and temp basal
        adjusted_basal = self.df_pump.groupby('PtID').apply(merge_basal_and_temp_basal).droplevel(0)#remove patient id index
        df_temp = pd.merge(self.df_pump[['PtID','DateTime','Suspend']], adjusted_basal, left_index=True, right_index=True)
        
        #adjust for pump suspends
        adjusted_basal = df_temp.groupby('PtID').apply(adjust_basal_for_pump_suspends).droplevel(0) #remove patient group index
        adjusted_basal = pd.merge(self.df_pump[['PtID','DateTime']], adjusted_basal, left_index=True, right_index=True)

        #reduce
        adjusted_basal = adjusted_basal.dropna(subset=['BasalRt'])[['PtID', 'DateTime', 'BasalRt']]
        adjusted_basal = adjusted_basal.rename(columns={'PtID':'patient_id', 'DateTime':'datetime', 'BasalRt':'basal_rate'})
        adjusted_basal['patient_id'] = adjusted_basal['patient_id'].astype(str)
        return adjusted_basal
    
    def _extract_cgm_history(self):
        # Use np.where to select DateTimeAdjusted if it's not null, otherwise use DateTime
        datetime = np.where(self.df_cgm['DateTimeAdjusted'].notnull(),
                            self.df_cgm['DateTimeAdjusted'],
                            self.df_cgm['DateTime'])
        # Select the AdjustedDateTime and CGM columns
        tmp = pd.DataFrame({'patient_id': self.df_cgm['PtID'].astype(str),
                            'datetime': datetime,
                            'cgm': self.df_cgm['CGM']})
        return tmp


def main():
    #get directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    study_path = os.path.join(current_dir, '..', 'data/test', 'FLAIRPublicDataSet')
    flair = Flair('FLAIR', study_path)
    flair.load_data()
    print(f'loaded data for {flair.study_name} from {flair.study_path}')
    #basal_events = flair.extract_basal_event_history()
    #cgm = flair.extract_cgm_history()
    boluses = flair.extract_bolus_event_history()
    
    
if __name__ == "__main__":
    main()
