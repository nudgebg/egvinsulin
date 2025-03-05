import pandas as pd
import os
from src.logger import Logger
logger = Logger.get_logger(__name__)

def validate_bolus_output_dataframe(func):
    def wrapper(*args, **kwargs):
        df = func(*args, **kwargs)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Output should be a pandas DataFrame")
        required_columns = ['patient_id', 'datetime', 'bolus', 'delivery_duration']
        if set(df.columns) != set(required_columns):
            raise ValueError(f"DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate' but has {df.columns}")
        if not pd.api.types.is_datetime64_dtype(df['datetime'].dtype):
            raise ValueError("DataFrame should have a 'datetime' column of type pandas datetime but is {df['datetime'].dtype}")
        if not all(isinstance(item, str) for item in df['patient_id']):
            raise ValueError("DataFrame should have a 'patient_id' column of type string")
        if not pd.api.types.is_numeric_dtype(df['bolus'].dtype):
            raise ValueError("DataFrame should have a 'bolus' column of type float but is {df['bolus'].dtype}")
        if not pd.api.types.is_timedelta64_dtype(df['delivery_duration'].dtype):
            raise ValueError(f"DataFrame should have a 'delivery_duration' column of type timedelta but is {df['delivery_duration'].dtype}")
        return df
    return wrapper

def validate_basal_output_dataframe(func):
    def wrapper(*args, **kwargs):
        df = func(*args, **kwargs)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Output should be a pandas DataFrame")
        required_columns = ['patient_id', 'datetime', 'basal_rate']
        if set(df.columns) != set(required_columns):
            raise ValueError(f"DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate' but has {df.columns}")
        if not pd.api.types.is_datetime64_dtype(df['datetime'].dtype):
            raise ValueError("DataFrame should have a 'datetime' column of type pandas datetime")
        if not all(isinstance(item, str) for item in df['patient_id']):
            raise ValueError("DataFrame should have a 'patient_id' column of type string")
        if not pd.api.types.is_numeric_dtype(df['basal_rate'].dtype):
            raise ValueError(f"DataFrame should have a 'basal_rate' column of numeric type but is {df['basal_rate'].dtype}")
        return df
    return wrapper

def validate_cgm_output_dataframe(func):
    def wrapper(*args, **kwargs):
        df = func(*args, **kwargs)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Output should be a pandas DataFrame")
        required_columns = ['patient_id', 'datetime', 'cgm']
        if set(df.columns) != set(required_columns):
            raise ValueError(f"DataFrame should have columns 'patient_id', 'datetime' and 'cgm' but has {df.columns}")
        if not pd.api.types.is_datetime64_dtype(df['datetime'].dtype):
            raise ValueError("DataFrame should have a 'datetime' column of type pandas datetime")
        if not pd.api.types.is_object_dtype(df['patient_id'].dtype) or not all(isinstance(item, str) for item in df['patient_id']):
            raise ValueError("DataFrame should have a 'patient_id' column of type string")
        if not pd.api.types.is_numeric_dtype(df['cgm'].dtype):
            raise ValueError(f"DataFrame should have a 'cgm' column of numeric type but is {df['cgm'].dtype}")
        return df
    return wrapper

def save_to_csv(df, file_path, compressed):
    df.to_csv(file_path + (".csv.gz" if compressed else '.csv'), index=False, 
                compression='gzip' if compressed else None)

