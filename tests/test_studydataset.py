# File: test_studydataset.py
# Author Jan Wrede
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
import pytest
import pandas as pd
from datetime import datetime, timedelta
from studies.studydataset import validate_bolus_output_dataframe, validate_basal_output_dataframe, validate_cgm_output_dataframe


# Mock functions to be decorated
@validate_bolus_output_dataframe
def mock_extract_bolus_event_history(df):
    return df

@validate_basal_output_dataframe
def mock_extract_basal_event_history(df):
    return df

@validate_cgm_output_dataframe
def mock_extract_cgm_history(df):
    return df

# Bolus validation tests
def test_validate_bolus_output_dataframe_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(ValueError, match="DataFrame should have a 'patient_id' column of type string"):
        mock_extract_bolus_event_history(df)

def test_validate_bolus_output_dataframe_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(ValueError, match="DataFrame should have a 'datetime' column of type pandas datetime"):
        mock_extract_bolus_event_history(df)

def test_validate_bolus_output_dataframe_wrong_bolus_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': ['1.0'], 'delivery_duration': [timedelta(minutes=60)]})
    with pytest.raises(ValueError, match="DataFrame should have a 'bolus' column of type float"):
        mock_extract_bolus_event_history(df)

def test_validate_bolus_output_dataframe_wrong_delivery_duration_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': ['60 minutes']})
    with pytest.raises(ValueError, match="DataFrame should have a 'delivery_duration' column of type timedelta"):
        mock_extract_bolus_event_history(df)

def test_validate_bolus_output_dataframe_column_name_spelling():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_dur': [timedelta(minutes=60)]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate'"):
        mock_extract_bolus_event_history(df)

def test_validate_bolus_output_dataframe_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)]})
    assert mock_extract_bolus_event_history(df).equals(df)

def test_validate_bolus_output_dataframe_additional_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'bolus': [1.0], 'delivery_duration': [timedelta(minutes=60)], 'extra_column': [1]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate'"):
        mock_extract_bolus_event_history(df)

# Basal validation tests
def test_validate_basal_output_dataframe_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'basal_rate': [1.0]})
    with pytest.raises(ValueError, match="DataFrame should have a 'patient_id' column of type string"):
        mock_extract_basal_event_history(df)

def test_validate_basal_output_dataframe_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'basal_rate': [1.0]})
    with pytest.raises(ValueError, match="DataFrame should have a 'datetime' column of type pandas datetime"):
        mock_extract_basal_event_history(df)

def test_validate_basal_output_dataframe_wrong_basal_rate_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_rate': ['1.0']})
    with pytest.raises(ValueError, match="DataFrame should have a 'basal_rate' column of numeric type"):
        mock_extract_basal_event_history(df)

def test_validate_basal_output_dataframe_column_name_spelling():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_ratee': [1.0]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate'"):
        mock_extract_basal_event_history(df)

def test_validate_basal_output_dataframe_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_rate': [1.0]})
    assert mock_extract_basal_event_history(df).equals(df)

def test_validate_basal_output_dataframe_additional_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'basal_rate': [1.0], 'extra_column': [1]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'basal_rate'"):
        mock_extract_basal_event_history(df)

# CGM validation tests
def test_validate_cgm_output_dataframe_wrong_patient_datatype():
    df = pd.DataFrame({'patient_id': [1], 'datetime': [datetime.now()], 'cgm': [100.0]})
    with pytest.raises(ValueError, match="DataFrame should have a 'patient_id' column of type string"):
        mock_extract_cgm_history(df)

def test_validate_cgm_output_dataframe_wrong_datetime_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': ['2023-01-01'], 'cgm': [100.0]})
    with pytest.raises(ValueError, match="DataFrame should have a 'datetime' column of type pandas datetime"):
        mock_extract_cgm_history(df)

def test_validate_cgm_output_dataframe_wrong_cgm_datatype():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgm': ['100.0']})
    with pytest.raises(ValueError, match="DataFrame should have a 'cgm' column of numeric type"):
        mock_extract_cgm_history(df)

def test_validate_cgm_output_dataframe_column_name_spelling():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgmm': [100.0]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'cgm' but has"):
        mock_extract_cgm_history(df)

def test_validate_cgm_output_dataframe_happy_case():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgm': [100.0]})
    assert mock_extract_cgm_history(df).equals(df)

def test_validate_cgm_output_dataframe_additional_column():
    df = pd.DataFrame({'patient_id': ['1'], 'datetime': [datetime.now()], 'cgm': [100.0], 'extra_column': [1]})
    with pytest.raises(ValueError, match="DataFrame should have columns 'patient_id', 'datetime' and 'cgm' but has"):
        mock_extract_cgm_history(df)

if __name__ == "__main__":
    pytest.main()