#collection of cleaning functions for insulin and egv data
import os
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import warnings
import time
import os
warnings.filterwarnings("ignore")

import pathlib
def datCnv(src):
    return pd.to_datetime(src)

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

    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    TDD_all = pd.DataFrame(columns=['PtID','TDD'])
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            bolus_pt = InsulinData[InsulinData.PtID == id]
            if len(bolus_pt)>0:
                patient_cgm = CGM[CGM.PtID == id]
                
                bolus_pt['DateTime'] = bolus_pt.DataDtTm.apply(datCnv)
                bolus_pt['DateTime'] = bolus_pt['DateTime'].dt.round("5min")
                bolus_pt['UnixTime'] = [int(time.mktime(bolus_pt.DateTime[x].timetuple())) for x in bolus_pt.index]
                bolus_pt['Date'] = [bolus_pt['DateTime'][x].date() for x in bolus_pt.index]
                bolus_pt = bolus_pt.sort_values(by='DateTime').reset_index(drop=True)
                bolus_pt = bolus_pt.filter(items=['DateTime','Date','UnixTime','BasalRt','BolusDeliv', 'ExtendBolusDuration'])
                                    
                start_date = bolus_pt.DateTime.iloc[0].date()
                end_date = bolus_pt.DateTime.iloc[-1].date() + timedelta(days=1)
                
                bolus_pt.BolusDeliv = bolus_pt.BolusDeliv.fillna(0)
                bolus_pt.BasalRt = bolus_pt.BasalRt/12
                bolus_pt.BasalRt = bolus_pt.BasalRt.ffill()
                bolus_pt = bolus_pt.dropna(subset='BasalRt')
                                
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
                patient_deliv = pd.concat([bolus_pt,replace_data]).sort_values(by='UnixTime').reset_index(drop=True)
                
                data_new_time = pd.DataFrame(columns=['DateTime_keep'])
                data_new_time['DateTime_keep'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
                data_new_time['UnixTime'] = [int(time.mktime(data_new_time.DateTime_keep[x].timetuple())) for x in data_new_time.index]
                data_new_time = data_new_time.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
                
                patient_deliv.UnixTime = patient_deliv.UnixTime.astype(int)
                
                insulin_merged = pd.merge_asof(data_new_time, patient_deliv, on="UnixTime",direction="nearest",tolerance=149)    
                
                patient_cgm['DateTime'] = patient_cgm.DataDtTm.apply(datCnv)
                patient_cgm['UnixTime'] = [int(time.mktime(patient_cgm.DateTime[x].timetuple())) for x in patient_cgm.index]
                patient_cgm = patient_cgm.sort_values(by='DateTime').reset_index(drop=True)
                patient_cgm = patient_cgm.filter(items=['DateTime','UnixTime','CGM'])
                patient_cgm = patient_cgm.drop_duplicates(subset=['UnixTime']).reset_index(drop=True)
                patient_cgm = patient_cgm.dropna(subset=['UnixTime']).sort_values(by='UnixTime')
                
                data_merged = pd.merge_asof(insulin_merged, patient_cgm, on="UnixTime",direction="nearest",tolerance=149)
                data_merged = data_merged.filter(items=['DateTime_keep','BasalRt','BolusDeliv','ExtendBolusDuration','CGM'])
                
                data_merged.BasalRt = data_merged.BasalRt.ffill()
                data_merged.BolusDeliv = data_merged.BolusDeliv.fillna(0)
                
                extended_boluses = data_merged[data_merged.ExtendBolusDuration.notna()]
                if len(extended_boluses) > 0:
                    extended_boluses['Duration'] = [datetime.strptime(extended_boluses.ExtendBolusDuration[t],"%H:%M:%S") for t in extended_boluses.index.values]
                    extended_boluses['Duration_minutes'] = [timedelta(hours=extended_boluses['Duration'][t].hour, minutes=extended_boluses['Duration'][t].minute, seconds=extended_boluses['Duration'][t].second).total_seconds()/60 for t in extended_boluses.index]
                    extended_boluses['Duration_steps'] = extended_boluses['Duration_minutes']/5
                    extended_boluses['Duration_steps'] = extended_boluses['Duration_steps'].round()
                
                    for ext in extended_boluses.index:
                        bolus_parts = extended_boluses.BolusDeliv[ext]/extended_boluses.Duration_steps[ext]
                        data_merged.BolusDeliv.loc[ext:ext+int(extended_boluses.Duration_steps[ext])] = bolus_parts
                                
                data_merged = data_merged.filter(items=['DateTime_keep','BasalRt','BolusDeliv','CGM'])
                data_merged['PtID'] = id
                data_merged = data_merged.rename(columns={
                                                "DateTime_keep": "DateTime",
                                                "CGM": "egv",
                                                "BolusDeliv": "BolusDelivery",
                                                "BasalRt": "BasalDelivery",
                                                }) 
                data_merged['Date'] = [data_merged['DateTime'][x].date() for x in data_merged.index]
                TDD_pt = pd.DataFrame(index=range(len(data_merged['Date'].unique())),columns=['PtID','TDD'])
                dd = 0
                for d in data_merged['Date'].unique():
                    check = bolus_pt[bolus_pt.Date==d]
                    index_values = data_merged[data_merged.Date==d].index.values
                    if len(check)==0:
                        data_merged.BasalDelivery.loc[index_values] = np.nan
                        data_merged.BolusDelivery.loc[index_values] = np.nan
                    if (data_val == True) & (len(check)!=0):
                        TDD_pt['PtID'][dd] = id
                        TDD_pt['TDD'][dd] = data_merged.BasalDelivery.loc[index_values].sum() + data_merged.BolusDelivery.loc[index_values].sum()
                        dd += 1

                TDD_all = pd.concat([TDD_all,TDD_pt])

                data_merged['Insulin'] = data_merged.BasalDelivery + data_merged.BolusDelivery
                data_merged.Insulin = data_merged.Insulin.replace({np.inf: np.nan})                
                data_merged.egv = data_merged.egv.replace({'HIGH': 400, 'High': 400, 'high': 400, 
                                                                'LOW': 40, 'Low': 40, 'low': 40})
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
    cleaned_data.to_csv(clean_data_path + "CleanedData/FLAIR_cleaned_egvinsulin.csv",index=False)
    patient_data.to_csv(clean_data_path + "CleanedData/FLAIR_patient_data.csv",index=False)
    TDD_all.to_csv(clean_data_path + "CleanedData/FLAIR_TDD_data.csv",index=False)
    
    return cleaned_data,patient_data 

def DCLP5_cleaning(filepath_data,clean_data_path,data_val = True):
    filename = os.path.join(filepath_data,'DCLP5TandemBolus_Completed_Combined_b.txt')
    Bolus = pd.read_csv(filename, sep="|", low_memory = False)

    filename = os.path.join(filepath_data, 'DCLP5TandemBASALRATECHG_b.txt')
    BasalRate = pd.read_csv(filename, sep="|" , low_memory = False)

    filename = os.path.join(filepath_data, 'DexcomClarityCGM.txt')
    CGM = pd.read_csv(filename, sep="|", low_memory = False)

    filename = os.path.join(filepath_data, 'PtRoster.txt')
    roster = pd.read_csv(filename, sep="|")
    
    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','TrtGroup'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['TrtGroup'] = roster['trtGroup']
    
    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    j = 0
    TDD_all = pd.DataFrame(columns=['PtID','TDD'])
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            patient_deliv = BasalRate[BasalRate.PtID == id]
            patient_cgm = CGM[CGM.PtID == id]
            patient_bolus = Bolus[Bolus.PtID == id]

            patient_deliv['DateTime'] = patient_deliv.DataDtTm.apply(datCnv)
            patient_cgm['DateTime'] = patient_cgm.DataDtTm.apply(datCnv)
            patient_bolus['DateTime'] = patient_bolus.DataDtTm.apply(datCnv)
            
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
            
            extended_index = data_merged[data_merged.BolusType=='Extended'].index.values
            for e in extended_index:
                data_merged.BolusDelivery[e] = data_merged.BolusDelivery[e]*0.5
                data_merged.BolusDelivery.loc[e+1:e+24] = data_merged.BolusDelivery.loc[e+1:e+24] + (data_merged.BolusDelivery[e]*0.5)/24
            
            data_merged.CGMVal = data_merged.CGMVal.replace({'HIGH': 400, 'High': 400, 'high': 400, 
                                                             'LOW': 40, 'Low': 40, 'low': 40})
            
            data_merged['Date'] = [data_merged['DateTime'][x].date() for x in data_merged.index]
            patient_deliv['Date'] = [patient_deliv['DateTime'][x].date() for x in patient_deliv.index]
            TDD_pt = pd.DataFrame(index=range(len(data_merged['Date'].unique())),columns=['PtID','TDD'])
            dd = 0
            for d in data_merged['Date'].unique():
                check = patient_deliv[patient_deliv.Date==d]
                index_values = data_merged[data_merged.Date==d].index.values
                if len(check)==0:
                    data_merged.BasalDelivery.loc[index_values] = np.nan
                    data_merged.BolusDelivery.loc[index_values] = np.nan
                if (data_val == True) & (len(check)!=0):
                    TDD_pt['PtID'][dd] = id
                    TDD_pt['TDD'][dd] = data_merged.BasalDelivery.loc[index_values].sum() + data_merged.BolusDelivery.loc[index_values].sum()
                    dd += 1

            TDD_all = pd.concat([TDD_all,TDD_pt])
            
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
                
                # pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
                # data_merged.to_csv(clean_data_path + "CleanedData/DCLP5_cleaned_egvinsulin_" + str(id) + ".csv",index=False)
        except:
            pass
        # j +=1
        # if j > 4:
            # break
            
    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    cleaned_data.to_csv(clean_data_path + "CleanedData/DCLP5_cleaned_egvinsulin.csv",index=False)
    patient_data.to_csv(clean_data_path + "CleanedData/DCLP5_patient_data.csv",index=False)
    TDD_all.to_csv(clean_data_path + "CleanedData/DCLP5_TDD_data.csv",index=False)

    return cleaned_data,patient_data

def DCLP3_cleaning(filepath_data,clean_data_path,data_val = True):
    filename = os.path.join(filepath_data,'Data Files', 'Pump_BasalRateChange.txt')
    BasalRate = pd.read_csv(filename, sep="|", low_memory = False)

    filename = os.path.join(filepath_data,'Data Files', 'Pump_BolusDelivered.txt')
    Bolus = pd.read_csv(filename, sep="|" , low_memory = False)

    filename = os.path.join(filepath_data,'Data Files', 'Pump_CGMGlucoseValue.txt')
    CGM = pd.read_csv(filename, sep="|", low_memory = False)

    filename = os.path.join(filepath_data,'Data Files', 'PtRoster_a.txt')
    roster = pd.read_csv(filename, sep="|", low_memory = False)
    
    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','TrtGroup'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['TrtGroup'] = roster['trtGroup']
    
    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    j = 0
    TDD_all = pd.DataFrame(columns=['PtID','TDD'])
    for id in PatientInfo.PtID.values:
        try:
            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            patient_deliv = BasalRate[BasalRate.PtID == id]
            patient_cgm = CGM[CGM.PtID == id]
            patient_bolus = Bolus[Bolus.PtID == id]

            patient_deliv['DateTime'] = patient_deliv.DataDtTm.apply(datCnv)
            patient_cgm['DateTime'] = patient_cgm.DataDtTm.apply(datCnv)
            patient_bolus['DateTime'] = patient_bolus.DataDtTm.apply(datCnv)
            
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
            TDD_pt = pd.DataFrame(index=range(len(data_merged['Date'].unique())),columns=['PtID','TDD'])
            dd = 0
            for d in data_merged['Date'].unique():
                check = patient_deliv[patient_deliv.Date==d]
                index_values = data_merged[data_merged.Date==d].index.values
                if len(check)==0:
                    data_merged.BasalDelivery.loc[index_values] = np.nan
                    data_merged.BolusDelivery.loc[index_values] = np.nan
                if (data_val == True) & (len(check)!=0):
                    TDD_pt['PtID'][dd] = id
                    TDD_pt['TDD'][dd] = data_merged.BasalDelivery.loc[index_values].sum() + data_merged.BolusDelivery.loc[index_values].sum()
                    dd += 1

            TDD_all = pd.concat([TDD_all,TDD_pt])
            
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
                
                # pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
                # data_merged.to_csv(clean_data_path + "CleanedData/DCLP3_cleaned_egvinsulin_" + str(id) + ".csv",index=False)
        except:
            pass
        # j +=1
        # if j > 5:
        #     break
            
    pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
    cleaned_data.to_csv(clean_data_path + "CleanedData/DCLP3_cleaned_egvinsulin.csv",index=False)
    patient_data.to_csv(clean_data_path + "CleanedData/DCLP3_patient_data.csv",index=False)
    TDD_all.to_csv(clean_data_path + "CleanedData/DCLP3_TDD_data.csv",index=False)

    return cleaned_data,patient_data

def IOBP2_cleaning(filepath,clean_data_path,data_val = True):
    #load patient roster
    filename = os.path.join(filepath, 'IOBP2PtRoster.txt')
    roster = pd.read_csv(filename, sep="|")
    #build clean roster
    PatientInfo = pd.DataFrame(columns=['PtID','StartDate','EndDate','TrtGroup','Age'])
    PatientInfo['PtID'] = roster['PtID']
    PatientInfo['StartDate'] = roster['RandDt']
    PatientInfo['EndDate'] = roster['TransRandDt']
    PatientInfo['TrtGroup'] = roster['TrtGroup']
    PatientInfo['Age'] = roster['AgeAsofEnrollDt']
    
    #load manual injections data
    filename = os.path.join(filepath, 'IOBP2ManualInsulinInj.txt')
    data_man_inj = pd.read_csv(filename, sep="|")
    #create datetime objects for easy inclusion
    data_man_inj['DateTime'] = np.nan
    data_man_inj.InsInjDt = [datetime.strptime(data_man_inj['InsInjDt'][x],'%m/%d/%Y').date() for x in data_man_inj.index.values]
    for i in data_man_inj.index.values:
        if (data_man_inj.InsInjAMPM[i] == 'PM') & (data_man_inj.InsInjHr[i]!= 12):
            data_man_inj.InsInjHr[i] = data_man_inj.InsInjHr[i] + 12

        data_man_inj['DateTime'][i] = datetime(data_man_inj.InsInjDt[i].year,
                                           data_man_inj.InsInjDt[i].month,
                                           data_man_inj.InsInjDt[i].day,
                                           data_man_inj.InsInjHr[i],
                                           data_man_inj.InsInjMin[i],
                                          )
    #load insulin pump data
    filename = os.path.join(filepath, 'IOBP2DeviceiLet.txt')
    data = pd.read_csv(filename, sep="|")
    #create new dateframe for clean data
    cleaned_data = pd.DataFrame()
    patient_data = pd.DataFrame()
    for id in PatientInfo.PtID.values:
        try:
            subj_data = data[data.PtID == id].reset_index(drop=True)
            

            subj_info = PatientInfo[PatientInfo.PtID == id].reset_index(drop=True)
            if len(subj_data) > 0:
                subj_info['DaysOfData'] = np.nan
                subj_info['Weight'] = np.nan
                subj_info['AVG_CGM'] = np.nan
                subj_info['STD_CGM'] = np.nan
                subj_info['CGM_Availability'] = np.nan
                subj_info['eA1C'] = np.nan
                subj_info['TIR'] = np.nan
                subj_info['TDD'] = np.nan

                subj_inj = data_man_inj[data_man_inj.PtID == id].reset_index(drop=True)
                data_preclean = subj_data.filter(items=['DeviceDtTm','PtID','CGMVal','BGMVal','InsDelivAvail','InsDelivPrev'])
                data_preclean['InsulinDelivered'] = data_preclean.InsDelivPrev.shift(-1)
                data_preclean['DateTime'] = data_preclean.DeviceDtTm.apply(datCnv)

                data_preclean = data_preclean.sort_values(by='DateTime').reset_index(drop=True)
                try:
                    subj_info['StartDate'] = subj_info.StartDate[0].apply(datCnv)
                    data_preclean = data_preclean[data_preclean.DateTime >= subj_info.StartDate.iloc[0]]
                    
                except:
                    pass
                #not everyone has an end data
                try:
                    subj_info['EndDate'] = subj_info.EndDate[0].apply(datCnv)
                    data_preclean = data_preclean[data_preclean.DateTime <= subj_info.EndDate.iloc[0]]
                except:
                    pass

                data_preclean['TimeBetween'] = data_preclean.DateTime.diff()
                data_preclean['TimeBetween'] = [data_preclean['TimeBetween'][x].total_seconds()/60 for x in data_preclean.index]
                #add manual injections
                data_preclean['ManualIns'] = 0
                if len(subj_inj)>0:
                    #find closest CGM time to injection
                    for i in subj_inj.index.values:
                        data_preclean['TimeFromInj'] = [(data_preclean['DateTime'][x] - subj_inj.DateTime[i]).total_seconds() for x in data_preclean.index]
                        data_preclean['TimeFromInj'] = data_preclean['TimeFromInj'].abs()
                        injection_index = data_preclean[data_preclean.TimeFromInj == data_preclean.TimeFromInj.min()].index.values[0]
                        data_preclean['ManualIns'][injection_index] = subj_inj.InsInjAmt[i]

                clean_subj = data_preclean.filter(items=['DateTime','PtID','CGMVal','BGMVal','InsDelivAvail','InsulinDelivered','ManualIns'])
                # clean_subj['DateTime'] = [clean_subj['DateTime'][x].isoformat() for x in clean_subj.index]
                #adjust data to start at midnight
                # print(clean_subj)
                start_date = clean_subj.DateTime.iloc[0].date()
                end_date = clean_subj.DateTime.iloc[-1].date() + timedelta(days=1)
                data_new_time = pd.DataFrame(columns=['DateTime_keep'])
                data_new_time['DateTime_keep'] = pd.date_range(start = start_date, end = end_date, freq="5min").values
                data_new_time['UnixTime'] = [int(time.mktime(data_new_time.DateTime_keep[x].timetuple())) for x in data_new_time.index]
                data_new_time = data_new_time.drop_duplicates(subset=['UnixTime']).sort_values(by='UnixTime')
                clean_subj['UnixTime'] = [int(time.mktime(clean_subj.DateTime[x].timetuple())) for x in clean_subj.index]
                
                clean_data_merged = pd.merge_asof(data_new_time, clean_subj, on="UnixTime",direction="nearest",tolerance=149)

                clean_data_merged = clean_data_merged.filter(items=['DateTime_keep','PtID','CGMVal','BGMVal','InsDelivAvail','InsulinDelivered','ManualIns'])
                clean_data_merged = clean_data_merged.rename(columns={"DateTime_keep": "DateTime", 
                                        "CGMVal": "egv",
                                        "InsulinDelivered": "insulin",
                                        "ManualIns": "ManualDelivery"
                                        })

                cleaned_data = pd.concat([cleaned_data,clean_data_merged])
                if len(clean_data_merged)>0:
                    if data_val == True:
                        subj_info['5minCheck'] = np.nan
                        subj_info['5minCheck_max'] = np.nan
                        subj_info['ValidCGMCheck'] = np.nan 
                        clean_data_merged['TimeBetween'] = clean_data_merged.DateTime.diff()
                        clean_data_merged['TimeBetween'] = [clean_data_merged['TimeBetween'][x].total_seconds()/60 for x in clean_data_merged.index]
                        subj_info['5minCheck'] = len(clean_data_merged[clean_data_merged.TimeBetween>5])
                        subj_info['5minCheck_max'] = clean_data_merged.TimeBetween.max()
                        subj_info['ValidCGMCheck'] = len(clean_data_merged[(clean_data_merged.egv<40) & (clean_data_merged.egv>400)])

                    subj_info['DaysOfData'][0] = np.round(len(subj_data)/288,2)
                    subj_info['Weight'][0] = subj_data.PtWeight.iloc[-1]
                    subj_info['AVG_CGM'][0] = np.round(clean_data_merged.egv.mean(),2)
                    subj_info['STD_CGM'][0] = np.round(clean_data_merged.egv.std(),2)
                    subj_info['CGM_Availability'][0] = np.round(100 * len(clean_data_merged[clean_data_merged.egv>0])/len(clean_data_merged),2)
                    subj_info['eA1C'][0] = np.round((46.7 + clean_data_merged.egv.mean())/28.7,2)
                    subj_info['TIR'][0] = np.round(100 * len(clean_data_merged[(clean_data_merged.egv>=70) & (clean_data_merged.egv<=180)])/len(clean_data_merged[clean_data_merged.egv>0]),2)
                    subj_info['TDD'][0] = np.round(clean_data_merged.insulin.sum()/subj_info['DaysOfData'][0],2)

                    pt_data = subj_info.filter(items=['PtID','StartDate','EndDate','TrtGroup','Age','DaysOfData','Weight','AVG_CGM','STD_CGM','CGM_Availability',
                                                    'eA1C','TIR','TDD','5minCheck','ValidCGMCheck','5minCheck_max'])
                    patient_data = pd.concat([patient_data,pt_data])
        except:
            pass
        #creates a new folder (if it doesnt exist) for cleaned data to be saved
        pathlib.Path(clean_data_path + "CleanedData").mkdir(parents=True, exist_ok=True)
        cleaned_data.to_csv(clean_data_path + "CleanedData/IOBP2_cleaned_egvinsulin.csv",index=False)
        patient_data.to_csv(clean_data_path + "CleanedData/IOBP2_patient_data.csv",index=False)
    
    return cleaned_data,patient_data

##########-------------- Run Functions for Testing 
# print('starting FLAIR')
# filepath = '/Users/rachelbrandt/Downloads/FLAIRPublicDataSet/Data Tables/'
# cleaned_data_path = '/Users/rachelbrandt/egvinsulin/' #location where you want cleaned data to be stored

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

# cleaned_data,patient_data =  IOBP2_cleaning(filepath,cleaned_data_path)
# print(patient_data)