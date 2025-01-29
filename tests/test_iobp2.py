import pandas as pd
from studies import IOBP2    

def test_extract_event_history(tmp_path):
    # create test data using temporary tmp_path fixture directory providede by pytest
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
    
    # Expected results
    expected_result_bolus = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:03:30 AM', '01/01/2023 1:10:00 PM', '01/01/2023 11:57:00 PM',
                     '01/01/2023 9:58:15 AM', '01/01/2023 11:02:45 AM', '01/02/2023 12:07:00 PM','01/02/2023 4:07:00 PM',
                     '01/01/2023 10:10:00 AM', '01/01/2023 2:19:50 PM','01/02/2023 6:25:00 PM','01/02/2023 8:05:00 PM'],),
        'bolus': [10.5, 15.8, 10.1,
                  8.6, 11.4, 9.9, 8.2,
                  6.5, 7.3, 8.8, 7.3],

        'delivery_duration': pd.to_timedelta(['5 minutes', '5 minutes', '5 minutes', 
                              '5 minutes', '5 minutes', '5 minutes', '5 minutes', 
                              '5 minutes', '5 minutes','5 minutes','5 minutes']),  
    })

    expected_result_cgm = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:08:30 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:02:00 AM',
                     '01/01/2023 10:03:15 AM', '01/01/2023 11:07:45 AM', '01/02/2023 12:12:00 PM','01/02/2023 4:12:00 PM',
                     '01/01/2023 10:15:00 AM', '01/01/2023 2:24:50 PM','01/02/2023 6:30:00 PM','01/02/2023 8:10:00 PM'],),
        
        'cgm': [100.0, 110.0, 105.0,
                120.0, 130.0, 140.0, 105.0,
                150.0, 160.0, 170.0, 155.0],               
    })
    #save the test data to a file
    (tmp_path / "Data Tables").mkdir()
    mock_data.to_csv(tmp_path / "Data Tables" / "IOBP2DeviceiLet.txt", sep='|', index=False)

    #load the data
    study = IOBP2(study_path=tmp_path)
    study.load_data()

    #extract
    result_bolus = study.extract_bolus_event_history()
    result_cgm = study.extract_cgm_history()
    
    #validate
    pd.testing.assert_frame_equal(result_bolus, expected_result_bolus)
    pd.testing.assert_frame_equal(result_cgm, expected_result_cgm)