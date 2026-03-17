## Study

**Background:** The objective of the study is to assess efficacy and safety of a closed loop system (t:slim X2 with Control-IQ Technology) in a large randomized controlled trial.  
**Devices:** t:slim X2 with Control-IQ and Dexcom G6 system  
**Population:** Teens and adults with type 1 diabetes ages 14 and older  
**Data:** There are roughly 19,700 days of data from 112 participants  

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
    - Identify duplicated rows across the dataset.
    - Review duplicates on specific columns (e.g., patient ID, datetime).
      - Determine the frequency of duplicates.
         - Investigate correlation patterns (e.g., CGM duplicates).
         - Decide on handling method: keep max, sum, or first instance.

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