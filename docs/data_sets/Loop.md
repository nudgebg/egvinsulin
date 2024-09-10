# Data Files
The study data folder is named **Loop study public dataset 2023-01-31**

From the DataGlossary.rtf file, the following relevant data tables were identified which are stored in the **Data Tables** subfolder. These are "|" separated csv files.

|File|Size|Description|
|---|---|---|
| PtRoster.txt: | 67KB | Patient Roster| Patient Roster|
| LOOPDeviceBolus.txt | 350 MB| Bolus data exported from Tidepool|
|LOOPDeviceBasal\<i>.txt, i=1-3 |**~7.5 GB** | 3 basal data files exported from Tidepool|
| LOOPDeviceCGM\<i>.txt, i=1-6: | ~**12.5 GB**| 6 List of cgm data dowloaded from Tidepool|

Below are **relevant** columns contained in each file

## PTRoster
* **PtID**: Patient ID [^0]  
* **PtTimezoneOffset**: Participant’s timezone offset

**Notes:**  The PtID column was not listed in the data glossary but exists in the actual table.

## LOOPDeviceBasal1-3
* **Duration**: Actual number of milliseconds basal will be in effect
* **Percnt**: Percentage of suppressed basal that should be delivered
* **Rate**: Number of units per hour
* **SuprBasalType**: Suppressed basal delivery type (suppressed basal = basal event not being delivered because this one is active)
* **SuprDuration**: Suppressed duration
* **SuprRate**: Suppressed rate

**Notes:**  It is unclear what suppressed deliveries are.

## LOOPDeviceBolus
* **BolusType**: Subtype of data (ex: "Normal" and "Square" are subtypes of "Bolus" type)
* **Normal**: Number of units of normal bolus
* **Extended**: Number of units for extended delivery
* **Duration**: Time span over which the bolus was delivered (milliseconds for Tidepool data, minutes for Diasend data)
* **OriginName**: Data origin name
* **OriginType**: Data origin type

**Notes:**  

1. There are also expected delivery columns (ExpectedNormal , ExpectedExtended, ExpectedDuration). Therefore, we assume these columns to be the actual delivered amounts and durations. 
2. Unclear how to determine if the data is uploaded from Tidepool of Diasend? This effects the extended boluses.

## LOOPDeviceCGM1-6
* **CGMVal**: Glucose reading from the CGM (in mmol/L from Tidepool)
* **Units**: Glucose reading units
* **DexInternalDtTm**: Dexcom Internal date and time


## Shared columns
These are commons shared between Basal, Bolus and CGM files:  
* **PtID**: Patient ID  
* **DeviceDtTm**: Local device date and time; note not present in most rows because unavailable in Tidepool data source.  
* **UTCDtTm**: Date and time with timezone offset.  
* **TmZnOffset**: Timezone offset.

**Notes:**  See [Timezones](#Timezones)


## Challenges & Unknowns
### Timezones

**Attention**: It is essential to obtain the local time but we don't know if this is possible.
The Data glossary describes `UTCDtTm` as UTC with timezone information. However, `TmZnOffset` is only present when local device times  `DeviceDtTm` exist which is true only for a very small percentage of the data.
Therefore, local time might not be available for a lot of cases and needs to be extrapolated using backward/forward filling. Or by using the `PtTimezoneOffset` providede in the patient roster, assuming it does not change (which would be a terrible assumption since this is outpatient data > 6-12 month).  
It is also unclear how the datetimes are related to the dexcom CGM `DexInternalDtTm` times and if these are in utc or local time. 

### File-Sizes
* There are 3 Basal files, 1 Bolus file, and 6 CGM files
* The Basal files are 2.9GB, 2.9GB, and 1.35GB in size
* The bolus file is 349 MB
* The CGM files are 2.14, 2.24, 2.3, 2.31, 2.33, and 1.53 GB

Together, the file sizes pose a real problem for processing the data on machines with limited memory. This requires out of core compuatation. Since the patient ids are split accross files, using chunked processing is not an option. Instead, we aim to use dask package to perform  an option to identify patient ids accross files and then process one patient at a time, potentially using parallel computing. 

## Questions:
* What are suppressed deliveries?
* Why are there more patient IDs in the CGM files than in the Basal and Bolus files.
* How to obtain local times for all patients?
* Are Dexcom times local time or utc?
* How do we determine if the data is uploaded from Tidepool of Diasend?