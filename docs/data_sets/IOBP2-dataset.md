This part of the project documentation focuses on 
**The Insulin-Only Bionic Pancreas Pivotal Trial (IOBP2)**. You'll get a
chance to read about the background of the dataset,
as well as the reasoning behind how the data was cleaned and normalized.
## Study
- **Study Background:** This is a multi-center randomized control trial to compare the efficacy and safety of the iLet Bionic Pancreas (BP) system. Enrolled participants used the devices and collected data over a 13 week period.
- **Study Devices:** Insulin data is recorded from the iLet BP. Data is stored as Basal Insulin Delivery, Bolus Insulin Delivery, and Meal Insulin Delivery. 
CGM data is recorded from Dexcom G6 sensors. 
- **Study Population:** Children and adults with type 1 diabetes ages 6+
- **Total Data:** There is roughly 30,000 days of data from 343 participants

## Data
From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Tables** subfolder.

* **IOBP2DeviceiLet.txt**: All events logged on the iLet including CGM and insulin delivery 
* **PtRoster.txt**: Patient Roster

These are text files ("|" separator) and host many columns related to the iLet pump events and the Dexcom CGM Data. The glossary provides information about each column. Below are the relevant columns contained in IOBP2DeviceiLet.txt.

#### Relevant Columns

- **PtID**: Patient ID
- **DeviceDtTm**: Local date and time on the device
- **CGMVal**: CGM glucose value. Valid CGM values range from 39-401 mg/dl. Anything outside of this range or missing values are marked by a -1
TODO: Confirm/Check for CGM Magic Numbers

- **BasalDelivPrev**: Delivered basal dose (U) of the prior executed step 
- **BolusDelivPrev**: Delivered bolus dose (U) of the prior executed step 
- **MealBolusDelivPrev**: Delivered meal bolus dose (U) of the prior executed step 

#### Assumptions
- DeviceDtTm has two formats within the data: mm/dd/yyy and mm/dd/yyyy HH:MM:SS. It is assumed that the missing time values are exactly midnight. All DeviceDtTm values with only mm/dd/yyyy have 00:00:00 added. 
