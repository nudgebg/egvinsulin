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

CARBS_SCHEMA = DataFrameSchema({
    "patient_id": Column(pa.String, nullable=False),
    "datetime": Column(pa.DateTime, nullable=False),
    "carbs": Column(pa.Float, nullable=False, checks=[Check.gt(0), Check.le(400)]),
}, strict=True)


class StudyDataset:
    """
    Abstract base class for clinical diabetes datasets with CGM, bolus, basal, and age data.

    Subclasses implement four abstract methods:
    - `_extract_bolus_event_history`: Return bolus events as a DataFrame.
    - `_extract_basal_event_history`: Return basal rate events as a DataFrame.
    - `_extract_cgm_history`: Return CGM measurements as a DataFrame.
    - `_extract_age_data`: Return patient age at enrollment as a DataFrame.

    Public properties (`bolus`, `basal`, `cgm`, `age`) validate output against pandera schemas
    and cache results via `cached_property`. Do not override them; override the private
    `_extract_*` methods instead.

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
    COL_NAME_CARBS = 'carbs'

    _raw_attrs = ()  # subclasses declare raw file cache attribute names here

    def __init__(self, study_path, study_name, subset=False):
        self.study_path = study_path
        self.study_name = study_name
        self.subset = subset

    def unload_raw(self):
        """Free raw file caches from memory.

        Call this after all needed data types have been extracted to release the memory
        used by raw file DataFrames. Derived outputs (bolus, basal, cgm, age) are kept.
        Raw attributes to clear are declared by subclasses in `_raw_attrs`.
        """
        for attr in self._raw_attrs:
            self.__dict__.pop(attr, None)

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

    def _extract_carb_history(self):
        """(Abstract) Extract carbohydrate meal entries. Implement in subclasses."""
        raise NotImplementedError("Subclasses should implement the _extract_carb_history method")

    @property
    def bolus(self):
        """Bolus event history as a validated, cached DataFrame.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                bolus (float, units), delivery_duration (timedelta).
                Standard boluses have delivery_duration of 0 seconds.
        """
        df = self._extract_bolus_event_history()
        BOLUS_SCHEMA.validate(df, lazy=True)
        return df
    
    @property
    def basal(self):
        """Basal rate event history as a validated, cached DataFrame.

        Notes:
            - Zero basal rates (pump suspends) must be included.
            - Rates are active until the next event.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                basal_rate (float, units/hour).
        """
        df = self._extract_basal_event_history()
        BASAL_SCHEMA.validate(df, lazy=True)
        return df

    @property
    def cgm(self):
        """CGM measurements as a validated, cached DataFrame.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                cgm (float, mg/dL).
        """
        df = self._extract_cgm_history()
        CGM_SCHEMA.validate(df, lazy=True)
        return df
    
    @property
    def age(self):
        """Patient age at enrollment as a validated, cached DataFrame.

        Returns:
            pd.DataFrame: Columns: patient_id (str), age (int, 0–120).
        """
        df = self._extract_age_data()
        AGE_SCHEMA.validate(df, lazy=True)
        return df

    @property
    def carbs(self):
        """Carbohydrate meal entries as a validated DataFrame.

        Returns:
            pd.DataFrame: Columns: patient_id (str), datetime (datetime64),
                carbs (float, grams, 0–400]. Only entries with carbs > 0 are included.
        """
        df = self._extract_carb_history()
        CARBS_SCHEMA.validate(df, lazy=True)
        return df
