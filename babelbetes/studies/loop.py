# File: loop.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from dask import dataframe as dd
from babelbetes.src.logger import Logger
import os 
import zipfile_deflate64

from .studydataset import StudyDataset

def unzip_folder(zip_path, extract_to):
    """
    Extracts all contents of a ZIP archive to the specified directory.

    Parameters:
        zip_path (str): Path to the ZIP file.
        extract_to (str): Directory where the contents should be extracted.
    """
    with zipfile_deflate64.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


class Loop(StudyDataset):

    def __init__(self, study_path):
        super().__init__(study_path, 'Loop')
        self._logger = Logger.get_logger('Loop')
        
        # We convert the csvs into parquet files in a temporary directory
        self._temp_dir = os.path.join(os.path.dirname(self.study_path), '..', 'temp')
        self._cgm_parquet_filename = 'loop_cgm.parquet'
        self._basal_parquet_filename = 'loop_basal.parquet'
        self._bolus_parquet_filename = 'loop_bolus.parquet'
    
    def _convert_csv_to_partqet(self, ddf, parquet_path, override=False):
        if os.path.exists(parquet_path) and (not override):
            self._logger.debug(f"{os.path.basename(parquet_path)} already exists. Skipping conversion.")
        else:
            self._logger.debug(f"{parquet_path} does not exist yet. Converting CSV to parquet.")

            # Patient data is spread across 6 large files and processing them in sequence would cause much overhead
            # therefore, export as parquet to a local directory indexed by PtID 
            # this allows us faster processing using dask later on
            ddf.to_parquet(parquet_path, partition_on='PtID')
            self._logger.debug(f"CSV files converted to parquet file {parquet_path}")

    def _load_data(self, subset: bool = False):
        #save for later since we are loading data lazily using dask
        self._load_subset = subset

        # if we received a zip file, we extract it to a temporary folder
        if '.zip' in self.study_path:
            self._logger.debug(f"Extracting Loop study file {self.study_path}")
            self._extracted_path = self.study_path.split('.zip')[0]
            # Check if the extracted path already exists; if not, extract the zip file
            if not os.path.exists(self._extracted_path):
                os.mkdir(self._extracted_path)
                unzip_folder(self.study_path, extract_to=self._extracted_path)
            else:
                self._logger.debug(f"Extracted path {self._extracted_path} already exists. Using existing folder.")
        else: #we received a folder
            self._extracted_path = self.study_path
        
        # Create a temporary directory to store the parquet files
        if not os.path.exists(self._temp_dir):
            os.makedirs(self._temp_dir)
            self._logger.debug(f"Temporary directory created at {self._temp_dir}")
        
        self._df_patient = pd.read_csv(os.path.join(self._extracted_path, 'Data Tables',  'PtRoster.txt'), sep='|')
        
        # Load the data from the CSV files and convert them to parquet files
        ddf_cgm = dd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceCGM*.txt'), sep='|', 
                            parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S', 
                            usecols=['PtID', 'UTCDtTm', 'RecordType', 'CGMVal'])
        ddf_basal = dd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceBasal*.txt'), sep='|', 
                                parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S', 
                                usecols=['PtID', 'UTCDtTm', 'BasalType', 'Duration', 'Rate'])
        self._convert_csv_to_partqet(ddf_cgm, os.path.join(self._temp_dir, self._cgm_parquet_filename))
        self._convert_csv_to_partqet(ddf_basal, os.path.join(self._temp_dir, self._basal_parquet_filename))

    
    def _extract_cgm_as_dask(self):
        # Load the parquet file
        ddf = dd.read_parquet(os.path.join(self._temp_dir,self._cgm_parquet_filename), aggregate_files='PtID')
        if self._load_subset:
            ddf = ddf.partitions[:2]
        
        # keep only CGM records (removes calibrations, etc.)
        ddf = ddf.loc[ddf.RecordType == 'CGM']

        # Convert to mg/dL
        ddf['CGMVal'] = ddf.CGMVal * 18.018

        # Convert to local datetime
        ddf = ddf.map_partitions(lambda df: df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left'))
        ddf['UTCDtTm'] = ddf['UTCDtTm'] + dd.to_timedelta(ddf['PtTimezoneOffset'], unit='hour')

        #drop duplicates (we see only insignificant differences in duplicates, likely due to rounding)
        ddf = ddf.map_partitions(lambda df: df.drop_duplicates(subset=['UTCDtTm']))

        #sort
        ddf = ddf.map_partitions(lambda df: df.sort_values('UTCDtTm'))

        #clip CGM data to 40-400 mg/dL, drop outliers (see dedicated analysis)
        ddf = ddf[ddf.CGMVal > 38]
        ddf["CGMVal"] = ddf["CGMVal"].clip(lower=40, upper=400)
        
        # Reduce, Rename
        ddf = ddf.drop(columns=['PtTimezoneOffset', 'RecordType'])

        ddf  = ddf.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                   'UTCDtTm': self.COL_NAME_DATETIME,
                                   'CGMVal': self.COL_NAME_CGM}) 
        
        ddf = ddf.astype({self.COL_NAME_PATIENT_ID: 'str'})
        return ddf
    
    def _extract_cgm_history(self):
        ddf = self._extract_cgm_as_dask()
        df = ddf.compute()
        return df

    def _extract_bolus_event_history(self):
        # Load the parquet file
        df = pd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceBolus.txt'), sep='|', 
                                parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                                usecols=['PtID', 'UTCDtTm', 'Normal', 'Extended', 'Duration'])
        
        # Convert to local datetime
        df = df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left')
        df['UTCDtTm'] = df.UTCDtTm + pd.to_timedelta(df.PtTimezoneOffset, unit='hour')

        #drop duplicates
        df = df.drop_duplicates(subset=['PtID', 'UTCDtTm'])

        # Split extended and normal boluses
        # for normal boluses the delivery duration = 0,
        # some normal boluses are NaN (relating to square boluses (no immediate part)) and should be dropped
        normal = df.drop(columns=['Extended']).dropna(subset='Normal')
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')

        #extended boluses have a delivery duration
        extended = df.drop(columns=['Normal']).dropna(subset=['Extended']).rename(columns={"Extended": "Normal"})
        extended['Duration'] = pd.to_timedelta(extended.Duration, unit='millisecond')
        # Some 108 extended durations are zero, probably indicating a cancelled bolus. These would become duplicates to the normal boluses part.
        extended = extended.loc[extended.Duration > pd.to_timedelta(0, unit='millisecond')]
        df = pd.concat([normal, extended], axis=0).sort_values('UTCDtTm')
        
        # Reduce, Rename, Return
        df = df.drop(columns=['PtTimezoneOffset'])

        df['PtID'] = df['PtID'].astype('str')
        df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                            'Normal': self.COL_NAME_BOLUS,
                            'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION,
                            'UTCDtTm': self.COL_NAME_DATETIME}, inplace=True)

        return df

    def _extract_basal_as_dask(self):
        # Load the parquet file
        ddf = dd.read_parquet(os.path.join(self._temp_dir, self._basal_parquet_filename), 
                              aggregate_files='PtID',
                              usecols=['PtID', 'UTCDtTm', 'Rate'])
        if self._load_subset:
            ddf = ddf.partitions[:10]
        
        #sort by datetime 
        #TODO: Check if it was not sorted
        ddf = ddf.map_partitions(lambda df: df.sort_values('UTCDtTm'))

        #drop duplicates
        ddf = ddf.map_partitions(lambda df: df.drop_duplicates(subset=['UTCDtTm']))

        #replace NaN basal rates with zero (these are suspends)
        ddf = ddf.map_partitions(lambda df: df.fillna({'Rate': 0}))

        # Convert to local datetime
        ddf = ddf.map_partitions(lambda df: df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left'))
        ddf['UTCDtTm'] = ddf['UTCDtTm'] + dd.to_timedelta(ddf['PtTimezoneOffset'], unit='hour')

        # Rename, Reduce, Return
        ddf  = ddf.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                  'UTCDtTm': self.COL_NAME_DATETIME,
                                  'Rate': self.COL_NAME_BASAL_RATE}) 
        ddf = ddf[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BASAL_RATE]]
        ddf = ddf.astype({self.COL_NAME_PATIENT_ID: 'str'})
        return ddf
    
    def _extract_basal_event_history(self):
        ddf = self._extract_basal_as_dask()
        df = ddf.compute()
        return df
    

if __name__ == "__main__":
    pass