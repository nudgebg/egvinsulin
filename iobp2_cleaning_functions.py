import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import warnings
import time
warnings.filterwarnings("ignore")
from studies.iobp2 import IOBP2StudyData

import pathlib

current_dir = os.path.dirname(__file__)
path = os.path.join(current_dir, 'studies', 'IOBP2 RCT Public Dataset')

study = IOBP2StudyData(study_name='IOBP2', study_path=path)
study.load_data()
bolus_history = study.extract_bolus_event_history()
basal_history = study.extract_basal_event_history()
cgm_history = study.extract_cgm_history()

def bolus_transform(bolus_data):
    #start data from midnight
    bolus_data = bolus_data.sort_values(by='datetime').reset_index(drop=True)
    #round to the nearest 5 minute value so timestamps that are close become duplicates (2:32:35 and 2:36:05 would both become 2:35:00)
    #this allows us to handle duplicates before needing to align data
    bolus_data['datetime'] = bolus_data['datetime'].dt.round("5min")
    #data aligns on unix time
    bolus_data['UnixTime'] = [int(time.mktime(bolus_data.datetime[x].timetuple())) for x in bolus_data.index]
    #create a new dataset of 5 minute time series data starting at midnight based on the data available
    start_date = bolus_data['datetime'].iloc[0].date()
    end_date = bolus_data['datetime'].iloc[-1].date() + timedelta(days=1)
    bolus_from_mid = pd.DataFrame(columns=['datetime_adj'])
    bolus_from_mid['datetime_adj'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
    bolus_from_mid['UnixTime'] = [int(time.mktime(bolus_from_mid.datetime_adj[x].timetuple())) for x in bolus_from_mid.index]
    bolus_from_mid = bolus_from_mid.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
    #sum boluses if there is a duplicate time (happens when two or more boluses are announces <5 minutes apart)
    bolus_data = bolus_data.groupby('UnixTime').agg({'bolus':'sum'})
    
    #merge new midnight aligned times with bolus data
    bolus_merged = pd.merge_asof(bolus_from_mid, bolus_data, on="UnixTime",direction="nearest",tolerance=149)

    bolus_data = bolus_merged.filter(items=['patient_id','datetime_adj','bolus'])
    bolus_data = bolus_data.rename(columns={"datetime_adj": "datetime",
                                        }) 
    
    #extended bolus handling: duration must be a timedelta for this to work
    extended_boluses = bolus_data[bolus_data.delivery_duration > timedelta(minutes=5)]
    #determine how many 5 minute steps the bolus is extended for and round to the nearst whole number step
    extended_boluses['Duration_steps'] = extended_boluses['Duration_minutes']/5
    extended_boluses['Duration_steps'] = extended_boluses['Duration_steps'].round()
    #extend the bolus out assumming an equal amount of delivery for each time step            
    for ext in extended_boluses.index:
        #devide the bolus by the number of time steps it is extended by
        bolus_parts = extended_boluses.bolus[ext]/extended_boluses.Duration_steps[ext]
        #replace bolus info with extended data
        bolus_data.bolus.loc[ext:ext+int(extended_boluses.Duration_steps[ext])] = bolus_parts
                        
    #fill nans with 0
    bolus_data = bolus_data.fillna(0)
    bolus_data.patient_id = bolus_data.patient_id.ffill()

    return bolus_data

def cgm_transform(cgm_data):
    #start data from midnight
    cgm_data = cgm_data.sort_values(by='datetime').reset_index(drop=True)
    cgm_data['datetime'] = cgm_data['datetime'].dt.round("5min")
    cgm_data['UnixTime'] = [int(time.mktime(cgm_data.datetime[x].timetuple())) for x in cgm_data.index]

    start_date = cgm_data['datetime'].iloc[0].date()
    end_date = cgm_data['datetime'].iloc[-1].date() + timedelta(days=1)
    
    cgm_from_mid = pd.DataFrame(columns=['datetime_adj'])
    cgm_from_mid['datetime_adj'] = pd.date_range(start = start_date, end = end_date, freq="5min").values

    cgm_from_mid['UnixTime'] = [int(time.mktime(cgm_from_mid.datetime_adj[x].timetuple())) for x in cgm_from_mid.index]
    cgm_from_mid = cgm_from_mid.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
    cgm_data = cgm_data.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')

    #merge new time with cgm data
    cgm_merged = pd.merge_asof(cgm_from_mid, cgm_data, on="UnixTime",direction="nearest",tolerance=149)

    cgm_data = cgm_merged.filter(items=['patient_id','datetime_adj','cgm'])
    cgm_data = cgm_data.rename(columns={"datetime_adj": "datetime",
                                        }) 
    cgm_data.patient_id = cgm_data.patient_id.ffill()
   
    return cgm_data

def basal_transform(basal_data):
    #start data from midnight
    basal_data = basal_data.sort_values(by='datetime').reset_index(drop=True)
    basal_data['datetime'] = basal_data['datetime'].dt.round("5min")
    basal_data['UnixTime'] = [int(time.mktime(basal_data.datetime[x].timetuple())) for x in basal_data.index]

    start_date = basal_data['datetime'].iloc[0].date()
    end_date = basal_data['datetime'].iloc[-1].date() + timedelta(days=1)
    
    basal_from_mid = pd.DataFrame(columns=['datetime_adj'])
    basal_from_mid['datetime_adj'] = pd.date_range(start = start_date, end = end_date, freq="5min").values

    basal_from_mid['UnixTime'] = [int(time.mktime(basal_from_mid.datetime_adj[x].timetuple())) for x in basal_from_mid.index]
    basal_from_mid = basal_from_mid.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
    #keep last basal rate if there is a duplicate time
    basal_data = basal_data.drop_duplicates(subset='UnixTime',keep='last')
    #merge new time with basal data
    basal_merged = pd.merge_asof(basal_from_mid, basal_data, on="UnixTime",direction="nearest",tolerance=149)

    basal_data = basal_merged.filter(items=['patient_id','datetime_adj','basal_rate'])
    basal_data = basal_data.rename(columns={"datetime_adj": "datetime",
                                        }) 

    #convert basal rate to 5 minute deliveries
    basal_data['basal_delivery'] = basal_data.basal_rate/12
    #forward fill basal values until next new value
    basal_data.basal_delivery = basal_data.basal_delivery.ffill()
    basal_data.patient_id = basal_data.patient_id.ffill()

    return basal_data

#transform data 
cgm_data = cgm_history.groupby('patient_id').apply(cgm_transform).reset_index(drop=True)
bolus_data = bolus_history.groupby('patient_id').apply(bolus_transform).reset_index(drop=True)
basal_data = basal_history.groupby('patient_id').apply(basal_transform).reset_index(drop=True)

