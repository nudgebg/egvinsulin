This part of the project documentation focuses on 
**The International Diabetes Closed Loop (iDCL) trial: Clinical Acceptance of the Artificial Pancreas in Pediatrics - A Pivotal Study of t:slim X2 with Control-IQ Technology**. You'll get a chance to read about the background of the dataset,
as well as the reasoning behind how the data was cleaned and normalized.
## Study
- **Study Background:** The objective of the study is to assess efficacy and safety of a closed loop control (CLC) system (t:slim X2 with Control-IQ Technology) in a randomized controlled trial with partial crossover.
- **Study Devices:** t:slim X2 with Control-IQ and Dexcom G6 system
- **Study Population:** Children aged 6 - 13 years old with type 1 diabetes
- **Total Data:** There are roughly 19,200 days of data from 100 participants

## Data
While there is a data glossary (DataGlossary_Dits.rtf) file, the file names within the glossary do not match the file names of the data. However, the column names do match and those definitions are listed below.

* **DCLP5TandemBolus_Completed_Combined_b.txt**: List of pupm data downloaded (bolus data only)
* **DCLP5TandemBASALRATECHG_b.txt**: List of pump data dowloaded (basal data only)
* **DCLP5TandemCGMDATAGXB_b.txt**: List of cgm data dowloaded 
* **PtRoster.txt**: Patient Roster

These are text files ("|" separator) and host many columns related to the iLet pump events and the Dexcom CGM Data. The glossary provides information about each column. Below are the relevant columns contained in each text file.

#### Relevant Columns
**DCLP5TandemBolus_Completed_Combined_b.txt:** 

* **PtID**: Patient ID
* **DataDtTm**: Date-time of delivered insulin
* **BolusAmount**: the amount of bolus delivered
* **BolusType**: The bolus insulin delivery type [Standard, Extended]
* **DataDtTm_adjusted**: adjusted Datetime

**DCLP5TandemBASALRATECHG_b.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Date-time of basal rate change
* **CommandedBasalRate**: Basal Rate (U/h) - The active basal insulin delivery rate in units per hour
* **DataDtTm_adjusted**: adjusted Datetime

**DCLP5TandemCGMDATAGXB_b.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Datetime 
* **CGMValue**: 40-400 are legitimate glucose values. 0 is used when the reading is high or low
* **DataDtTm_adjusted**: adjusted Datetime


#### Assumptions
- There is no information on how the extended boluses were programmed. It was assummed that all extended boluses were set to the default settings: 50% of the bolus was delivered up front and the remaining 50% was delivered over the next two hours. 
- DeviceDtTm has two formats within the data: mm/dd/yyy and mm/dd/yyyy HH:MM:SS. It is assumed that the missing time values are exactly midnight. All DeviceDtTm values with only mm/dd/yyyy have 00:00:00 added. This occurs only in the Basal and CGM data.