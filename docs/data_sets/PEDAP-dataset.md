This part of the project documentation focuses on 
**TThe Pediatric Artificial Pancreas (PEDAP) trial: A Randomized Controlled Comparison of the Control- IQ technology Versus Standard of Care in Young Children in Type 1 Diabetes**. You'll get a chance to read about the background of the dataset,
as well as the reasoning behind how the data was cleaned and normalized.
## Study
- **Study Background:** The objective of the study is to assess efficacy, quality of life, and safety of a closed loop control (CLC) system (t:slim X2 with Control-IQ Technology) in a randomized controlled trial with partial crossover.
- **Study Devices:** t:slim X2 with Control-IQ and Dexcom G6 system
- **Study Population:** Children ages 2-5
- **Total Data:** There are roughly 19,700 days of data from 112 participants

## Data
From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Tables** subfolder.

* **PEDAPTandemBolusDelivered.txt**: List of pump data downloaded (bolus data only)
* **PEDAPTandemBASALRATECHG.txt**: List of pump data downloaded (basal data only)
* **PEDAPTandemCGMDATAGXB.txt**: List of cgm data downloaded 
* **PtRoster.txt**: Patient Roster

These are text files ("|" separator) and host many columns related to the iLet pump events and the Dexcom CGM Data. The glossary provides information about each column. Below are the relevant columns contained in each text file.

#### Relevant Columns
**PEDAPTandemBolusDelivered.txt:** 

* **PtID**: Patient ID
* **DataDtTm**: Datetime of completion of bolus insulin delivery
* **BolusAmount**: Size of completed bolus 
* **BolusType**: The bolus insulin delivery type [Automatic, Standard, Extended]
* **Duration**: For Extended bolus events, requested bolus duration in minutes
* **ExtendedBolusPortion**: For Extended bolus events, flag differentiating the immediate “Now” portion of the bolus (if any) from the extended portion (“Later”)

**PEDAPTandemBASALRATECHG.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Datetime of change in basal insulin delivery rate
* **BasalRate**: Basal insulin delivery rate, in U/hr

**PEDAPTandemCGMDATAGXB.txt:**

* **PtID**: Patient ID
* **DataDtTm**: Date-time of cgm value
* **CGMValue**: CGM value in mg/dl. Valid readings are 40-400, anything outside this range is marked with a 0

#### Differences and Similarities with DCLP3 and DCLP5
- In the PEDAP data, the basal rate and CGM events are reported in the same way as DCLP3 and DCLP5. However, the column name for the basal rate value is different in PEDAP.
- The PEDAP data set provides information on extended boluses, while the DCLP studies do not. In PEDAP, the extended portion of the bolus is reported at the completion of the bolus along with how long it was extended for. Using this information, we can accurately backfill the 5 minute deliveries. In the DCLP studies, we have to make assumptions on how long the bolus is extended for, and if the extended portion is reported at the announcement or at the completion. 