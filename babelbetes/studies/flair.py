# File: flair.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import os
import numpy as np

from babelbetes.studies.studydataset import StudyDataset
from babelbetes.src.find_periods import find_periods
from babelbetes.src.pandas_helper import get_df
from babelbetes.src.date_helper import parse_flair_dates, convert_duration_to_timedelta
from babelbetes.src import pandas_helper

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
        self._df_pump = None
        self._df_cgm = None
        self._pump_file = os.path.join(self.study_path, 'Data Tables', 'FLAIRDevicePump.txt')
        self._cgm_file = os.path.join(self.study_path, 'Data Tables', 'FLAIRDeviceCGM.txt')

    def _load_data(self, subset) -> tuple[pd.DataFrame, pd.DataFrame]:
        df_cgm = get_df(self._cgm_file, usecols=['PtID', 'DataDtTm', 'DataDtTm_adjusted', 'CGM', 'Unusuable'], subset=subset)
        df_cgm['DateTime'] = df_cgm.loc[df_cgm.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates).astype('datetime64[ns]')
        df_cgm['DateTimeAdjusted'] = df_cgm.loc[df_cgm.DataDtTm_adjusted.notna(), 'DataDtTm_adjusted'].transform(parse_flair_dates).astype('datetime64[ns]')
        self._df_cgm = df_cgm

        # Using pump data mock for the data where it is removed
        df_pump = get_df(self._pump_file, usecols=['RecID', 'PtID', 'DataDtTm', 'BasalRt', 'TempBasalAmt', 'TempBasalType',
                                                    'TempBasalDur', 'BolusDeliv', 'ExtendBolusDuration', 'Suspend',
                                                    'AutoModeStatus', 'TDD'], subset=subset)
        df_pump['DateTime'] = df_pump.loc[df_pump.DataDtTm.notna(), 'DataDtTm'].transform(parse_flair_dates)
        #to datetime required because otherwise pandas provides a Object type which will fail the studydataset validation
        df_pump['DateTime'] = pd.to_datetime(df_pump['DateTime'])
        self._df_pump = df_pump.sort_values('DateTime')
    
    def _extract_bolus_event_history(self):
        df_bolus = self._df_pump.dropna(subset=['BolusDeliv']).copy()
        #convert ExtendBolusDuration to timedelta (do this first so that duplicates can be found)
        df_bolus['ExtendBolusDuration'] = df_bolus.ExtendBolusDuration.apply(lambda x: convert_duration_to_timedelta(x) if pd.notnull(x) else pd.Timedelta(0))
        
        #the extended boluses are reported upon completion
        df_bolus['DateTime'] = df_bolus['DateTime']-df_bolus['ExtendBolusDuration']
        df_bolus = df_bolus.sort_values(by=['PtID','DateTime', 'ExtendBolusDuration'])
        
        #drop zero boluses
        df_bolus = df_bolus[df_bolus.BolusDeliv != 0]
        
        #resolve duplicates:
        # most rows are duplicates with NaN Bolus Source
        # most others others are identical but the BolusDeliv value is rounded up by 0.005 
        # therefore we are using maximum record id (assuming later imports are more accurate)
        # we include the ExtendBolusDuration in the duplicate check to avoid dropping extended parts that start at the same time
        _,_,i_drop = pandas_helper.get_duplicated_max_indexes(df_bolus, ['PtID', 'DateTime', 'ExtendBolusDuration'],max_col='RecID')
        df_bolus = df_bolus.drop(i_drop)
        
        #reduce, rename, return
        df_bolus = df_bolus[['PtID', 'DateTime', 'BolusDeliv', 'ExtendBolusDuration']].copy().astype({'PtID': str})
        df_bolus = df_bolus.rename(columns={'PtID': 'patient_id', 'DateTime': 'datetime', 'BolusDeliv': 'bolus', 'ExtendBolusDuration': 'delivery_duration'})
        return df_bolus
    
    def _extract_basal_event_history(self):
        df_pump_copy = self._df_pump.copy()

        #adjust for temp basals
        df_pump_copy['merged_basal'] = df_pump_copy.groupby('PtID').apply(merge_basal_and_temp_basal,include_groups=False).droplevel(0)

        #adjust for closed loop periods
        df_pump_copy['basal_adj_cl'] = df_pump_copy.merged_basal
        df_pump_copy.loc[df_pump_copy.AutoModeStatus==True, 'basal_adj_cl'] = 0.0
        #setting the basal rate from NaN to zero can cause additional temporal duplicates if we already had a non Nan basal rate at the same time

        #adjust for pump suspends
        df_pump_copy['basal_adj_cl_spd'] = df_pump_copy.groupby('PtID').apply(lambda x: disable_basal(x, find_periods(x.dropna(subset='Suspend'), 'Suspend', 'DateTime', 
                                                                                                    lambda x: x != 'NORMAL_PUMPING', 
                                                                                                    lambda x: x == 'NORMAL_PUMPING'), 'basal_adj_cl'), include_groups=False).droplevel(0)

        #we drop duplicates after adjusting for temp basals, closed loop periods and pump suspends because these routines can cause additional duplicates
        #drop duplicates keeping the maximum value
        _,_,i_drop = pandas_helper.get_duplicated_max_indexes(df_pump_copy.dropna(subset=['basal_adj_cl_spd']), ['PtID','DateTime'], max_col='basal_adj_cl_spd')
        df_pump_copy = df_pump_copy.drop(i_drop)
        
        #reduce
        adjusted_basal = df_pump_copy.dropna(subset=['basal_adj_cl_spd'])[['PtID', 'DateTime', 'basal_adj_cl_spd']]
        adjusted_basal = adjusted_basal.rename(columns={'PtID':'patient_id', 'DateTime':'datetime', 'basal_adj_cl_spd':'basal_rate'})
        adjusted_basal['patient_id'] = adjusted_basal['patient_id'].astype(str)

        return adjusted_basal
    
    def _extract_cgm_history(self):
        df_cgm = self._df_cgm.copy()
        # Use DateTimeAdjusted over DateTime
        df_cgm['DateTime'] = df_cgm.DateTimeAdjusted.fillna(df_cgm.DateTime)
        #drop unusable cgms
        df_cgm = df_cgm[~df_cgm.Unusuable]
        #drop duplicates
        df_cgm = df_cgm.drop_duplicates(subset=['PtID', 'DateTime'])
        #sort
        df_cgm = df_cgm.sort_values(['PtID', 'DateTime'])
        #reduce, rename return
        df_cgm = df_cgm[['PtID', 'DateTime', 'CGM']].copy()
        df_cgm = df_cgm.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                                    'DateTime': self.COL_NAME_DATETIME,
                                    'CGM': self.COL_NAME_CGM})
        df_cgm[self.COL_NAME_PATIENT_ID] = df_cgm[self.COL_NAME_PATIENT_ID].astype(str)
        return df_cgm

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
            (pd.DataFrame): The DataFrame containing the retrieved TDDs based on the specified method.
        
        Raises:
            ValueError: If the method is not one of: 'max', 'sum', 'latest', 'all'.
        """
        TDDs = self._df_pump.dropna(subset=['TDD'])[['PtID','DateTime','TDD']]
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
    study_path = os.path.join(current_dir, '..', 'data','raw', 'FLAIRPublicDataSet')
    flair = Flair('FLAIR', study_path)
    flair.load_data()
    print(f'loaded data for {flair.study_name} from {flair.study_path}')
    basal_events = flair.extract_basal_event_history()
    cgm = flair.extract_cgm_history()
    boluses = flair.extract_bolus_event_history()
     
if __name__ == "__main__":
    main()
