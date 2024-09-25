from studies.studydataset import StudyDataset
import pandas as pd
import os
import numpy as np
from datetime import timedelta
from src.find_periods import find_periods

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

def disable_basal(df, periods, column):
    assert df.DateTime.is_monotonic_increasing, 'Data must be sorted by DateTime'

    basals = df.dropna(subset=[column])
    adjusted_basals = df[column].copy() # we start with absolute basals

    for suspend in periods:
        
        #find the last reported basal value before suspend ends
        previous_basal_rows = basals[basals.DateTime <= suspend.time_end]
        if not previous_basal_rows.empty:
            #for the suspend end event, reset basal to the last reported basal rate
            adjusted_basals.loc[suspend.index_end] = previous_basal_rows.iloc[-1][column]

            #for the suspend start event, set the basal rate to zero
            adjusted_basals.loc[suspend.index_start] = 0
        
            #set affected existing basal rates to zero 
            indexes = basals[(basals.DateTime >= suspend.time_start) & (basals.DateTime <= suspend.time_end)].index
            adjusted_basals[indexes] = 0
    return adjusted_basals

class Flair(StudyDataset):
    def __init__(self, study_path: str):
        super().__init__(study_path, 'Flair')
        self.basals = None
        self.boluses = None
        self.cgms = None
        self.df_pump = None
        self.df_cgm = None
        self.pump_file = os.path.join(
            self.study_path, 'Data Tables', 'FLAIRDevicePump.txt')
        
        self.cgm_file = os.path.join(self.study_path, 'Data Tables', 'FLAIRDeviceCGM.txt')
        if not os.path.exists(self.pump_file):
            raise FileNotFoundError(f"File not found: {self.study_path}")
        if not os.path.exists(self.cgm_file):
            raise FileNotFoundError(f"File not found: {self.study_path}")

    def load_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        if self.df_pump is None and self.df_cgm is None:
            df_cgm = pd.read_csv(self.cgm_file, sep="|", low_memory=False, usecols=['PtID', 'DataDtTm', 'DataDtTm_adjusted', 'CGM'])
            df_cgm['DateTime'] = df_cgm.loc[df_cgm.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates)
            df_cgm['DateTimeAdjusted'] = df_cgm.loc[df_cgm.DataDtTm_adjusted.notna(), 'DataDtTm_adjusted'].transform(parse_flair_dates)
            self.df_cgm = df_cgm

            df_pump = pd.read_csv(self.pump_file, sep="|", low_memory=False, usecols=['PtID', 'DataDtTm', 
                                                                                    'BasalRt', 'TempBasalAmt', 'TempBasalType', 'TempBasalDur',
                                                                                    'BolusDeliv', 'ExtendBolusDuration',
                                                                                    'Suspend', 'AutoModeStatus', 
                                                                                    'TDD'])
            
            df_pump['DateTime'] = df_pump.loc[df_pump.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates)
            #to datetime required because otherwise pandas provides a Object type which will fail the studydataset validation
            df_pump['DateTime'] = pd.to_datetime(df_pump['DateTime'])
            self.df_pump = df_pump.sort_values('DateTime')
        return self.df_cgm, self.df_pump
    
    def _extract_bolus_event_history(self):
        if self.boluses is None:
            subFrame = self.df_pump.dropna(subset=['BolusDeliv'])
            #ther are duplicated boluses, we need to remove them
            subFrame = subFrame[~subFrame.duplicated(subset=['PtID','DateTime', 'BolusDeliv'], keep='first')]
            boluses = subFrame[['PtID', 'DateTime', 'BolusDeliv', 'ExtendBolusDuration']].copy().astype({'PtID': str})
            boluses = boluses.rename(columns={'PtID': 'patient_id', 'DateTime': 'datetime', 'BolusDeliv': 'bolus', 'ExtendBolusDuration': 'delivery_duration'})
            boluses.delivery_duration = boluses.delivery_duration.apply(lambda x: convert_duration_to_timedelta(x) if pd.notnull(x) else pd.Timedelta(0))
            self.boluses = boluses
        return self.boluses
    
    def _extract_basal_event_history(self):
        if self.basals is None:
            df_pump_copy = self.df_pump.copy()

            #adjust for temp basals
            df_pump_copy['merged_basal'] = df_pump_copy.groupby('PtID').apply(merge_basal_and_temp_basal,include_groups=False).droplevel(0)
            
            #adjust for closed loop periods
            df_pump_copy['basal_adj_cl'] = df_pump_copy.merged_basal
            df_pump_copy.loc[df_pump_copy.AutoModeStatus==True, 'basal_adj_cl'] = 0.0

            #adjust for pump suspends
            df_pump_copy['basal_adj_cl_spd'] = df_pump_copy.groupby('PtID').apply(lambda x: disable_basal(x, find_periods(x.dropna(subset='Suspend'), 'Suspend', 'DateTime', 
                                                                                                     lambda x: x != 'NORMAL_PUMPING', 
                                                                                                     lambda x: x == 'NORMAL_PUMPING'), 'basal_adj_cl'), include_groups=False).droplevel(0)

            #reduce
            adjusted_basal = df_pump_copy.dropna(subset=['basal_adj_cl_spd'])[['PtID', 'DateTime', 'basal_adj_cl_spd']]
            adjusted_basal = adjusted_basal.rename(columns={'PtID':'patient_id', 'DateTime':'datetime', 'basal_adj_cl_spd':'basal_rate'})
            adjusted_basal['patient_id'] = adjusted_basal['patient_id'].astype(str)

            self.basals = adjusted_basal
        return self.basals
    
    def _extract_cgm_history(self):
        if self.cgms is None:
            # Use np.where to select DateTimeAdjusted if it's not null, otherwise use DateTime
            datetime = np.where(self.df_cgm['DateTimeAdjusted'].notnull(),
                                self.df_cgm['DateTimeAdjusted'],
                                self.df_cgm['DateTime'])
            # Select the AdjustedDateTime and CGM columns
            temp = pd.DataFrame({'patient_id': self.df_cgm['PtID'].astype(str),
                                'datetime': datetime,
                                'cgm': self.df_cgm['CGM']})
            self.cgms = temp
        return self.cgms

    def get_reported_tdds(self, method='max'):
        """
        Retrieves reported total daily doses (TDDs) based on the specified method.
        
        Parameters:
            method (str): The method to use for retrieving the TDDs. 
                - 'max': Returns the TDD with the maximum reported value for each patient and date.
                - 'sum': Returns the sum of all reported TDDs for each patient and date.
                - 'latest': Returns the TDD with the latest reported datetime for each patient and date.
                - 'all': Returns all TDDs without any grouping or filtering.
        
        Returns:
            pandas.DataFrame: The DataFrame containing the retrieved TDDs based on the specified method.
        
        Raises:
            ValueError: If the method is not one of: 'max', 'sum', 'latest', 'all'.
        """
        TDDs = self.df_pump.dropna(subset=['TDD'])[['PtID','DateTime','TDD']]
        TDDs['date'] = TDDs.DateTime.dt.date
        TDDs['PtID'] = TDDs.PtID.astype(str)
        TDDs = TDDs.rename(columns={'PtID':'patient_id','TDD':'tdd', 'DateTime':'datetime'})
    
        if method == 'max':
            return TDDs.groupby(['patient_id','date']).apply(lambda x: x.iloc[x.tdd.argmax()]).reset_index(drop=True)
        elif method == 'sum':
            return TDDs.groupby(['patient_id','date']).agg({'tdd':'sum'}).reset_index()
        elif method == 'latest':
            return TDDs.groupby(['patient_id','date']).apply(lambda x: x.iloc[x.datetime.argmax()]).reset_index(drop=True)
        elif method == 'all':
            return TDDs
        else:
            raise ValueError('method must be one of: max, sum, latest, all')


def main():
    #get directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    study_path = os.path.join(current_dir, '..', 'data/test', 'FLAIRPublicDataSet')
    flair = Flair('FLAIR', study_path)
    flair.load_data()
    print(f'loaded data for {flair.study_name} from {flair.study_path}')
    basal_events = flair.extract_basal_event_history()
    cgm = flair.extract_cgm_history()
    boluses = flair.extract_bolus_event_history()
    
    
if __name__ == "__main__":
    main()