class StudyDataset:
    """
    The `StudyDataset` class is designed to handle and validate data related to a medical study.
    It has a member variable `df` which is a pandas DataFrame that holds the data.
    The class is initialized with a `study_path` which is the path to the study directory

    The class has several methods:

    - `load_data`: This method is automatically called before extracting data. However, it can also be called up-front. After data was loaded 
        the member variable `data_loaded` is set to True. It calls the `_load_data` method which should be implemented by subclasses.
    
    - `extract_bolus_event_history`, `extract_basal_event_history`, and `extract_cgm_history`:
      These methods are designed to extract specific types of data from the DataFrame.
      They are decorated with `validate_bolus_output_dataframe`, `validate_basal_output_dataframe`,
      and `validate_cgm_output_dataframe` respectively, which validate the output data.
      These methods should not be overridden by subclasses. Instead, subclasses should implement the corresponding `_extract_*` methods.

    - `_extract_bolus_event_history`, `_extract_basal_event_history`, and `_extract_cgm_history`:
      These methods are meant to be overridden by subclasses to extract specific types of data from the DataFrame.

    The returned dataframes are as follows:

    - For bolus event history: The DataFrame should have the columns 'patient_id' (string),
      'datetime' (pandas datetime), 'bolus' (float), and 'delivery_duration' (pandas timedelta).

    - For basal event history: The DataFrame should have the columns 'patient_id' (string),
      'datetime' (pandas datetime), and 'basal_rate' (float).

    - For cgm history: The DataFrame should have the columns 'patient_id' (string),
      'datetime' (pandas datetime), and 'cgm' (float).
    """

    COL_NAME_PATIENT_ID = 'patient_id'
    COL_NAME_DATETIME = 'datetime'
    COL_NAME_BOLUS = 'bolus'
    COL_NAME_BASAL_RATE = 'basal_rate'
    COL_NAME_BOLUS_DELIVERY_DURATION = 'delivery_duration'
    COL_NAME_CGM = 'cgm'


    def __init__(self, study_path, study_name):
        self.study_path = study_path
        self.study_name = study_name
        self.bolus_event_history = None
        self.basal_event_history = None
        self.cgm_history = None
        self.data_loaded = False

    def _load_data(self, subset: bool = False):
        raise NotImplementedError("Subclasses should implement the _load_data method")
    def _extract_bolus_event_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_bolus_event_history method")
    def _extract_basal_event_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_basal_event_history method")
    def _extract_cgm_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_cgm_history method")
    
    
    def load_data(self, subset=False):
        """Method to load the data from the study directory. 
        
        This method should be called before extracting any data from the dataset. 
        This method should not be overridden by subclasses. Instead, subclasses should implement the _load_data method.
        
        Args:
            subset (bool, optional): Should only load a small subset of the data for testing purposes. Defaults to False.
        """
        if not self.data_loaded:
            self._load_data(subset=subset)
            self.data_loaded = True

    @validate_bolus_output_dataframe
    def extract_bolus_event_history(self):
        """ Extract bolus event history from the dataset. 
        
        This method does do type checking on the output data and should not be overriden
        by subclasses. Instead, subclasses should implement the _extract_bolus_event_history method.
        
        Returns:
            bolus_events (pd.DataFrame): A DataFrame containing the bolus event history. The DataFrame should have the following columns:

                - `patient_id`: A string representing the patient ID
                - `datetime`: A pandas datetime object representing the date and time of the bolus event
                - `bolus`: A float representing the bolus amount in units
                - `delivery_duration`: A pandas timedelta object representing the duration of the bolus delivery.
                For standard boluses the delivery duration is 0 seconds, for extended boluses,
                these are the duration of the extended delivery.
        """
        if self.bolus_event_history is None:
            self.load_data()
            self.bolus_event_history = self._extract_bolus_event_history()
        return self.bolus_event_history

    @validate_basal_output_dataframe
    def extract_basal_event_history(self):
        """ Extract basal event history from the dataset. 
        This method does do type checking on the output data and should not be overriden by subclasses. 
        Instead, subclasses should implement the _extract_basal_event_history method.
                
        Returns:
            basal_event_history (pd.DataFrame): A DataFrame containing the basal event history. The DataFrame should have the following columns:

                - `patient_id`: A string representing the patient ID
                - `datetime`: A pandas datetime object representing the date and time of the basal event
                - `basal_rate`: A float representing the basal rate in units per hour
        """
        if self.basal_event_history is None:
            self.load_data()
            self.basal_event_history = self._extract_basal_event_history()
        return self.basal_event_history

    @validate_cgm_output_dataframe
    def extract_cgm_history(self):
        """ Extract cgm measurements from the dataset. This method does
        do type checking on the output data and should not be overriden
        by subclasses. Instead, subclasses should implement the _extract_cgm_history method.
        
        Returns:
            cgm_measurements (pd.DataFrame): A DataFrame containing the cgm measurements. The DataFrame should have the following columns:

                - `patient_id`: A string representing the patient ID
                - `datetime`: A pandas datetime object representing the date and time of the cgm measurement
                - `cgm`: A float representing the cgm value in mg/dL
        
        """
        if self.cgm_history is None:
            self.load_data()
            self.cgm_history = self._extract_cgm_history()
        return self.cgm_history
    
    
    def save_cgm_to_file(self, out_path,  compressed=False):
        """Save the cgm history to a file.
        This method extracts the cgm history, processes it to reduce file size,
        and saves it to a specified output directory. If the directory does not exist,
        it will be created. The filenames follow the pattern <study_name>_cgm_history.csv(.gz)

        The output csv format is as follows:
        - patient_id: A string representing the patient ID
        - datetime: integer representing the local timestamp in seconds since epoch
        - cgm: A integer representing the cgm value in mg/dL

        Example csv output:   
        ```
        patient_id,datetime,cgm
        10,1524150016,88
        10,1524150270,85
        10,1524150568,81
        ```

        Args:
            out_path (str): The path to the output directory where the file will be saved.
            compressed (bool, optional): If True, the output file will be compressed. Defaults to False.
        """
        if not os.path.exists(out_path):
            logger.warning(f"Output directory {out_path} does not exist. Creating it now.")
            os.makedirs(out_path)
        file_path = os.path.join(out_path, f"{self.study_name}_cgm_history")
        df_cgm = self.extract_cgm_history().copy()
        #reduce file size
        df_cgm[self.COL_NAME_DATETIME] = df_cgm[self.COL_NAME_DATETIME].astype('int64')//10**9
        df_cgm[self.COL_NAME_CGM] = df_cgm[self.COL_NAME_CGM].astype('int')
        save_to_csv(df_cgm, file_path, compressed)    
        
    def save_bolus_event_history_to_file(self, out_path, compressed=False):
        """
        Save the bolus event history to a file.
        This method extracts the bolus event history, processes it to reduce file size,
        and saves it to a specified output directory. If the directory does not exist,
        it will be created. The filenames follow the pattern <study_name>_bolus_event_history.csv(.gz)

        The output csv format is as follows:
        - patient_id: A string representing the patient ID
        - datetime: integer representing the local timestamp in seconds since epoch
        - bolus: A float representing the bolus amount in units (2 decimal places)
        - delivery_duration: integer representing the duration of the bolus delivery in seconds

        Example csv output:   
        ```
        patient_id,datetime,bolus,delivery_duration
        10,1522847353,0.1,0
        10,1522852851,7.45,0
        10,1523040411,4.449,7200
        ```

        Parameters:
            out_path (str): The path to the output directory where the file will be saved.
            compressed (bool): If True, the output file will be compressed. Default is False.
        Returns:
            None
        """

        if not os.path.exists(out_path):
            logger.warning(f"Output directory {out_path} does not exist. Creating it now.")
            os.makedirs(out_path)
        file_path = os.path.join(out_path, f"{self.study_name}_bolus_event_history")
        df_bolus = self.extract_bolus_event_history().copy()
        # Reduce file size
        df_bolus[self.COL_NAME_DATETIME] = df_bolus[self.COL_NAME_DATETIME].astype('int64') // 10**9
        df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION] = df_bolus[self.COL_NAME_BOLUS_DELIVERY_DURATION].dt.total_seconds().astype('int')
        df_bolus[self.COL_NAME_BOLUS] = df_bolus[self.COL_NAME_BOLUS].round(4)
        save_to_csv(df_bolus, file_path, compressed)

    def save_basal_event_history_to_file(self, out_path, compressed=False):
        """
        Save the basal event history to a file.
        This method extracts the basal event history, processes it to reduce file size,
        and saves it to a specified output directory. If the directory does not exist,
        it will be created. The filenames follow the pattern <study_name>_basal_event_history.csv(.gz) 

        The output format is as follows: csv file with the following columns:
        - patient_id: A string representing the patient ID
        - datetime: integer representing the local timestamp in seconds since epoch
        - basal_rate: A float representing the basal rate in units per hour

        Example csv output:   
        ```
        patient_id,datetime,basal_rate
        10,1522846361,2.0
        10,1522846661,0.0
        10,1522872700,1.0
        ```
        
        Parameters:
            out_path (str): The path to the output directory where the file will be saved.
            compressed (bool): If True, the output file will be compressed. Default is False.
        Returns:
            None
        """

        if not os.path.exists(out_path):
            logger.warning(f"Output directory {out_path} does not exist. Creating it now.")
            os.makedirs(out_path)
        file_path = os.path.join(out_path, f"{self.study_name}_basal_event_history")
        df_basal = self.extract_basal_event_history().copy()
        # Reduce file size
        df_basal[self.COL_NAME_DATETIME] = df_basal[self.COL_NAME_DATETIME].astype('int64') // 10**9
        df_basal[self.COL_NAME_BASAL_RATE] = df_basal[self.COL_NAME_BASAL_RATE].round(4)

        save_to_csv(df_basal, file_path, compressed)