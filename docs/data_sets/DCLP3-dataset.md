This part of the project documentation focuses on 
**The International Diabetes Closed Loop (iDCL) trial: Clinical Acceptance of the Artificial Pancreas - A Pivotal Study of t:slim X2 with Control-IQ Technology (DCLP3)**. You'll get a chance to read about the background of the dataset,
as well as the reasoning behind how the data was cleaned and normalized.
## Study
- **Study Background:** The objective of the study is to assess efficacy and safety of a closed loop system (t:slim X2 with Control-IQ Technology) in a large randomized controlled trial.
- **Study Devices:** t:slim X2 with Control-IQ and Dexcom G6 system
- **Study Population:** Teens and adults with type 1 diabetes ages 14 and older
- **Total Data:** There are roughly 19,700 days of data from 112 participants

## Data
From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Tables** subfolder.

* **Pump_BolusDelivered.txt**: List of pupm data downloaded (bolus data only)
* **Pump_BasalRateChange.txt**: List of pump data dowloaded (basal data only)
* **Pump_CGMGlucoseValue.txt**: List of cgm data dowloaded 
* **PtRoster.txt**: Patient Roster

These are text files ("|" separator) and host many columns related to the iLet pump events and the Dexcom CGM Data. The glossary provides information about each column. Below are the relevant columns contained in each text file.

#### Relevant Columns
**Pump_BolusDelivered.txt:** 

* **PtID**: Patient ID
* **DataDtTm**: Datetime of delivered insulin
* **BolusAmount**: the amount of bolus delivered 
* **DataDtTm_adjusted**: Adjusted value of DataDtTm 
* **BolusType**: The bolus insulin delivery type [Standard, Extended]

**Pump_BasalRateChange.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Date-time of basal rate change
* **CommandedBasalRate**: Basal Rate (U/h) - The active basal insulin delivery. These events appear everytime a new basal rate is programmed 
* **DataDtTm_adjusted**: Adjusted value of DataDtTm

**Pump_CGMGlucoseValue.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Date-time of basal rate change
* **CGMValue**: CGM value in mg/dl. Valid readings are 40-400, anything outside this range is marked with a 0
* **DataDtTm_adjusted**: Adjusted value of DataDtTm 

#### Assumptions
- There is no information on how the extended boluses were programmed. It was assummed that all extended boluses were set to the default settings: 50% of the bolus was delivered up front and the remaining 50% was delivered over the next two hours. 
