import pandas as pd
from dask import dataframe as dd
from studydataset import StudyDataset
import tempfile
import shutil
from src.logger import Logger
import time 
import os 

class Loop(StudyDataset):

    def __init__(self, study_path):
        super().__init__(study_path, 'Loop')
        
        self._cgm_parquet_filename = 'loop_cgm.parquet'
        self._basal_parquet_filename = 'loop_basal.parquet'
        self._bolus_parquet_filename = 'loop_bolus.parquet'

        self.logger = Logger.get_logger('Loop')
        self.temp_dir = os.path.join(self.study_path, '..', '..', 'temp')
        self.load_subset = False
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.debug(f"Temporary directory created at {self.temp_dir}")
        
    def __del__(self):
        pass
        #TODO: Convert to temporary directories
        # Delete the temporary directory and its contents
        # shutil.rmtree(self.temp_dir)
    
    def convert_csv_to_partqet(self, ddf, parquet_path, override=False):
        if os.path.exists(parquet_path) and (not override):
            self.logger.debug(f"{os.path.basename(parquet_path)} already exists. Skipping conversion.")
        else:
            self.logger.debug("{parquet_path} does not exist yet. Converting CSV to parquet.")

            # Patient data is spread across 6 large files and processing them in sequence would cause much overhead
            # therefore, export as parquet to a local directory indexed by PtID 
            # this allows us faster processing using dask later on
            ddf.to_parquet(parquet_path, partition_on='PtID')
            self.logger.debug(f"CSV files converted to parquet file {parquet_path}")

    def _load_data(self, subset: bool = False):
        self.df_patient = pd.read_csv(os.path.join(self.study_path, 'Data Tables',  'PtRoster.txt'), sep='|')
        self.load_subset = subset

        # Load the data from the CSV files and convert them to parquet files
        ddf_cgm = dd.read_csv(os.path.join(self.study_path, 'Data Tables', 'LOOPDeviceCGM*.txt'), sep='|', 
                            parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S', 
                            usecols=['PtID', 'UTCDtTm', 'RecordType', 'CGMVal'])
        
        
        ddf_basal = dd.read_csv(os.path.join(self.study_path, 'Data Tables', 'LOOPDeviceBasal*.txt'), sep='|', 
                                parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S', 
                                usecols=['PtID', 'UTCDtTm', 'BasalType', 'Duration', 'Rate'])
        self.convert_csv_to_partqet(ddf_cgm, os.path.join(self.temp_dir, self._cgm_parquet_filename))
        self.convert_csv_to_partqet(ddf_basal, os.path.join(self.temp_dir, self._basal_parquet_filename))
        
    def _extract_cgm_history(self):
        self.logger.debug("Extracting CGM history...")
        
        # Load the parquet file
        ddf = dd.read_parquet(os.path.join(self.temp_dir,self._cgm_parquet_filename), aggregate_files='PtID')
        if self.load_subset:
            ddf = ddf.partitions[:2]
        
        # Make sure divisions are set correctly
        ddf = ddf.set_index('PtID') 
        
        # keep only CGM records (removes calibrations, etc.)
        ddf = ddf.loc[ddf.RecordType == 'CGM']
        ddf.index = ddf.index.astype('int')  # Workaround to omit error when there are no rows left

        #drop duplicates
        ddf = ddf.map_partitions(lambda df: df.drop_duplicates(subset=['UTCDtTm', 'CGMVal']))

        # Convert to mg/dL
        ddf['CGMVal'] = ddf.CGMVal * 18.018

        # Convert to local datetime
        ddf = ddf.map_partitions(lambda df: df.merge(self.df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left'))
        ddf['UTCDtTm'] = ddf['UTCDtTm'] + dd.to_timedelta(ddf['PtTimezoneOffset'], unit='hour')

        # Reduce, Rename, Return
        ddf = ddf.drop(columns=['PtTimezoneOffset', 'RecordType'])

        # Convert Dask DataFrame to pandas DataFrame
        self.logger.debug("Converting Dask DataFrame to pandas DataFrame")
        
        #TODO: This is just for testing
        start_time = time.time()
        df_cgm = ddf.compute()
        self.logger.debug(f"compute() took: {time.time() - start_time} seconds")

        #TODO: Check if reset_index can be done before compute() without harming performance
        start_time = time.time()
        df_cgm.reset_index(inplace=True)
        df_cgm['PtID'] = df_cgm['PtID'].astype('str')
        df_cgm.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                               'CGMVal': self.COL_NAME_CGM, 
                               'UTCDtTm': self.COL_NAME_DATETIME}, inplace=True)
        self.logger.debug(f"The rest took: {time.time() - start_time} seconds")

        return df_cgm


    def _extract_bolus_event_history(self):
        # Load the parquet file
        df = pd.read_csv(os.path.join(self.study_path, 'Data Tables', 'LOOPDeviceBolus.txt'), sep='|', 
                                parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                                usecols=['PtID', 'UTCDtTm', 'Normal', 'Extended', 'Duration'])
        
        #drop duplicates
        df = df.drop_duplicates(subset=['PtID', 'UTCDtTm'])
        
        # Convert to local datetime
        df = df.merge(self.df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left')
        df['UTCDtTm'] = df.UTCDtTm + pd.to_timedelta(df.PtTimezoneOffset, unit='hour')

        #split extended and normal boluses
        #for normal boluses the delivery duration = 0
        normal = df.drop(columns=['Extended'])
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')

        #extended boluses have a delivery duration
        extended = df.drop(columns=['Normal']).dropna(subset=['Extended']).rename(columns={"Extended": "Normal"})
        extended['Duration'] = pd.to_timedelta(extended.Duration, unit='millisecond')
        df = pd.concat([normal, extended], axis=0).sort_values('UTCDtTm')
        
        # Reduce, Rename, Return
        df = df.drop(columns=['PtTimezoneOffset'])

        df['PtID'] = df['PtID'].astype('str')
        df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                            'Normal': self.COL_NAME_BOLUS,
                            'Duration': self.COL_NAME_BOLUS_DELIVERY_DURATION,
                            'UTCDtTm': self.COL_NAME_DATETIME}, inplace=True)

        return df

        
        
        


    def _extract_basal_event_history(self):

        # #return emtpy dataframe with right dtypes 
        # return pd.DataFrame(columns={
        #     self.COL_NAME_PATIENT_ID: pd.Series([], dtype='str'),
        #     self.COL_NAME_DATETIME: pd.Series([], dtype='datetime64[ns]'),
        #     self.COL_NAME_BASAL_RATE: pd.Series([], dtype='float64')
        # })
            
        # Load the parquet file
        ddf = dd.read_parquet(os.path.join(self.temp_dir, self._basal_parquet_filename), aggregate_files='PtID')
        if self.load_subset:
            ddf = ddf.partitions[:2]
        
        # Make sure divisions are set correctly
        ddf = ddf.set_index('PtID') 

        #drop duplicates
        ddf = ddf.map_partitions(lambda df: df.drop_duplicates(subset=['UTCDtTm']))

        # Convert to local datetime
        ddf = ddf.map_partitions(lambda df: df.merge(self.df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left'))
        ddf['UTCDtTm'] = ddf['UTCDtTm'] + dd.to_timedelta(ddf['PtTimezoneOffset'], unit='hour')

        # Reduce, Rename, Return
        ddf = ddf.drop(columns=['PtTimezoneOffset', 'RecordType'])

        # Convert Dask DataFrame to pandas DataFrame
        self.logger.debug("Converting Dask DataFrame to pandas DataFrame")
        
        
        start_time = time.time() #TODO: Remove these
        df = ddf.compute()
        self.logger.debug(f"compute() took: {time.time() - start_time} seconds")

        start_time = time.time()
        df.reset_index(inplace=True)
        df['PtID'] = df['PtID'].astype('str')
        df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 
                           'Rate': self.COL_NAME_BASAL_RATE, 
                           'UTCDtTm': self.COL_NAME_DATETIME}, inplace=True)
        
        self.logger.debug(f"The rest took: {time.time() - start_time} seconds")

        
        
   

# Example usage
if __name__ == "__main__":
    pass #TODO: Add working example
    