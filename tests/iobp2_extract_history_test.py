import pathlib
import pytest
import pandas as pd
import rootpath
rootpath.append()
from studies.iobp2 import IOBP2StudyData    

def test_extract_event_history():
    # Mock data
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
                150, 160, 170, 10.5],
    })
    #create csv of mock data and save to folder structure and filename to mimic original data
    pathlib.Path('tests/Data Tables').mkdir(parents=True, exist_ok=True)
    mock_data.to_csv('tests/Data Tables/IOBP2DeviceiLet.txt', sep='|',index=False)
    # Expected result
    expected_result_bolus = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:03:30 AM', '01/01/2023 1:10:00 PM', '01/01/2023 11:57:00 PM',
                     '01/01/2023 9:58:15 AM', '01/01/2023 11:02:45 AM', '01/02/2023 12:07:00 PM','01/02/2023 4:07:00 PM',
                     '01/01/2023 10:10:00 AM', '01/01/2023 2:19:50 PM','01/02/2023 6:25:00 PM','01/02/2023 8:05:00 PM'],),
        'bolus': [10.0, 15.2, 10.0,
                  8.5, 11.1, 9.0, 8.0,
                  6.3, 7.2, 8.1, 7.0],

        'delivery_duration': pd.to_timedelta(['5 minutes', '5 minutes', '5 minutes', 
                              '5 minutes', '5 minutes', '5 minutes', '5 minutes', 
                              '5 minutes', '5 minutes','5 minutes','5 minutes']),  
    })

    expected_result_basal = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:03:30 AM', '01/01/2023 1:10:00 PM', '01/01/2023 11:57:00 PM',
                     '01/01/2023 9:58:15 AM', '01/01/2023 11:02:45 AM', '01/02/2023 12:07:00 PM','01/02/2023 4:07:00 PM',
                     '01/01/2023 10:10:00 AM', '01/01/2023 2:19:50 PM','01/02/2023 6:25:00 PM','01/02/2023 8:05:00 PM'],),
         
        'basal_rate': [0.5*12, 0.6*12, 0.1*12,
                       0.1*12, 0.3*12, 0.9*12, 0.2*12,
                       0.2*12, 0.1*12, 0.7*12, 0.3*12],              
    })

    expected_result_cgm = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:08:30 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:02:00 AM',
                     '01/01/2023 10:03:15 AM', '01/01/2023 11:07:45 AM', '01/02/2023 12:12:00 PM','01/02/2023 4:12:00 PM',
                     '01/01/2023 10:15:00 AM', '01/01/2023 2:24:50 PM','01/02/2023 6:30:00 PM','01/02/2023 8:10:00 PM'],),
        
        'cgm': [100, 110, 105,
                120, 130, 140, 105,
                150, 160, 170, 10.5],               
    })
    
    # Call the function
    study = IOBP2StudyData(study_name='IOBP2', study_path='tests')
    study.load_data()
    #test bolus history
    result_bolus = study.extract_bolus_event_history()
    print('resulting extracted bolus event history')
    print()
    print(result_bolus)
    print()
    print('expected extracted bolus event history')
    print()
    print(expected_result_bolus)
    #test basal history
    result_basal = study.extract_basal_event_history()
    print('resulting extracted basal event history')
    print()
    print(result_basal)
    print()
    print('expected extracted basal event history')
    print()
    print(expected_result_basal)
    #test cgm history
    result_cgm = study.extract_cgm_history()
    print('resulting extracted cgm event history')
    print()
    print(result_cgm)
    print()
    print('expected extracted cgm event history')
    print()
    print(expected_result_cgm)
    
    # Assertions
    pd.testing.assert_frame_equal(result_bolus, expected_result_bolus)
    pd.testing.assert_frame_equal(result_basal, expected_result_basal)
    pd.testing.assert_frame_equal(result_cgm, expected_result_cgm)
    #delete file and folder created for test
    pathlib.Path('tests/Data Tables/IOBP2DeviceiLet.txt').unlink()
    pathlib.Path('tests/Data Tables').rmdir()
    return result_bolus, result_basal, result_cgm   #return mock data to use in cleaning function test


if __name__ == "__main__":
    # pytest.main()
    test_extract_event_history()