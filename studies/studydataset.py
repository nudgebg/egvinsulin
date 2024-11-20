import pandas as pd

def validate_bolus_output_dataframe(func):
    def wrapper(*args, **kwargs):
        df = func(*args, **kwargs)
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Output should be a pandas DataFrame")
        required_columns = ['patient_id', 'datetime', 'bolus', 'delivery_duration']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame should have columns {required_columns} but has {df.columns}")
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
        if not all(col in df.columns for col in required_columns):
            raise ValueError("DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate'")
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
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame should have columns {required_columns} but has {df.columns}")
        if not pd.api.types.is_object_dtype(df['patient_id'].dtype) or not all(isinstance(item, str) for item in df['patient_id']):
            raise ValueError("DataFrame should have a 'patient_id' column of type string")
        if not pd.api.types.is_numeric_dtype(df['cgm'].dtype):
            raise ValueError(f"DataFrame should have a 'cgm' column of numeric type but is {df['cgm'].dtype}")
        return df
    return wrapper


class StudyDataset:
    """
    The `StudyDataset` class is designed to handle and validate data related to a medical study.
    It has a member variable `df` which is a pandas DataFrame that holds the data.
    The class is initialized with a `study_path` which is the path to the study directory

    The class has several methods:

    - `load_data`: This method is meant to be overridden by subclasses to load data into the `df` DataFrame.
      It has a decorator `validate_load_data` which checks if the DataFrame `df` is not None after loading the data.

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

    def __init__(self, study_path, study_name):
        self.study_path = study_path
        self.study_name = study_name
        self.bolus_event_history = None
        self.basal_event_history = None
        self.cgm_history = None
        self.data_loaded = False

    def _load_data(self):
        raise NotImplementedError("Subclasses should implement the _load_data method")
    def _extract_bolus_event_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_bolus_event_history method")
    def _extract_basal_event_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_basal_event_history method")
    def _extract_cgm_history(self):
        raise NotImplementedError("Subclasses should implement the _extract_cgm_history method")
    
    def load_data(self):
        if not self.data_loaded:
            self._load_data()
            self.data_loaded = True

    @validate_bolus_output_dataframe
    def extract_bolus_event_history(self):
        """ Extract bolus event history from the dataset. This method does
        do type checking on the output data and should not be overriden
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