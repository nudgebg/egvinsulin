from cleaning_functions import bolus_transform, basal_transform, cgm_transform
import pandas as pd

#general test of the transform functions - basal, bolus, and cgm

#create mock cleaned data
cleaned_bolus = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:03:30 AM', '01/01/2023 1:10:00 PM', '01/01/2023 11:50:00 PM',
                     '01/01/2023 9:58:15 AM', '01/01/2023 11:02:45 AM', '01/02/2023 12:07:00 PM','01/02/2023 4:07:00 PM',
                     '01/01/2023 10:10:00 AM', '01/01/2023 2:19:50 PM','01/02/2023 6:25:00 PM','01/02/2023 8:05:00 PM'],),
        'bolus': [10.5, 15.8, 10.1,
                  8.6, 11.4, 9.9, 8.2,
                  6.5, 7.3, 8.8, 7.3],

        'delivery_duration': pd.to_timedelta(['5 minutes', '30 minutes', '115 minutes', #extended bolus judt before midight
                              '5 minutes', '75 minutes', '5 minutes', '15 minutes', #extended bolus that overlaps another bolus
                              '5 minutes', '8 minutes','5 minutes','6 minutes']), #extended boluses just over 5 minutes 
    })

cleaned_basal = pd.DataFrame({
        'patient_id' : ['1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],

        'datetime' : pd.to_datetime(['01/01/2023 8:00:00 AM', '01/01/2023 12:30:00 PM',
                     '01/01/2023 9:00:00 AM', '01/03/2023 4:00:00 PM', #large gap in basal announcements
                     '01/01/2023 10:13:33 AM', '01/01/2023 2:19:22 PM','01/02/2023 6:12:30 PM','01/02/2023 8:07:00 PM']), #irregular times

        'basal_rate' : [1.3, 2,
                        0.7, 1.5,
                        0.1, 4, 0.75, 0.2]
        
    })

cleaned_cgm = pd.DataFrame({
        'patient_id': ['1', '1', '1', '2', '2', '2', '2', '3', '3', '3', '3'],
        
        'datetime': pd.to_datetime(['01/01/2023 10:08:30 AM', '01/01/2023 1:15:00 PM', '01/02/2023 12:02:00 AM', #irregular times to test time rounding and alignment
                     '01/01/2023 10:03:15 AM', '01/01/2023 11:07:45 AM', '01/02/2023 12:12:00 PM','01/02/2023 4:12:00 PM',
                     '01/01/2023 10:15:00 AM', '01/01/2023 2:24:50 PM','01/02/2023 6:30:00 PM','01/02/2023 8:10:00 PM'],),
        
        'cgm': [100.0, 110.0, 105.0,
                120.0, 130.0, 140.0, 105.0,
                150.0, 160.0, 170.0, 155.0],               
    })

#test transform function
tranformed_cgm_data = cleaned_cgm.groupby('patient_id').apply(cgm_transform).reset_index(drop=True)
transformed_bolus_data = cleaned_bolus.groupby('patient_id').apply(bolus_transform).reset_index(drop=True)
transformed_basal_data = cleaned_basal.groupby('patient_id').apply(basal_transform).reset_index(drop=True)

print(tranformed_cgm_data)
