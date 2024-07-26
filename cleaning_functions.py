#collection of cleaning functions for insulin and egv data
import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import warnings
import time
warnings.filterwarnings("ignore")
from studies.iobp2 import IOBP2StudyData
import pathlib
def datCnv(src):
    return pd.to_datetime(src)
from studies.iobp2 import IOBP2StudyData
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
        bolus_data.bolus.loc[ext:ext+int(extended_boluses.Duration_steps[ext])] = bolus_parts
                        
    #fill nans with 0
    bolus_data.patient_id = bolus_data.patient_id.ffill()
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

def FLAIR_cleaning(filepath_data, clean_data_path, data_val=True):

    filename = os.path.join(filepath_data,'Data Tables', 'FLAIRDevicePump.txt')
    InsulinData = pd.read_csv(filename, sep="|", low_memory = False)

    filename = os.path.join(filepath_data,'Data Tables', 'FLAIRDeviceCGM.txt')
    CGM = pd.read_csv(filename, sep="|" , low_memory = False)

    filename = os.path.join(filepath_data, 'Data Tables', 'PtRoster.txt')
    roster = pd.read_csv(filename, sep="|", low_memory = False)

    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','TrtGroup'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['TrtGroup'] = roster['TrtGroup']
    PatientInfo['Age'] = roster['AgeAsofEnrollDt']
    #initialize final data frames
    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            bolus_pt = df_insulin[df_insulin.PtID == id]
            if len(bolus_pt)>0:
                patient_cgm = df_cgm[df_cgm.PtID == id]

                #round to nearest 5 minutes - helps combine data that will be slotted into the same datetime values when combining data
                bolus_pt['DateTime'] = bolus_pt['DateTime'].dt.round("5min")
                #add unix time column to combine on 'nearest'
                bolus_pt['UnixTime'] = [int(time.mktime(bolus_pt.DateTime[x].timetuple())) for x in bolus_pt.index]
                bolus_pt['Date'] = [bolus_pt['DateTime'][x].date() for x in bolus_pt.index]
                bolus_pt = bolus_pt.sort_values(by='DateTime').reset_index(drop=True)
                bolus_pt = bolus_pt.filter(items=['DateTime','Date','UnixTime','BasalRt','BolusDeliv', 'ExtendBolusDuration'])
                #use for creating complete 5 minute time steps from midnight                    
                start_date = bolus_pt.DateTime.iloc[0].date()
                end_date = bolus_pt.DateTime.iloc[-1].date() + timedelta(days=1)

                bolus_pt.BolusDeliv = bolus_pt.BolusDeliv.fillna(0)
                #convert basal rate from U/hr to 5 minute delivery values
                bolus_pt.BasalRt = bolus_pt.BasalRt/12
                bolus_pt.BasalRt = bolus_pt.BasalRt.ffill()
                bolus_pt = bolus_pt.dropna(subset='BasalRt')
                #take care of duplicate time values by combining boluses and taking last delivered basal rate at that time                
                dups = bolus_pt[bolus_pt.duplicated(subset='UnixTime', keep=False)]
                utime = dups.UnixTime.unique()
                count = 0
                replace_data = pd.DataFrame(index=range(len(utime)),columns=dups.columns)
                for u in utime:
                    dup_data = dups[dups.UnixTime==u]
                    replace_data['DateTime'][count] = dup_data['DateTime'].iloc[0]
                    replace_data['UnixTime'][count] = u
                    replace_data['BasalRt'][count] = dup_data['BasalRt'].iloc[-1]
                    replace_data['BolusDeliv'][count] = dup_data['BolusDeliv'].sum()
                    if any(dup_data['ExtendBolusDuration'].notnull()):
                        replace_data['ExtendBolusDuration'][count] = dup_data[dup_data['ExtendBolusDuration'].notnull()].ExtendBolusDuration.iloc[-1]

                    count += 1

                bolus_pt = bolus_pt.drop_duplicates(subset=['UnixTime'],keep=False)
                #recombine fixed duplicates back into original data
                patient_deliv = pd.concat([bolus_pt,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
                #creates the 5min timeseries data
                data_new_time = pd.DataFrame(columns=['DateTime_keep'])
                data_new_time['DateTime_keep'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
                data_new_time['UnixTime'] = [int(time.mktime(data_new_time.DateTime_keep[x].timetuple())) for x in data_new_time.index]
                data_new_time = data_new_time.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')

                patient_deliv.UnixTime = patient_deliv.UnixTime.astype(int)
                #merge insulin data into the 5min timeseries data frame
                insulin_merged = pd.merge_asof(data_new_time, patient_deliv, on="UnixTime",direction="nearest",tolerance=149)

                #process cgm data to be in the format needed to merge
                patient_cgm['UnixTime'] = [int(time.mktime(patient_cgm.DateTime[x].timetuple())) for x in patient_cgm.index]
                patient_cgm = patient_cgm.sort_values(by='DateTime').reset_index(drop=True)
                patient_cgm = patient_cgm.filter(items=['DateTime','UnixTime','CGM'])
                patient_cgm = patient_cgm.drop_duplicates(subset=['UnixTime']).reset_index(drop=True)
                patient_cgm = patient_cgm.dropna(subset=['UnixTime']).sort_values(by='UnixTime')
                #merge cgm and insulin together
                data_merged = pd.merge_asof(insulin_merged, patient_cgm, on="UnixTime",direction="nearest",tolerance=149)
                data_merged = data_merged.filter(items=['DateTime_keep','BasalRt','BolusDeliv','ExtendBolusDuration','CGM'])
                #forward fill basal rates and replace NaNs in bolus to 0 for easy addition into single column
                data_merged.BasalRt = data_merged.BasalRt.ffill()
                data_merged.BolusDeliv = data_merged.BolusDeliv.fillna(0)
                #process extended boluses 
                extended_boluses = data_merged[data_merged.ExtendBolusDuration.notna()]
                if len(extended_boluses) > 0:
                    extended_boluses['Duration'] = [datetime.strptime(extended_boluses.ExtendBolusDuration[t],"%H:%M:%S") for t in extended_boluses.index.values]
                    extended_boluses['Duration_minutes'] = [timedelta(hours=extended_boluses['Duration'][t].hour, minutes=extended_boluses['Duration'][t].minute, seconds=extended_boluses['Duration'][t].second).total_seconds()/60 for t in extended_boluses.index]
                    extended_boluses['Duration_steps'] = extended_boluses['Duration_minutes']/5
                    extended_boluses['Duration_steps'] = extended_boluses['Duration_steps'].round()

                    for ext in extended_boluses.index:
                        bolus_parts = extended_boluses.BolusDeliv[ext]/extended_boluses.Duration_steps[ext]
                        data_merged.BolusDeliv.loc[ext:ext+int(extended_boluses.Duration_steps[ext])] = bolus_parts
                #filter out unwanted data and convert column names                
                data_merged = data_merged.filter(items=['DateTime_keep','BasalRt','BolusDeliv','CGM'])
                data_merged['PtID'] = id
                data_merged = data_merged.rename(columns={
                                                "DateTime_keep": "DateTime",
                                                "CGM": "egv",
                                                "BolusDeliv": "BolusDelivery",
                                                "BasalRt": "BasalDelivery",
                                                })
                #remove insulin data on the days we have no delivery data available. This keeps the full time series complete, but has NaNs in insulin delivery
                data_merged['Date'] = [data_merged['DateTime'][x].date() for x in data_merged.index]
                for d in data_merged['Date'].unique():
                    check = bolus_pt[bolus_pt.Date==d]
                    index_values = data_merged[data_merged.Date==d].index.values
                    if len(check)==0:
                        data_merged.BasalDelivery.loc[index_values] = np.nan
                        data_merged.BolusDelivery.loc[index_values] = np.nan

                data_merged['Insulin'] = data_merged.BasalDelivery + data_merged.BolusDelivery
                data_merged.Insulin = data_merged.Insulin.replace({np.inf: np.nan})
                data_merged.egv = data_merged.egv.replace({'HIGH': 400, 'High': 400, 'high': 400,
                                                                'LOW': 40, 'Low': 40, 'low': 40})
                #merge individual cleaned data into one large file
                cleaned_data = pd.concat([cleaned_data,data_merged])
                #create a patient summary file
                if len(data_merged)>0:
                    subj_info['DaysOfData'] = np.nan
                    subj_info['AVG_CGM'] = np.nan
                    subj_info['STD_CGM'] = np.nan
                    subj_info['CGM_Availability'] = np.nan
                    subj_info['eA1C'] = np.nan
                    subj_info['TIR'] = np.nan
                    subj_info['TDD'] = np.nan
                    #validate data to make sure all time is 5 minutes apart (except daylight savings) and all CGM values are valid 
                    if data_val == True:
                        subj_info['5minCheck'] = np.nan
                        subj_info['5minCheck_max'] = np.nan
                        subj_info['ValidCGMCheck'] = np.nan
                        data_merged['TimeBetween'] = data_merged.DateTime.diff()
                        data_merged['TimeBetween'] = [data_merged['TimeBetween'][x].total_seconds()/60 for x in data_merged.index]
                        subj_info['5minCheck'] = len(data_merged[data_merged.TimeBetween>5])
                        subj_info['5minCheck_max'] = data_merged.TimeBetween.max()
                        subj_info['ValidCGMCheck'] = len(data_merged[(data_merged.egv<40) & (data_merged.egv>400)])

                    subj_info['DaysOfData'][0] = np.round(len(data_merged)/288,2)
                    subj_info['AVG_CGM'][0] = np.round(data_merged.egv.mean(),2)
                    subj_info['STD_CGM'][0] = np.round(data_merged.egv.std(),2)
                    subj_info['CGM_Availability'][0] = np.round(100 * len(data_merged[data_merged.egv>0])/len(data_merged),2)
                    subj_info['eA1C'][0] = np.round((46.7 + data_merged.egv.mean())/28.7,2)
                    subj_info['TIR'][0] = np.round(100 * len(data_merged[(data_merged.egv>=70) & (data_merged.egv<=180)])/len(data_merged[data_merged.egv>0]),2)
                    subj_info['TDD'][0] = np.round(data_merged.Insulin.sum()/subj_info['DaysOfData'][0],2)

                    pt_data = subj_info.filter(items=['PtID','StartDate','TrtGroup','DaysOfData','AVG_CGM','STD_CGM','CGM_Availability',
                                                    'eA1C','TIR','TDD','5minCheck','ValidCGMCheck','5minCheck_max'])
                    patient_data = pd.concat([patient_data,pt_data])

        except:
            pass
    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    save_data_as(cleaned_data,'CSV',clean_data_path + 'CleanedData/FLAIR_cleaned_egvinsulin')
    save_data_as(patient_data,'CSV',clean_data_path + "CleanedData/FLAIR_patient_data")

    return cleaned_data,patient_data 

def DCLP5_cleaning(filepath_data,clean_data_path,data_val = True):
    #load insulin related csvs
    df_bolus = pd.read_csv(os.path.join(filepath_data, 'DCLP5TandemBolus_Completed_Combined_b.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType'],parse_dates=[2])

    df_basal = pd.read_csv(os.path.join(filepath_data, 'DCLP5TandemBASALRATECHG_b.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate'])
    df_basal = parse_flair_dates(df_basal,'DataDtTm')
    #load cgm data
    df_cgm = pd.read_csv(os.path.join(filepath_data, 'DexcomClarityCGM.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CGM'])
    df_cgm = parse_flair_dates(df_cgm,'DataDtTm')

    filename = os.path.join(filepath_data, 'PtRoster.txt')
    roster = pd.read_csv(filename, sep="|")

    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','TrtGroup'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['TrtGroup'] = roster['trtGroup']

    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            patient_deliv = df_basal[df_basal.PtID == id]
            patient_cgm = df_cgm[df_cgm.PtID == id]
            patient_bolus = df_bolus[df_bolus.PtID == id]

            patient_deliv = patient_deliv.sort_values(by='DateTime').reset_index(drop=True)
            patient_cgm = patient_cgm.sort_values(by='DateTime').reset_index(drop=True)
            patient_bolus = patient_bolus.sort_values(by='DateTime').reset_index(drop=True)

            patient_deliv = patient_deliv[patient_deliv.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)
            patient_cgm = patient_cgm[patient_cgm.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)
            patient_bolus = patient_bolus[patient_bolus.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)

            patient_cgm['DateTime'] = patient_cgm['DateTime'].dt.round("5min")
            patient_deliv['DateTime'] = patient_deliv['DateTime'].dt.round("5min")
            patient_bolus['DateTime'] = patient_bolus['DateTime'].dt.round("5min")

            patient_cgm['UnixTime'] = [int(time.mktime(patient_cgm.DateTime[x].timetuple())) for x in patient_cgm.index]
            patient_deliv['UnixTime'] = [int(time.mktime(patient_deliv.DateTime[x].timetuple())) for x in patient_deliv.index]
            patient_bolus['UnixTime'] = [int(time.mktime(patient_bolus.DateTime[x].timetuple())) for x in patient_bolus.index]

            start_date = patient_deliv.DateTime.iloc[0].date()
            end_date = patient_deliv.DateTime.iloc[-1].date() + timedelta(days=1)

            data_new_time = pd.DataFrame(columns=['DateTime_keep'])
            data_new_time['DateTime_keep'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
            data_new_time['UnixTime'] = [int(time.mktime(data_new_time.DateTime_keep[x].timetuple())) for x in data_new_time.index]
            data_new_time = data_new_time.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')

            #remove duplicate basal rates
            dups = patient_deliv[patient_deliv.duplicated(subset='UnixTime', keep=False)]
            utime = dups.UnixTime.unique()
            count = 0
            replace_data = pd.DataFrame(index=range(len(utime)),columns=dups.columns)
            for u in utime:
                dup_data = dups[dups.UnixTime==u]
                replace_data['DateTime'][count] = dup_data['DateTime'].iloc[0]
                replace_data['UnixTime'][count] = u
                replace_data['CommandedBasalRate'][count] = dup_data['CommandedBasalRate'].iloc[-1]
                count += 1

            patient_deliv = patient_deliv.drop_duplicates(subset=['UnixTime'],keep=False)
            patient_deliv.CommandedBasalRate = patient_deliv.CommandedBasalRate/12
            patient_deliv_dup_rem = pd.concat([patient_deliv,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
            patient_deliv_dup_rem.UnixTime = patient_deliv_dup_rem.UnixTime.astype(int)

            insulin_merged = pd.merge_asof(data_new_time, patient_deliv, on="UnixTime",direction="nearest",tolerance=149)
            insulin_merged.CommandedBasalRate = insulin_merged.CommandedBasalRate.ffill()

            dups = patient_bolus[patient_bolus.duplicated(subset='UnixTime', keep=False)]
            utime = dups.UnixTime.unique()
            count = 0
            replace_data = pd.DataFrame(index=range(len(utime)),columns=dups.columns)
            for u in utime:
                dup_data = dups[dups.UnixTime==u]
                replace_data['DateTime'][count] = dup_data['DateTime'].iloc[0]
                replace_data['UnixTime'][count] = u
                replace_data['BolusAmount'][count] = dup_data['BolusAmount'].sum()
                count += 1

            patient_bolus = patient_bolus.drop_duplicates(subset=['UnixTime'],keep=False)
            patient_bolus_dup_rem = pd.concat([patient_bolus,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
            patient_bolus_dup_rem.UnixTime = patient_bolus_dup_rem.UnixTime.astype(int)
            patient_bolus_dup_rem.BolusAmount = patient_bolus_dup_rem.BolusAmount.fillna(0)

            delivery_merged = pd.merge_asof(insulin_merged, patient_bolus_dup_rem, on="UnixTime",direction="nearest",tolerance=149)
            delivery_merged = delivery_merged.filter(items=['DateTime_keep','UnixTime','BolusAmount','CommandedBasalRate','BolusType'])

            patient_cgm = patient_cgm.sort_values(by='UnixTime').reset_index(drop=True)
            data_merged = pd.merge_asof(delivery_merged, patient_cgm, on="UnixTime",direction="nearest",tolerance=149)
            data_merged = data_merged.filter(items=['DateTime_keep','UnixTime','BolusAmount','CommandedBasalRate','BolusType','CGM'])

            data_merged = data_merged.rename(columns={
                                            "DateTime_keep": "DateTime",
                                            "CGM": "egv",
                                            "BolusDeliv": "BolusDelivery",
                                            "BasalRt": "BasalDelivery",
                                          })
            data_merged.BolusDelivery = data_merged.BolusDelivery.astype(float)
            data_merged.BolusDelivery = data_merged.BolusDelivery.fillna(0)
            #process extended bolus data. assumes that 50% is delivered up front and 50% is extended for 2 hours. There is no data for how patients programmed the boluses
            extended_index = data_merged[data_merged.BolusType=='Extended'].index.values
            for e in extended_index:
                data_merged.BolusDelivery[e] = data_merged.BolusDelivery[e]*0.5
                data_merged.BolusDelivery.loc[e+1:e+24] = data_merged.BolusDelivery.loc[e+1:e+24] + (data_merged.BolusDelivery[e]*0.5)/24

            data_merged.egv = data_merged.egv.replace({'HIGH': 400, 'High': 400, 'high': 400,
                                                             'LOW': 40, 'Low': 40, 'low': 40})

            data_merged['Date'] = [data_merged['DateTime'][x].date() for x in data_merged.index]
            patient_deliv['Date'] = [patient_deliv['DateTime'][x].date() for x in patient_deliv.index]
            for d in data_merged['Date'].unique():
                check = patient_deliv[patient_deliv.Date==d]
                index_values = data_merged[data_merged.Date==d].index.values
                if len(check)==0:
                    data_merged.BasalDelivery.loc[index_values] = np.nan
                    data_merged.BolusDelivery.loc[index_values] = np.nan
            
            data_merged['Insulin'] = data_merged.BasalDelivery + data_merged.BolusDelivery
            data_merged['PtID'] = id
            data_merged = data_merged.filter(items=['PtID','DateTime','UnixTime','BasalDelivery','BolusDelivery','egv','Insulin','BolusType'])
            data_merged = data_merged.sort_values(by='DateTime')
            cleaned_data = pd.concat([cleaned_data,data_merged])
            if len(data_merged)>0:
                subj_info['DaysOfData'] = np.nan
                subj_info['AVG_CGM'] = np.nan
                subj_info['STD_CGM'] = np.nan
                subj_info['CGM_Availability'] = np.nan
                subj_info['eA1C'] = np.nan
                subj_info['TIR'] = np.nan
                subj_info['TDD'] = np.nan
                if data_val == True:
                    subj_info['5minCheck'] = np.nan
                    subj_info['5minCheck_max'] = np.nan
                    subj_info['ValidCGMCheck'] = np.nan
                    data_merged['TimeBetween'] = data_merged.DateTime.diff()
                    data_merged['TimeBetween'] = [data_merged['TimeBetween'][x].total_seconds()/60 for x in data_merged.index]
                    subj_info['5minCheck'] = len(data_merged[data_merged.TimeBetween>5])
                    subj_info['5minCheck_max'] = data_merged.TimeBetween.max()
                    subj_info['ValidCGMCheck'] = len(data_merged[(data_merged.egv<40) & (data_merged.egv>400)])

                subj_info['DaysOfData'][0] = np.round(len(data_merged)/288,2)
                subj_info['AVG_CGM'][0] = np.round(data_merged.egv.mean(),2)
                subj_info['STD_CGM'][0] = np.round(data_merged.egv.std(),2)
                subj_info['CGM_Availability'][0] = np.round(100 * len(data_merged[data_merged.egv>0])/len(data_merged),2)
                subj_info['eA1C'][0] = np.round((46.7 + data_merged.egv.mean())/28.7,2)
                subj_info['TIR'][0] = np.round(100 * len(data_merged[(data_merged.egv>=70) & (data_merged.egv<=180)])/len(data_merged[data_merged.egv>0]),2)
                subj_info['TDD'][0] = np.round(data_merged.Insulin.sum()/subj_info['DaysOfData'][0],2)

                pt_data = subj_info.filter(items=['PtID','StartDate','TrtGroup','DaysOfData','AVG_CGM','STD_CGM','CGM_Availability',
                                                  'eA1C','TIR','TDD','5minCheck','ValidCGMCheck','5minCheck_max'])
                patient_data = pd.concat([patient_data,pt_data])
                
        except:
            pass
            
    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    save_data_as(cleaned_data,'CSV',clean_data_path + 'CleanedData/DCLP5_cleaned_egvinsulin')
    save_data_as(patient_data,'CSV',clean_data_path + "CleanedData/DCLP5_patient_data")

    return cleaned_data,patient_data

def DCLP3_cleaning(filepath_data,clean_data_path,data_val = True):
    #load insulin related csvs
    df_bolus = pd.read_csv(os.path.join(filepath_data, 'Data Files', 'Pump_BolusDelivered.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'BolusAmount', 'BolusType'],parse_dates=[2])

    df_basal = pd.read_csv(os.path.join(filepath_data, 'Data Files', 'Pump_BasalRateChange.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CommandedBasalRate'],parse_dates=[2])
    #load cgm data
    df_cgm = pd.read_csv(os.path.join(filepath_data, 'Data Files', 'Pump_CGMGlucoseValue.txt'), sep="|", low_memory=False,
                             usecols=['RecID', 'PtID', 'DataDtTm', 'CGMValue'],parse_dates=[2])

    filename = os.path.join(filepath_data,'Data Files', 'PtRoster_a.txt')
    roster = pd.read_csv(filename, sep="|", low_memory = False)

    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','TrtGroup'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['TrtGroup'] = roster['trtGroup']

    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            patient_deliv = df_basal[df_basal.PtID == id]
            patient_cgm = df_cgm[df_cgm.PtID == id]
            patient_bolus = df_bolus[df_bolus.PtID == id]

            patient_deliv = patient_deliv.sort_values(by='DateTime').reset_index(drop=True)
            patient_cgm = patient_cgm.sort_values(by='DateTime').reset_index(drop=True)
            patient_bolus = patient_bolus.sort_values(by='DateTime').reset_index(drop=True)

            patient_deliv = patient_deliv[patient_deliv.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)
            patient_cgm = patient_cgm[patient_cgm.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)
            patient_bolus = patient_bolus[patient_bolus.DateTime >= subj_info.StartDate.iloc[0]].reset_index(drop=True)

            patient_cgm['DateTime'] = patient_cgm['DateTime'].dt.round("5min")
            patient_deliv['DateTime'] = patient_deliv['DateTime'].dt.round("5min")
            patient_bolus['DateTime'] = patient_bolus['DateTime'].dt.round("5min")

            patient_cgm['UnixTime'] = [int(time.mktime(patient_cgm.DateTime[x].timetuple())) for x in patient_cgm.index]
            patient_deliv['UnixTime'] = [int(time.mktime(patient_deliv.DateTime[x].timetuple())) for x in patient_deliv.index]
            patient_bolus['UnixTime'] = [int(time.mktime(patient_bolus.DateTime[x].timetuple())) for x in patient_bolus.index]

            start_date = patient_deliv.DateTime.iloc[0].date()
            end_date = patient_deliv.DateTime.iloc[-1].date() + timedelta(days=1)

            data_new_time = pd.DataFrame(columns=['DateTime_keep'])
            data_new_time['DateTime_keep'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
            data_new_time['UnixTime'] = [int(time.mktime(data_new_time.DateTime_keep[x].timetuple())) for x in data_new_time.index]
            data_new_time = data_new_time.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')

            #remove duplicate basal rates
            dups = patient_deliv[patient_deliv.duplicated(subset='UnixTime', keep=False)]
            utime = dups.UnixTime.unique()
            count = 0
            replace_data = pd.DataFrame(index=range(len(utime)),columns=dups.columns)
            for u in utime:
                dup_data = dups[dups.UnixTime==u]
                replace_data['DateTime'][count] = dup_data['DateTime'].iloc[0]
                replace_data['UnixTime'][count] = u
                replace_data['CommandedBasalRate'][count] = dup_data['CommandedBasalRate'].iloc[-1]
                count += 1

            patient_deliv = patient_deliv.drop_duplicates(subset=['UnixTime'],keep=False)
            patient_deliv.CommandedBasalRate = patient_deliv.CommandedBasalRate/12
            patient_deliv_dup_rem = pd.concat([patient_deliv,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
            patient_deliv_dup_rem.UnixTime = patient_deliv_dup_rem.UnixTime.astype(int)

            insulin_merged = pd.merge_asof(data_new_time, patient_deliv, on="UnixTime",direction="nearest",tolerance=149)
            insulin_merged.CommandedBasalRate = insulin_merged.CommandedBasalRate.ffill()

            dups = patient_bolus[patient_bolus.duplicated(subset='UnixTime', keep=False)]
            utime = dups.UnixTime.unique()
            count = 0
            replace_data = pd.DataFrame(index=range(len(utime)),columns=dups.columns)
            for u in utime:
                dup_data = dups[dups.UnixTime==u]
                replace_data['DateTime'][count] = dup_data['DateTime'].iloc[0]
                replace_data['UnixTime'][count] = u
                replace_data['BolusAmount'][count] = dup_data['BolusAmount'].sum()
                count += 1

            patient_bolus = patient_bolus.drop_duplicates(subset=['UnixTime'],keep=False)
            patient_bolus_dup_rem = pd.concat([patient_bolus,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
            patient_bolus_dup_rem.UnixTime = patient_bolus_dup_rem.UnixTime.astype(int)
            patient_bolus_dup_rem.BolusAmount = patient_bolus_dup_rem.BolusAmount.fillna(0)

            delivery_merged = pd.merge_asof(insulin_merged, patient_bolus_dup_rem, on="UnixTime",direction="nearest",tolerance=149)
            delivery_merged = delivery_merged.filter(items=['DateTime_keep','UnixTime','BolusAmount','CommandedBasalRate','BolusType'])

            patient_cgm = patient_cgm.sort_values(by='UnixTime').reset_index(drop=True)
            data_merged = pd.merge_asof(delivery_merged, patient_cgm, on="UnixTime",direction="nearest",tolerance=149)
            data_merged = data_merged.filter(items=['DateTime_keep','UnixTime','BolusAmount','CommandedBasalRate','BolusType','CGMValue'])

            data_merged = data_merged.rename(columns={
                                            "CGMValue": "egv",
                                            "BolusAmount": "BolusDelivery",
                                            "CommandedBasalRate": "BasalDelivery",
                                            "DateTime_keep": "DateTime",
                                            })
            data_merged.BolusDelivery = data_merged.BolusDelivery.astype(float)
            data_merged.BolusDelivery = data_merged.BolusDelivery.fillna(0)

            extended_index = data_merged[data_merged.BolusType=='Extended'].index.values
            for e in extended_index:
                data_merged.BolusDelivery[e] = data_merged.BolusDelivery[e]*0.5
                data_merged.BolusDelivery.loc[e+1:e+24] = data_merged.BolusDelivery.loc[e+1:e+24] + (data_merged.BolusDelivery[e]*0.5)/24

            data_merged.egv = data_merged.egv.replace({'HIGH': 400, 'High': 400, 'high': 400,
                                                                'LOW': 40, 'Low': 40, 'low': 40})

            data_merged['Date'] = [data_merged['DateTime'][x].date() for x in data_merged.index]
            patient_deliv['Date'] = [patient_deliv['DateTime'][x].date() for x in patient_deliv.index]
            for d in data_merged['Date'].unique():
                check = patient_deliv[patient_deliv.Date==d]
                index_values = data_merged[data_merged.Date==d].index.values
                if len(check)==0:
                    data_merged.BasalDelivery.loc[index_values] = np.nan
                    data_merged.BolusDelivery.loc[index_values] = np.nan
            
            data_merged['insulin'] = data_merged.BasalDelivery + data_merged.BolusDelivery
            data_merged['PtID'] = id
            data_merged = data_merged.filter(items=['PtID','DateTime','UnixTime','BasalDelivery','BolusDelivery','egv','insulin','BolusType'])
            data_merged = data_merged.sort_values(by='DateTime')
            cleaned_data = pd.concat([cleaned_data,data_merged])
            if len(data_merged)>0:
                subj_info['DaysOfData'] = np.nan
                subj_info['AVG_CGM'] = np.nan
                subj_info['STD_CGM'] = np.nan
                subj_info['CGM_Availability'] = np.nan
                subj_info['eA1C'] = np.nan
                subj_info['TIR'] = np.nan
                subj_info['TDD'] = np.nan
                if data_val == True:
                    subj_info['5minCheck'] = np.nan
                    subj_info['5minCheck_max'] = np.nan
                    subj_info['ValidCGMCheck'] = np.nan
                    data_merged['TimeBetween'] = data_merged.DateTime.diff()
                    data_merged['TimeBetween'] = [data_merged['TimeBetween'][x].total_seconds()/60 for x in data_merged.index]
                    subj_info['5minCheck'] = len(data_merged[data_merged.TimeBetween>5])
                    subj_info['5minCheck_max'] = data_merged.TimeBetween.max()
                    subj_info['ValidCGMCheck'] = len(data_merged[(data_merged.egv<40) & (data_merged.egv>400)])

                subj_info['DaysOfData'][0] = np.round(len(data_merged)/288,2)
                subj_info['AVG_CGM'][0] = np.round(data_merged.egv.mean(),2)
                subj_info['STD_CGM'][0] = np.round(data_merged.egv.std(),2)
                subj_info['CGM_Availability'][0] = np.round(100 * len(data_merged[data_merged.egv>0])/len(data_merged),2)
                subj_info['eA1C'][0] = np.round((46.7 + data_merged.egv.mean())/28.7,2)
                subj_info['TIR'][0] = np.round(100 * len(data_merged[(data_merged.egv>=70) & (data_merged.egv<=180)])/len(data_merged[data_merged.egv>0]),2)
                subj_info['TDD'][0] = np.round(data_merged.insulin.sum()/subj_info['DaysOfData'][0],2)

                pt_data = subj_info.filter(items=['PtID','StartDate','TrtGroup','DaysOfData','AVG_CGM','STD_CGM','CGM_Availability',
                                                    'eA1C','TIR','TDD','5minCheck','ValidCGMCheck','5minCheck_max'])
                patient_data = pd.concat([patient_data,pt_data])
                
        except:
            pass
            
    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    save_data_as(cleaned_data,'CSV',clean_data_path + 'CleanedData/DCLP3_cleaned_egvinsulin')
    save_data_as(patient_data,'CSV',clean_data_path + "CleanedData/DCLP3_patient_data")

    return cleaned_data,patient_data

def IOBP2_cleaning(filepath,clean_data_path):
    study = IOBP2StudyData(study_name='IOBP2', study_path=filepath)
    study.load_data()
    bolus_history = study.extract_bolus_event_history()
    cgm_history = study.extract_cgm_history()

    cgm_data = cgm_history.groupby('patient_id').apply(cgm_transform).reset_index(drop=True)
    bolus_data = bolus_history.groupby('patient_id').apply(bolus_transform).reset_index(drop=True)

    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    cgm_data.to_csv(clean_data_path + "CleanedData/IOBP2_cleaned_egv.csv",index=False)
    bolus_data.to_csv(clean_data_path + "CleanedData/IOBP2_cleaned_bolus.csv",index=False)

    return cgm_data,bolus_data

##########-------------- Run Functions for Testing 
# print('starting IOBP2')
# filepath = '/Users/rachelbrandt/egvinsulin_1/studies/IOBP2 RCT Public Dataset'
# cleaned_data_path = '/Users/rachelbrandt/egvinsulin_1/' #location where you want cleaned data to be stored

# cleaned_data,patient_data =  FLAIR_cleaning(filepath,cleaned_data_path)

# print('starting DCLP5')
# filepath = '/Users/rachelbrandt/Downloads/DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53/'
# cleaned_data_path = '/Users/rachelbrandt/egvinsulin/' #location where you want cleaned data to be stored

# cleaned_data,patient_data =  DCLP5_cleaning(filepath,cleaned_data_path)

# filepath = '/Users/rachelbrandt/Downloads/DCLP3 Public Dataset - Release 3 - 2022-08-04/Data Files/'
# cleaned_data_path = '/Users/rachelbrandt/egvinsulin/' #location where you want cleaned data to be stored

# cleaned_data,patient_data =  DCLP3_cleaning(filepath,cleaned_data_path)
# print(patient_data)

# filepath = '/Users/rachelbrandt/Downloads/IOBP2 RCT Public Dataset/Data Tables/'
# cleaned_data_path = '/Users/rachelbrandt/egvinsulin/' #location where you want cleaned data to be stored

# cgm_data,bolus_data,basal_data =  IOBP2_cleaning(filepath,cleaned_data_path)
# print(bolus_data[bolus_data.bolus>0])