## Replace BG

A Randomized Trial Comparing Continuous Glucose Monitoring With and Without Routine Blood Glucose Monitoring in Adults with Type 1 Diabetes

**Background:** The primary objective of the study is to determine whether the routine use of CGM without BGM confirmation is as safe and effective as CGM used as an adjunct to BGM. 

**Duration**: Run-in phase of 2–10 weeks, 26 weeks study duration
**Devices:** Dexcom G4 Platinum
**Population:** 276 entered run in phase, 226 were assigned to groups, 217 completed, Patients, Type 1, >=18 years, CSII
**Data:** There are roughly xxx days of data from 225 participants  


“Data were uploaded from the study CGM and BGM devices and the participant’spersonal insulin pump by using the Tidepool platform (http://tidepool.org). For insulin pumps that were unable to be uploaded to the Tidepool platform, the data were obtained by using Diasend (Chicago, IL) software” ([Aleppo et al., 2017, p. 540](zotero://select/library/items/JMBWSKEE)) ([pdf](zotero://open-pdf/library/items/JHYQJ9TW?page=3&annotation=GTMF46IL))


## Data
From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Tables** subfolder: 

Filename1: Holds information about ...
| Column| Description | Comment |
|--------------------|-----|-------|
| PtID               | Patient ID|       |

Filename2: Holds information about ...
| Column| Description | Comment |
|--------------------|-----|-------|
| PtID               | Patient ID|       |



## General Observation (first Glance)
 - ...
 - ...

 

## Data Integrity

### Missing Data
    - Check for null values across columns.

### Duplicate Rows
Some duplicates have same time, duration and rate (but differ in type) those i don’t care about. Others have same time and duration but different rate. Others have only same time but different duration / rate. The meaning of the extra columns (Percent, ExpectedDuration, SuprDuration…) remain unclear. Reverse engineering this is a big time sink and we probably won’t get it right all the time. 

A few examples (same time and rate). Split by which combination of basal types exist. 

![](assets/replacebg_basal_dups_time_duration_by_basal_types.png)

For these, those are the assumptions i made:
From the exampels we believe the following assumptions should be made: When there are temporal duplicates in time and duration. Then the duplicates should be resolved as follows:
 1. (scheduled or temp) and suspends: keep the suspend, set Rate to 0 (using fillna)
 2. scheduled and temp: use temp over scheduled
 3. Only scheduled: use the maximum value


The duplicates that have different durations are still to be done. I have already seen that many durations don’t match with the “next” correct basal rate. In these cases i would only keep the one that matches.
Here is an example: Two duplicates at 14:00 with different durations. Only one of the durations (4h) matches with the next non-duplicated row at 18:00. The other, is probably wrong.
image.png
 
![](assets/replacebg_basal_dups_different_durations_example.png)
### Incomplete Patients
    - Filter for patients with complete data in all datasets.
      - Use: `total_ids = reduce(np.intersect1d, (df_basal.PtID.unique(), df_bolus.PtID.unique(), df_cgm.PtID.unique()))`


## Datetimes
We want to make sure that datetimes of all datasets are in the same datetime and provide information about local time.

### Datetime Strings
    - Ensure uniform datetime formatting across records.
    - Parse as needed, using `parse_flair_dates` if applicable.

### Datetime Adjustments
    - Determine if datetime adjustments are needed.
      - Verify adjustments by:
         - Visually inspecting samples for continuity.
         - Reviewing summary statistics to check if gaps decrease.


## Timestamps

### Time Localization
    - Confirm timestamps are in local time.
    - Check dataset documentation for references to UTC/timezones.

### Distribution Analysis
    - Analyze timestamp distributions.
      - Look for peaks around meal times (breakfast, lunch, dinner).
      - Ensure consistency with bolus and CGM data.


## CGM

### Special Values
    - Identify and replace any special CGM values if needed.



## Boluses

### Requested vs. Delivered
    - Compare requested vs. delivered boluses and clarify timestamp meaning.

### Extended Bolus Duration
    - Check durations for extended boluses to ensure accuracy.


## Basal Rates

### Suspends
    - Identify and process any basal suspensions.

### Temporary Basals
    - Review and validate temporary basal settings.

## Other 