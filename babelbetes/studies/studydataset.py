# File: studydataset.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
from babelbetes.src.logger import Logger
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

logger = Logger.get_logger(__name__)

BOLUS_SCHEMA = DataFrameSchema({
    "patient_id": Column(pa.String, nullable=False),
    "datetime": Column(pa.DateTime, nullable=False),
    "bolus": Column(pa.Float, nullable=False),
    "delivery_duration": Column(pa.Timedelta, nullable=False),
}, strict=True)

BASAL_SCHEMA = DataFrameSchema({
    "patient_id": Column(pa.String, nullable=False),
    "datetime": Column(pa.DateTime, nullable=False),
    "basal_rate": Column(pa.Float, nullable=False),
}, strict=True)

CGM_SCHEMA = DataFrameSchema({
    "patient_id": Column(pa.String, nullable=False),
    "datetime": Column(pa.DateTime, nullable=False),
    "cgm": Column(pa.Float, nullable=False),
}, strict=True)

AGE_SCHEMA = DataFrameSchema({
    "patient_id": Column(pa.String, nullable=False, unique=True),
    "age": Column(pa.Int, nullable=False, checks=[Check.ge(0), Check.le(120)]),
}, strict=True)

# Backward-compatible alias removed after all studies are migrated
AGE_OUTPUT_SCHEMA = AGE_SCHEMA


class StudyDataset:
    """
    Abstract base class for clinical diabetes datasets with CGM, bolus, basal, and age data.

    Subclasses implement four abstract methods:
    - `_load_data`: Load raw files from the study directory.
    - `_extract_bolus_event_history`: Return bolus events as a DataFrame.
    - `_extract_basal_event_history`: Return basal rate events as a DataFrame.
    - `_extract_cgm_history`: Return CGM measurements as a DataFrame.
    - `_extract_age_data`: Return patient age at enrollment as a DataFrame.

    Public extraction methods (`extract_bolus_event_history`, etc.) validate output against
    pandera schemas and cache results. Do not override them; override the private `_extract_*`
    methods instead.

    For memory management when processing multiple studies, declare raw file cache attributes
    in `_raw_attrs` and call `unload_raw()` after extraction is complete.
    """

    COL_NAME_PATIENT_ID = 'patient_id'
    COL_NAME_DATETIME = 'datetime'
    COL_NAME_BOLUS = 'bolus'
    COL_NAME_BASAL_RATE = 'basal_rate'
    COL_NAME_BOLUS_DELIVERY_DURATION = 'delivery_duration'
    COL_NAME_CGM = 'cgm'
    COL_NAME_AGE = 'age'

    _raw_attrs = ()  # subclasses declare raw file cache attribute names here

    def __init__(self, study_path, study_name, subset=False):
        self.study_path = study_path
        self.study_name = study_name
        self.subset = subset
        self._bolus_event_history = None
        self._basal_event_history = None
        self._cgm_history = None
        self._age_data = None
        self._data_loaded = False

    def unload_raw(self):
        """Free raw file caches from memory.

        Call this after all needed data types have been extracted to release the memory
        used by raw file DataFrames. Derived outputs (bolus, basal, cgm, age) are kept.
        Raw attributes to clear are declared by subclasses in `_raw_attrs`.
        """
        for attr in self._raw_attrs:
            self.__dict__.pop(attr, None)

    def _load_data(self, subset: bool = False):
        """(Abstract) Load raw study files into memory."""
        raise NotImplementedError("Subclasses should implement the _load_data method")

    def _extract_bolus_event_history(self):
        """(Abstract) Extract bolus events. Implement in subclasses."""
        raise NotImplementedError("Subclasses should implement the _extract_bolus_event_history method")

    def _extract_basal_event_history(self):
        """(Abstract) Extract basal rate events. Implement in subclasses."""
        raise NotImplementedError("Subclasses should implement the _extract_basal_event_history method")

    def _extract_cgm_history(self):
        """(Abstract) Extract CGM measurements. Implement in subclasses."""
        raise NotImplementedError("Subclasses should implement the _extract_cgm_history method")

    def _extract_age_data(self):
        """(Abstract) Extract patient age at enrollment. Implement in subclasses."""
        raise NotImplementedError("Subclasses should implement the _extract_age_data method")

    def load_data(self, subset=False):
        """Load and cache study data by calling `_load_data`. Idempotent.

        Called automatically by extraction methods. Can also be called up-front.

        Args:
            subset (bool): Load only a small subset for testing. Defaults to False.
        """
        if not self._data_loaded:
            self._load_data(subset=subset)
            self._data_loaded = True

    def extract_bolus_event_history(self):
        """Extract and validate bolus event history, caching the result.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                bolus (float, units), delivery_duration (timedelta).
                Standard boluses have delivery_duration of 0 seconds.
        """
        if self._bolus_event_history is None:
            self.load_data()
            df = self._extract_bolus_event_history()
            BOLUS_SCHEMA.validate(df, lazy=True)
            self._bolus_event_history = df
        return self._bolus_event_history

    def extract_basal_event_history(self):
        """Extract and validate basal event history, caching the result.

        Notes:
            - Zero basal rates (pump suspends) must be included.
            - Rates are active until the next event.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                basal_rate (float, units/hour).
        """
        if self._basal_event_history is None:
            self.load_data()
            df = self._extract_basal_event_history()
            BASAL_SCHEMA.validate(df, lazy=True)
            self._basal_event_history = df
        return self._basal_event_history

    def extract_cgm_history(self):
        """Extract and validate CGM measurements, caching the result.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                cgm (float, mg/dL).
        """
        if self._cgm_history is None:
            self.load_data()
            df = self._extract_cgm_history()
            CGM_SCHEMA.validate(df, lazy=True)
            self._cgm_history = df
        return self._cgm_history

    def extract_age_data(self):
        """Extract and validate patient age at enrollment, caching the result.

        Returns:
            pd.DataFrame: Columns: patient_id (str), age (int, 0–120).
        """
        if self._age_data is None:
            self.load_data()
            df = self._extract_age_data()
            AGE_SCHEMA.validate(df, lazy=True)
            self._age_data = df
        return self._age_data
