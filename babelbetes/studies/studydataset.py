# File: studydataset.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pandas as pd
import os
from babelbetes.src.logger import Logger
logger = Logger.get_logger(__name__)

def validate_bolus_output_dataframe(func):
    """
    A decorator to validate the output of a function that returns a pandas DataFrame. It is used to validate the output of the `extract_bolus_event_history` method in the `StudyDataset` class.
    Subclasses should implement the `_extract_bolus_event_history` method which is called by the `extract_bolus_event_history` method to use this decorator.
    
    The DataFrame must have the following  (see output format in the `extract_bolus_event_history` method):
    - 'patient_id': of type string
    - 'datetime': of type pandas datetime
    - 'bolus': of type float
    - 'delivery_duration': of type pandas timedelta

    Raises:
        TypeError: If the output is not a pandas DataFrame.
        ValueError: If the DataFrame does not have the required columns.
        ValueError: If the 'datetime' column is not of type pandas datetime  (datetime64[ns]).
        ValueError: If the 'patient_id' column is not of type string.
        ValueError: If the 'bolus' column is not of type float.
        ValueError: If the 'delivery_duration' column is not of type pandas timedelta.
    
    Args:
        func (callable): The function to be decorated.
    
    Returns:
        function (function): The wrapped function with validation applied to its output.
    """
    def wrapper(*args, **kwargs):
        df = func(*args, **kwargs)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Output should be a pandas DataFrame")
        required_columns = ['patient_id', 'datetime', 'bolus', 'delivery_duration']
        if set(df.columns) != set(required_columns):
            raise ValueError(f"DataFrame should have columns 'patient_id', 'datetime', 'bolus' and 'delivery_duration' but has {df.columns}")
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
    """
    A decorator to validate the output of a function to ensure it is a pandas DataFrame with specific required columns and data types. 
    
    It is used to validate the output of the `extract_basal_event_history` method in the `StudyDataset` class.
    Subclasses should implement the `_extract_basal_event_history` method which is called by the `extract_basal_event_history` method to use this decorator.

    The DataFrame must have the following columns (see output format in the `extract_basal_event_history` method):
    - 'patient_id': of type string
    - 'datetime': of type pandas datetime (datetime64[ns]).
    - 'basal_rate': of numeric type

    Raises:
        TypeError: If the output is not a pandas DataFrame.
        ValueError: If the DataFrame does not have the required columns.
        ValueError: If the 'datetime' column is not of type pandas datetime (datetime64[ns]).
        ValueError: If the 'patient_id' column is not of type string.
        ValueError: If the 'basal_rate' column is not of numeric type.

    Args:
        func (function): The function whose output will be validated.

    Returns:
        function (function): The wrapped function with validation applied to its output.
    """
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
    """
    A decorator to validate the output of a function to ensure it is a pandas DataFrame with specific required columns and data types. 
    
    It is used to validate the output of the `extract_cgm_history` method in the `StudyDataset` class.
    Subclasses should implement the `_extract_cgm_history` method which is called by the `extract_cgm_history` method to use this decorator.

    The DataFrame must have the following columns (see output format in the `extract_cgm_history` method):
    - 'patient_id': of type string
    - 'datetime': of type pandas datetime (datetime64[ns]).
    - 'cgm': of numeric type

    Raises:
        TypeError: If the output is not a pandas DataFrame.
        ValueError: If the DataFrame does not have the required columns.
        ValueError: If the 'datetime' column is not of type pandas datetime (datetime64[ns]).
        ValueError: If the 'patient_id' column is not of type string.   
        ValueError: If the 'cgm' column is not of numeric type.

    Args:
        func (function): The function whose output will be validated.
    
    Returns:
        function (function): The wrapped function with validation applied to its output.
    """
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

