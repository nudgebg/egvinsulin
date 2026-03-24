# File: test_studydataset.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pytest
import pandas as pd
from datetime import datetime, timedelta
from babelbetes.studies import StudyDataset
from babelbetes.studies.studydataset import BOLUS_SCHEMA, BASAL_SCHEMA, CGM_SCHEMA, AGE_SCHEMA
from pandera.errors import SchemaErrors


def validate_bolus(df):
    return BOLUS_SCHEMA.validate(df, lazy=True)

def validate_basal(df):
    return BASAL_SCHEMA.validate(df, lazy=True)

def validate_cgm(df):
    return CGM_SCHEMA.validate(df, lazy=True)

def validate_age(df):
    return AGE_SCHEMA.validate(df, lazy=True)


# --- Bolus ---

def test_bolus_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_wrong_bolus_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': ['1.0'], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_wrong_delivery_duration_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': ['60 minutes']})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_extra_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)], 'extra': [1]})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_missing_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0]})
    with pytest.raises(SchemaErrors):
        validate_bolus(df)

def test_bolus_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': pd.to_datetime(['2023-01-01']), 'bolus': [1.0], 'delivery_duration': pd.to_timedelta([0], unit='s')})
    result = validate_bolus(df)
    assert result is not None


# --- Basal ---

def test_basal_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'basal_rate': [1.0]})
    with pytest.raises(SchemaErrors):
        validate_basal(df)

def test_basal_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'basal_rate': [1.0]})
    with pytest.raises(SchemaErrors):
        validate_basal(df)

def test_basal_wrong_basal_rate_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_rate': ['1.0']})
    with pytest.raises(SchemaErrors):
        validate_basal(df)

def test_basal_extra_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_rate': [1.0], 'extra': [1]})
    with pytest.raises(SchemaErrors):
        validate_basal(df)

def test_basal_missing_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()]})
    with pytest.raises(SchemaErrors):
        validate_basal(df)

def test_basal_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': pd.to_datetime(['2023-01-01']), 'basal_rate': [1.0]})
    result = validate_basal(df)
    assert result is not None


# --- CGM ---

def test_cgm_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'cgm': [100.0]})
    with pytest.raises(SchemaErrors):
        validate_cgm(df)

def test_cgm_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'cgm': [100.0]})
    with pytest.raises(SchemaErrors):
        validate_cgm(df)

def test_cgm_wrong_cgm_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgm': ['100.0']})
    with pytest.raises(SchemaErrors):
        validate_cgm(df)

def test_cgm_extra_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgm': [100.0], 'extra': [1]})
    with pytest.raises(SchemaErrors):
        validate_cgm(df)

def test_cgm_missing_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()]})
    with pytest.raises(SchemaErrors):
        validate_cgm(df)

def test_cgm_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': pd.to_datetime(['2023-01-01']), 'cgm': [100.0]})
    result = validate_cgm(df)
    assert result is not None


# --- Age ---

def test_age_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'age': [25]})
    with pytest.raises(SchemaErrors):
        validate_age(df)

def test_age_wrong_age_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'age': ['25']})
    with pytest.raises(SchemaErrors):
        validate_age(df)

def test_age_out_of_range():
    df = pd.DataFrame({'patient_id': ['1'], 'age': [150]})
    with pytest.raises(SchemaErrors):
        validate_age(df)

def test_age_missing_column():
    df = pd.DataFrame({'patient_id': ['1']})
    with pytest.raises(SchemaErrors):
        validate_age(df)

def test_age_extra_column():
    df = pd.DataFrame({'patient_id': ['1'], 'age': [25], 'extra': [1]})
    with pytest.raises(SchemaErrors):
        validate_age(df)

def test_age_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'age': [25]})
    result = validate_age(df)
    assert result is not None


# --- unload_raw ---

def test_unload_raw_clears_declared_attrs():
    class MockStudy(StudyDataset):
        _raw_attrs = ('_pump',)

        def _load_data(self, subset=False): pass
        def _extract_bolus_event_history(self): pass
        def _extract_basal_event_history(self): pass
        def _extract_cgm_history(self): pass
        def _extract_age_data(self): pass

    study = MockStudy('', 'Mock')
    study._pump = pd.DataFrame({'a': [1]})
    assert '_pump' in study.__dict__
    study.unload_raw()
    assert '_pump' not in study.__dict__

def test_unload_raw_is_safe_when_nothing_cached():
    class MockStudy(StudyDataset):
        _raw_attrs = ('_pump',)

        def _load_data(self, subset=False): pass
        def _extract_bolus_event_history(self): pass
        def _extract_basal_event_history(self): pass
        def _extract_cgm_history(self): pass
        def _extract_age_data(self): pass

    study = MockStudy('', 'Mock')
    study.unload_raw()  # should not raise


if __name__ == "__main__":
    pytest.main()
