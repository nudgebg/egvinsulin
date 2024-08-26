import pandas as pd
import time 
from datetime import timedelta
import numpy as np

#functions for time alignment and transformation of basal, bolus, and cgm event data. These functions can be used for any study dataset.
def bolus_transform(bolus_data):
    """
    Transform the bolus data by aligning timestamps, handling duplicates, and extending boluses based on durations.

    Parameters:
    - bolus_data (DataFrame): The input is a bolus data dataframe containing columns 'patient_id, 'datetime', 'bolus', and 'delivery_duration'.

    Returns:
    - bolus_data (DataFrame): The transformed bolus data with aligned timestamps, duplicates removed, and extended bolus handling.
    """

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
    #keep maximum duration of the bolus - in the rare case a standard and extended are announced int the same 5 minute window, it will be treated as an extended bolus
    bolus_data = bolus_data.groupby('UnixTime').agg({'bolus':'sum','delivery_duration':'max','patient_id':'first'}).reset_index()
   
    #merge new midnight aligned times with bolus data
    bolus_merged = pd.merge_asof(bolus_from_mid, bolus_data, on="UnixTime",direction="nearest",tolerance=149)
    bolus_data = bolus_merged.filter(items=['patient_id','datetime_adj','bolus','delivery_duration'])
    bolus_data = bolus_data.rename(columns={"datetime_adj": "datetime",
                                        }) 
    #extended bolus handling: duration must be a timedelta for this to work
    extended_boluses = bolus_data[bolus_data.delivery_duration > timedelta(minutes=5)]
    #determine how many 5 minute steps the bolus is extended for and round to the nearst whole number step
    extended_boluses['Duration_minutes'] = extended_boluses['delivery_duration'].dt.total_seconds()/60
    extended_boluses['Duration_steps'] = extended_boluses['Duration_minutes']/5
    extended_boluses['Duration_steps'] = extended_boluses['Duration_steps'].round()
    #extend the bolus out assumming an equal amount of delivery for each time step            
    for ext in extended_boluses.index:
        #devide the bolus by the number of time steps it is extended by
        bolus_parts = extended_boluses.bolus[ext]/extended_boluses.Duration_steps[ext]
        #replace bolus info with extended data
        bolus_data.loc[ext:ext+int(extended_boluses.Duration_steps[ext])-1, 'bolus'] = bolus_parts
                        
    #fill nans with 0
    bolus_data.patient_id = bolus_data.patient_id.ffill()
    bolus_data.patient_id = bolus_data.patient_id.bfill()
    bolus_data = bolus_data.dropna(subset=['patient_id'])
    bolus_data.bolus = bolus_data.bolus.fillna(0)

    return bolus_data

def cgm_transform(cgm_data):
    """
    time aligns the cgm data to midnight with a 5 minute sampling rate.

    Parameters:
    - cgm_data (DataFrame): The input is a cgm data dataframe containing columns 'patient_id, 'datetime', and 'cgm'.

    Returns:
    - cgm_data (DataFrame): The transformed cgm data with aligned timestamps.
    """
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
    cgm_data.patient_id = cgm_data.patient_id.bfill()

    #replace not null values outside of 40-400 range with 40 or 400
    cgm_data.loc[cgm_data['cgm'] < 40, 'cgm'] = 40
    cgm_data.loc[cgm_data['cgm'] > 400, 'cgm'] = 400
    
    return cgm_data

def basal_transform(basal_data):
    """
    Transform the basal data by aligning timestamps and handling duplicates.

    Parameters:
    - basal_data (DataFrame): The input is a basal data dataframe containing columns 'patient_id, 'datetime', and 'basal_rate'.

    Returns:
    - basal_data (DataFrame): The transformed basal data with aligned timestamps and duplicates removed.
    """
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
    basal_data = basal_data.sort_values(by='UnixTime')
    basal_merged = pd.merge_asof(basal_from_mid, basal_data, on="UnixTime", direction="nearest", tolerance=149)

    basal_data = basal_merged.filter(items=['patient_id','datetime_adj','basal_rate'])
    basal_data = basal_data.rename(columns={"datetime_adj": "datetime",
                                        }) 

    #convert basal rate to 5 minute deliveries
    basal_data['basal_delivery'] = basal_data.basal_rate/12
    #forward fill basal values until next new value
    def durations_since_previous_valid_value(dates, values):
        """
        Calculate the durations between each date and the previous date with a valid value (non NaN).

        Parameters:
        dates (list): A list of dates.
        values (list): A list of values.

        Returns:
        list: A list of durations between each date and the previous valid date. NaN if there is no previous valid date.
        """
        last_valid_date = None
        durations = []
        for (date, value) in zip(dates, values):
            duration = np.NaN
            if last_valid_date is not None:
                duration = date - last_valid_date
            if not np.isnan(value):
                last_valid_date = date
            durations.append(duration)
        return durations

    def combine_and_forward_fill(basal_df, gap=float('inf')):
        #forward fill, but only if duration between basal values is smaller than the threshold
        durations = durations_since_previous_valid_value(basal_df['datetime'], basal_df['basal_delivery'])    
        bSignificantGap = [True if pd.notna(duration) and duration >= gap else False for duration in np.array(durations)]
        basal_df['basal_delivery'] = basal_df['basal_delivery'].where(bSignificantGap, basal_df['basal_delivery'].ffill())
        return basal_df
    
    # basal_data.basal_delivery = basal_data.basal_delivery.ffill()
    basal_data = combine_and_forward_fill(basal_data, gap=timedelta(hours=24))
    basal_data.patient_id = basal_data.patient_id.ffill()
    basal_data.patient_id = basal_data.patient_id.bfill()

    return basal_data
