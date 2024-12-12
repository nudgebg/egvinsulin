import pandas as pd
from dask import dataframe as dd
from studies.studydataset import StudyDataset
import tempfile
import shutil
from src.logger import Logger
import time 
import os 

class Loop(StudyDataset):

    def __init__(self, study_path):
        super().__init__(study_path, 'Loop')
        
        self._cgm_parquet_filename = 'loop_cgm.parquet'
        self.logger = Logger.get_logger('Loop')
        self.temp_dir = os.path.join(self.study_path, '..', '..', 'temp')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            self.logger.debug(f"Temporary directory created at {self.temp_dir}")
        
    def __del__(self):
        pass
        # Delete the temporary directory and its contents
        # shutil.rmtree(self.temp_dir)
    
    def _load_data(self, subset: bool = False):
        self.df_patient = pd.read_csv(os.path.join(self.study_path, 'Data Tables',  'PtRoster.txt'), sep='|')
        
        self.logger.debug("Converting CGM files to parquet...")
        
        parquet_path = os.path.join(self.temp_dir, self._cgm_parquet_filename)
        if os.path.exists(parquet_path):
            self.logger.debug(f"Parquet file already exists. Using existing data at {parquet_path}")
        else:
            self.logger.debug("Parquet file does not exist. Creating new parquet file.")

            # Patient data is spread across 6 large files and processing them in sequence would cause much overhead
            # therefore, export as parquet to a local directory indexed by PtID 
            # this allows us faster processing using dask later on
            ddf_cgm = dd.read_csv(os.path.join(self.study_path, 'Data Tables', 'LOOPDeviceCGM*.txt'), sep='|', 
                            parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S', 
                            usecols=['PtID', 'UTCDtTm', 'RecordType', 'CGMVal'])

            ddf_cgm.to_parquet(parquet_path, partition_on='PtID')
            self.logger.debug(f"cgm files converted to temporary parquet file {parquet_path}")

    def _extract_cgm_history(self):
        self.logger.debug("Extracting CGM history...")
        # return pd.DataFrame({
        #     self.COL_NAME_PATIENT_ID: pd.Series(dtype='str'),
        #     self.COL_NAME_DATETIME: pd.Series(dtype='datetime64[ns]'),
        #     self.COL_NAME_CGM: pd.Series(dtype='float'),
        # })
    
        # Load the parquet file
        loop_parquet_path = os.path.join(self.temp_dir, self._cgm_parquet_filename)
        ddf = dd.read_parquet(loop_parquet_path, aggregate_files='PtID')
                              #TODO: Remove this filter
                              #filters=[('PtID', '<=', 20)])
        self.logger.debug(f"PtID column data type: {ddf['PtID'].dtype}")
        ddf = ddf.set_index('PtID')  # Make sure divisions are set correctly
        
        # keep only CGM records (removes calibrations, etc.)
        ddf = ddf.loc[ddf.RecordType == 'CGM']
        ddf.index = ddf.index.astype('int')  # Workaround to omit error when there are no rows left

        # Convert to mg/dL
        ddf['CGMVal'] = ddf.CGMVal * 18.018

        # Convert to local datetime
        ddf = ddf.join(self.df_patient[['PtID', 'PtTimezoneOffset']].set_index('PtID'), how='left')
        ddf['UTCDtTm'] = ddf.UTCDtTm + dd.to_timedelta(ddf.PtTimezoneOffset, unit='hour')

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
        df_cgm.rename(columns={'PtID': 'patient_id', 'CGMVal': 'cgm', 'UTCDtTm': 'datetime'}, inplace=True)
        self.logger.debug(f"The rest took: {time.time() - start_time} seconds")

        return df_cgm


    def _extract_bolus_event_history(self):
        # Return an empty DataFrame with the required columns
        return pd.DataFrame(columns=[
            self.COL_NAME_PATIENT_ID,
            self.COL_NAME_DATETIME,
            self.COL_NAME_BOLUS,
            self.COL_NAME_BOLUS_DELIVERY_DURATION
        ])

    def _extract_basal_event_history(self):
        # Return an empty DataFrame with the required columns
        return pd.DataFrame(columns=[
            self.COL_NAME_PATIENT_ID,
            self.COL_NAME_DATETIME,
            self.COL_NAME_BASAL_RATE
        ])
   

# Example usage
if __name__ == "__main__":
    pass #TODO: Add working example
    