class StudyDataset:
    """
    The `StudyDataset` class is designed to represent a clinical diabetes dataset with continuous glucose monitoring and insulin delivery data in the form of boluses and basal rates.
    By subclassing and implementing the required methods, it can be used to extract continuous glucose monitoring (CGM) data, bolus event history, and basal event history from a dataset.

    The following private methods need to be implemented by subclasses:
    - `_load_data`: This method should load the data from the study directory. 
    - `_extract_bolus_event_history`: This method should extract the bolus event history from the dataset. 
    - `_extract_basal_event_history`: This method should extract the basal event history from the dataset.
    - `_extract_cgm_history`: This method should extract the CGM measurements from the dataset.

    **Output Validation**: While subclasses should implement the private methods, the extraction methods should not be overridden. Instead, the output of these methods is validated using decorators.
    To extract the data, the `extract_bolus_event_history`, `extract_basal_event_history`, and `extract_cgm_history` methods should be called. These methods will call the private methods and validate the output.

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
        self._bolus_event_history = None
        self._basal_event_history = None
        self._cgm_history = None
        self._data_loaded = False

    def _load_data(self, subset: bool = False):
        """(Abstract) Load the study data into memory.
        This method is called by the `load_data` method which ensures that the data is loaded only once and cached for subsequent use. This ensures that we load the data only once. Additionally, keeping the raw data in memory allows for easier debugging and inspection of the data.
        """
        raise NotImplementedError("Subclasses should implement the _load_data method")
    
    def _extract_bolus_event_history(self):
        """(Abstract) Extracts the bolus event history from the dataset. This is a abstract method that should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses should implement the _extract_bolus_event_history method")
    
    def _extract_basal_event_history(self):
        """(Abstract) Extracts the basal event history from the dataset. This is a abstract method that should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses should implement the _extract_basal_event_history method")
    
    def _extract_cgm_history(self):
        """(Abstract) Extracts the continuous glucose monitoring (CGM) measurements from the dataset. This is a abstract method that should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses should implement the _extract_cgm_history method")
    
    def load_data(self, subset=False):
        """Load and cache the study data into memory by calling the `_load_data` method which should be implemented by subclasses. 

        This method is automatically called when calling one of the extraction methods. However, it can also be called up-front. After data was loaded the member variable `data_loaded` is set to True and subsequent calls to this method will not reload the data.

        Notes:  
         - **Don't override this:** This method does do type checking on the output data and should not be overriden by subclasses. Instead, subclasses should implement the `_extract_bolus_event_history` method.
         
        Args:
            subset (bool, optional): Should only load a small subset of the data for testing purposes. Defaults to False.
        """
        if not self._data_loaded:
            self._load_data(subset=subset)
            self._data_loaded = True
    
    @validate_bolus_output_dataframe
    def extract_bolus_event_history(self):
        """ Extract bolus event history from the dataset, perform type checking, and cache the result.
        
        Notes:   
        For standard boluses the delivery duration is 0 seconds, for extended boluses, these are the duration of the extended delivery.

        Warning:  
        **Don't override this:** This method does do type checking on the output data and should not be overriden by subclasses. Instead, subclasses should implement the `_extract_bolus_event_history` method.

         
        Returns:  
            bolus_events (pd.DataFrame): The bolus event history with the following columns:

                - `patient_id` (String): the unique patient ID
                - `datetime` (pandas.datetime): the date and time of the bolus event
                - `bolus` (float): the bolus amount in units
                - `delivery_duration` (pandas.timedelta): the duration of the bolus delivery: For standard boluses the delivery duration is 0 seconds, for extended boluses, these are the duration of the extended delivery.

        """
        if self._bolus_event_history is None:
            self.load_data()
            self._bolus_event_history = self._extract_bolus_event_history()
        return self._bolus_event_history
    
    @validate_basal_output_dataframe
    def extract_basal_event_history(self):
        """ Uses `_extract_basal_event_history` to extract the basal event history, perform type checking, and cache the result.
        
        Warning:
            **Don't override this:** This method does do type checking on the output data and should not be overriden by subclasses. Instead, subclasses should implement the `_extract_basal_event_history` method.

        Notes:
         - Include zero basal rates: The assumption is that basal rates continue until a new rate is set. Therefore, zero basal rates should be included in the output.
         - Account for suspend and temporary basal events.
         - Ensure the datetime object is a pandas datetime object and is of type datetime64[ns], otherwise the validation will fail e.g. by using df.
        
        Returns:  
            basal_event_history (pd.DataFrame): The basal event history with the following columns:    
            
             - `patient_id` (String): the unique patient ID
             - `datetime` (pandas.datetime): the date and time of the basal event
             - `basal_rate` (float): the basal rate in units per hour. Make sure to include zero basal rates as they mark basal suspends.
        """
        if self._basal_event_history is None:
            self.load_data()
            self._basal_event_history = self._extract_basal_event_history()
        return self._basal_event_history
    
    @validate_cgm_output_dataframe
    def extract_cgm_history(self):
        """ Extract cgm measurements from the dataset, perform type checking, and cache the result.
        
        Warning:
            **Don't override this!** This method does do type checking on the output data and should not be overriden by subclasses. Instead, subclasses should implement the `_extract_cgm_history` method.
        
        Returns:
            cgm_measurements (pd.DataFrame): A DataFrame containing the cgm measurements. The DataFrame should have the following columns:

                - `patient_id`: A string representing the patient ID
                - `datetime`: A pandas datetime object representing the date and time of the cgm measurement
                - `cgm`: A float representing the cgm value in mg/dL
        
        """
        if self._cgm_history is None:
            self.load_data()
            self._cgm_history = self._extract_cgm_history()
        return self._cgm_history