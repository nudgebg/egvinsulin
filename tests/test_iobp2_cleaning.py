import pytest
import pandas as pd
import pathlib
import shutil
#import rootpath
#rootpath.append()
from cleaning_functions import IOBP2_cleaning
#from iobp2_extract_history_test import test_extract_event_history

def test_IOBP2_cleaning(clean_data_path='tests/'):
    # Mock data from test_extract_event_history
    mock_data = pd.DataFrame({
        'PtID': [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3],
        'DeviceDtTm': ['01/01/2023 10:08:30 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:02:00 AM',
                     '01/01/2023 10:03:15 AM', '01/01/2023 11:07:45 AM', '01/02/2023 12:12:00 PM','01/02/2023 4:12:00 PM',
                     '01/01/2023 10:15:00 AM', '01/01/2023 2:24:50 PM','01/02/2023 6:30:00 PM','01/02/2023 8:10:00 PM'],
        'BolusDelivPrev': [10.0, 11.2, 0.0,
                  8.5, 11.1, 9.0, 0.0,
                  6.3, 7.2, 8.1, 0.0],
        'MealBolusDelivPrev': [0.0, 4.0, 10.0,
                                0.0, 0.0, 0.0, 8.0,
                                0.0, 0.0, 0.0, 7.0],
        'BasalDelivPrev': [0.5, 0.6, 0.1,
                       0.1, 0.3, 0.9, 0.2,
                       0.2, 0.1, 0.7, 0.3],
        'CGMVal': [100, 110, 105,
                120, 130, 140, 105,
                150, 160, 170, 155],
    })
    expected_TDDs = pd.DataFrame({
        'patient_id': ['1','1', '2', '2', '3', '3'],
        
        'date': pd.to_datetime(['01/01/2023', '01/02/2023',
                     '01/01/2023', '01/02/2023',
                     '01/01/2023', '01/02/2023'],),
        
        'TDD': [36.4, 0.0,
                20, 18.1,
                13.8, 16.1],               
    })
    #create csv of mock data and save to folder structure and filename to mimic original data
    pathlib.Path('tests/Data Tables').mkdir(parents=True, exist_ok=True)
    mock_data.to_csv('tests/Data Tables/IOBP2DeviceiLet.txt', sep='|',index=False)
    
    # Call the function
    cgm_data, bolus_data = IOBP2_cleaning('tests', clean_data_path)

    # Verify the content of the files if necessary
    cgm_df = pd.read_csv('tests/CleanedData/IOBP2_cleaned_egv.csv')
    bolus_df = pd.read_csv('tests/CleanedData/IOBP2_cleaned_bolus.csv')

    assert not cgm_df.empty
    assert not bolus_df.empty
    
    #calculate sum of bolus on each unique patient_id and unique date 
    #convert datetime column to date column
    bolus_df['datetime'] = pd.to_datetime(bolus_df['datetime'])
    bolus_df['TDD'] = bolus_df.groupby(['patient_id', bolus_df['datetime'].dt.date])['bolus'].transform('sum')
    bolus_df['date'] = bolus_df['datetime'].dt.date
    #convert patient_id to string - reading in csv to get final data results in the strings being converted to ints
    bolus_df['patient_id'] = bolus_df['patient_id'].astype(str)
    #drop duplicates to get unique patient_id and date with TDD
    result_TDDs = bolus_df.drop_duplicates(subset=['TDD'], keep='first')
    result_TDDs = result_TDDs.filter(items=['patient_id', 'date', 'TDD']).reset_index(drop=True)
    #check if result_TDDs is equal to expected_TDDs
    expected_TDDs['date'] = expected_TDDs['date'].dt.date
    pd.testing.assert_frame_equal(result_TDDs, expected_TDDs)
if __name__ == "__main__":
    pytest.main()
