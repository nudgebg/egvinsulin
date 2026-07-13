# File: loop.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
from dask import dataframe as dd
from functools import cached_property
from babelbetes.logger import Logger
import os
import zipfile_deflate64

from .studydataset import StudyDataset
from babelbetes import pandas_helper

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

    _raw_attrs = ('_df_patient',)

    def __init__(self, study_path, subset=False):
        super().__init__(study_path, 'Loop', subset=subset)
        self._logger = Logger.get_logger('Loop')
        self._temp_dir = os.path.join(os.path.dirname(self.study_path), '..', 'temp')
        self._cgm_parquet_filename = 'loop_cgm.parquet'
        self._basal_parquet_filename = 'loop_basal.parquet'

    def _convert_csv_to_partqet(self, ddf, parquet_path, override=False):
        if os.path.exists(parquet_path) and (not override):
            self._logger.debug(f"{os.path.basename(parquet_path)} already exists. Skipping conversion.")
        else:
            self._logger.debug(f"{parquet_path} does not exist yet. Converting CSV to parquet.")
            ddf.to_parquet(parquet_path, partition_on='PtID')
            self._logger.debug(f"CSV files converted to parquet file {parquet_path}")

    @cached_property
    def _extracted_path(self):
        if '.zip' in self.study_path:
            self._logger.debug(f"Extracting Loop study file {self.study_path}")
            extracted = self.study_path.split('.zip')[0]
            if not os.path.exists(extracted):
                os.mkdir(extracted)
                unzip_folder(self.study_path, extract_to=extracted)
            else:
                self._logger.debug(f"Extracted path {extracted} already exists. Using existing folder.")
            return extracted
        return self.study_path

    @cached_property
    def _df_patient(self):
        if not os.path.exists(self._temp_dir):
            os.makedirs(self._temp_dir)
            self._logger.debug(f"Temporary directory created at {self._temp_dir}")
        return pd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'PtRoster.txt'), sep='|')

    def _extract_cgm_as_dask(self):
        cgm_path = os.path.join(self._temp_dir, self._cgm_parquet_filename)
        ddf_csv = dd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceCGM*.txt'), sep='|',
                              parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                              usecols=['PtID', 'UTCDtTm', 'RecordType', 'CGMVal'])
        self._convert_csv_to_partqet(ddf_csv, cgm_path)

        ddf = dd.read_parquet(cgm_path, aggregate_files='PtID')
        if self.subset:
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
        ddf = ddf.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                   'UTCDtTm': self.COL_NAME_DATETIME,
                                   'CGMVal': self.COL_NAME_CGM})
        ddf = ddf.astype({self.COL_NAME_PATIENT_ID: 'str'})
        return ddf

    def _extract_cgm_history(self):
        return self._extract_cgm_as_dask().compute()

    def _extract_bolus_event_history(self):
        df = pd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceBolus.txt'), sep='|',
                         parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                         usecols=['PtID', 'UTCDtTm', 'Normal', 'Extended', 'Duration'])

        # Convert to local datetime
        df = df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left')
        df['UTCDtTm'] = df.UTCDtTm + pd.to_timedelta(df.PtTimezoneOffset, unit='hour')

        #drop duplicates
        df = df.drop_duplicates(subset=['PtID', 'UTCDtTm'])

        # Split extended and normal boluses
        normal = df.drop(columns=['Extended']).dropna(subset='Normal')
        normal['Duration'] = pd.to_timedelta(0, unit='millisecond')

        extended = df.drop(columns=['Normal']).dropna(subset=['Extended']).rename(columns={"Extended": "Normal"})
        extended['Duration'] = pd.to_timedelta(extended.Duration, unit='millisecond')
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
        basal_path = os.path.join(self._temp_dir, self._basal_parquet_filename)
        ddf_csv = dd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceBasal*.txt'), sep='|',
                              parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                              usecols=['PtID', 'UTCDtTm', 'BasalType', 'Duration', 'Rate'])
        self._convert_csv_to_partqet(ddf_csv, basal_path)

        ddf = dd.read_parquet(basal_path, aggregate_files='PtID', usecols=['PtID', 'UTCDtTm', 'Rate'])
        if self.subset:
            ddf = ddf.partitions[:10]

        ddf = ddf.map_partitions(lambda df: df.sort_values('UTCDtTm'))
        ddf = ddf.map_partitions(lambda df: df.drop_duplicates(subset=['UTCDtTm']))
        ddf = ddf.map_partitions(lambda df: df.fillna({'Rate': 0}))

        # Convert to local datetime
        ddf = ddf.map_partitions(lambda df: df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left'))
        ddf['UTCDtTm'] = ddf['UTCDtTm'] + dd.to_timedelta(ddf['PtTimezoneOffset'], unit='hour')

        # Rename, Reduce, Return
        ddf = ddf.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                                  'UTCDtTm': self.COL_NAME_DATETIME,
                                  'Rate': self.COL_NAME_BASAL_RATE})
        ddf = ddf[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_BASAL_RATE]]
        ddf = ddf.astype({self.COL_NAME_PATIENT_ID: 'str'})
        return ddf

    def _extract_basal_event_history(self):
        return self._extract_basal_as_dask().compute()

    def _extract_age_data(self):
        df_age = self._df_patient.copy()[['PtID', 'AgeAtEnrollment']].rename(columns={'PtID': self.COL_NAME_PATIENT_ID, 'AgeAtEnrollment': self.COL_NAME_AGE})
        return df_age.astype({self.COL_NAME_PATIENT_ID: str, self.COL_NAME_AGE: int})

    def _extract_wizard_carbs(self):
        df = pd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceWizard.txt'), sep='|',
                         parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                         usecols=['PtID', 'RecID', 'UTCDtTm', 'CarbInput'])
        df = df.dropna(subset=['CarbInput'])
        df = df[df['CarbInput'] > 0]

        # Convert to local datetime
        df = df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left')
        df['UTCDtTm'] = df.UTCDtTm + pd.to_timedelta(df.PtTimezoneOffset, unit='hour')

        # Drop temporal duplicates (keep max RecID)
        _, _, i_drop = pandas_helper.get_duplicated_max_indexes(df, ['PtID', 'UTCDtTm'], 'RecID')
        df = df.drop(index=i_drop)

        return df[['PtID', 'UTCDtTm', 'CarbInput']]

    def _extract_food_carbs(self):
        df = pd.read_csv(os.path.join(self._extracted_path, 'Data Tables', 'LOOPDeviceFood.txt'), sep='|',
                         parse_dates=['UTCDtTm'], date_format='%Y-%m-%d %H:%M:%S',
                         usecols=['PtID', 'RecID', 'UTCDtTm', 'CarbsNet'])
        df = df.dropna(subset=['CarbsNet'])
        df = df[df['CarbsNet'] > 0]

        # Convert to local datetime
        df = df.merge(self._df_patient[['PtID', 'PtTimezoneOffset']], on='PtID', how='left')
        df['UTCDtTm'] = df.UTCDtTm + pd.to_timedelta(df.PtTimezoneOffset, unit='hour')

        # Drop temporal duplicates (keep max RecID)
        _, _, i_drop = pandas_helper.get_duplicated_max_indexes(df, ['PtID', 'UTCDtTm'], 'RecID')
        df = df.drop(index=i_drop)

        return df[['PtID', 'UTCDtTm', 'CarbsNet']]

    def _extract_carb_history(self):
        wizard = self._extract_wizard_carbs().rename(columns={'CarbInput': 'carbs'})
        food = self._extract_food_carbs().rename(columns={'CarbsNet': 'carbs'})

        df = pd.concat([wizard, food], ignore_index=True)
        df = df.sort_values(['PtID', 'UTCDtTm'])

        # Rename and return
        df['PtID'] = df['PtID'].astype('str')
        df.rename(columns={'PtID': self.COL_NAME_PATIENT_ID,
                           'UTCDtTm': self.COL_NAME_DATETIME,
                           'carbs': self.COL_NAME_CARBS}, inplace=True)
        return df[[self.COL_NAME_PATIENT_ID, self.COL_NAME_DATETIME, self.COL_NAME_CARBS]]
