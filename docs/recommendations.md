# Recommendations for Better Datasets

We have spend hundreds of hours processing and reverse-engineering clinical diabetes study datasets. In this process we often came accross similar challenges and unknowns. Often, we were not able to resolve these and had to make small or large assumptions. This page summarizes these challenges and provides suggestions for improvements. This should act as a guide for other researchers when processing datasets as well as investigators to improve the quality and utility of their datasets. 

## Access
- Access is often difficult and time-consuming
- Approval processes are cumbersome
- Data should be **click-to-download ready**

## File Structure and Glossary
- Filenames and column names often don't align with the glossary.
- One file per data type is preferred. 
 - DCLP3 is particularly problematic: 5 CGM files from different sources with inadequate descriptions.
- Avoid large files (e.g. Loop, T1DEXI)
  - This often requires out of memory computation
  - Split files by patient
  - Use **parquet over csv** (more efficient and persists datatype)

### Redundant Data
- Multiple columns or files may contain the same information (e.g. 6 CGM files with no added value)
- Confusing: which one is correct? Do I need all?
- Documentation should clearly specify:
  - Which files were used
  - How they were generated
  - Who created them (device or investigator)

## Datetimes
- **Prefer Local Datetime:**  
  - Ideally, local times
  - If UTC with offset, provide loale to allow acocuntin for Daylight Saving Time (DST) and travel-related shifts.

- **Device Resets & Time Shifts:**  
  - Do not send both "corrected timestamps" and original timestamps. Only the correct one should be shipped.
  - Ideally, device time resets are already integrated: If you provide them on top, explain if the datetimes are already accounted.

- **Consistent Format:**  
  - Follow ISO 8601 for all datetime formats.  
  - Avoid mixed formats (e.g., date/time separate, relative to study start).  
  - Relative to start can compromise analysis, such as weekends seasonality.

## Data Consistency
 - Avoid using different units in the same column:
 	- Replace BG bolus durations are given in ms or minutes depending on the data source (resides in a different table). 
	- Sometimes glucose values are expressed in both/either mg/dl and mmol/dl
 - Ensure all column unique column values are described (look at the unique values and discuss each single one including NaNs).
 	- Avoid using different labels for the same meaning e.g. dual vs. combination boluses
	- We've seen values that were not documented or missing. This is problematic because filtering by one criteria will miss other rows.
		- Flair: besides the CLOSED_LOOP_MICRO_BOLUS bolus type, there are also rows CL_MICRO_BOLUS
		- T1DEXI: combination vs. dual, standard vs. normal etc.

### Special Values & NaNs
 - Zero unit deliveries are unnecessary to report in boluses. If possible, these should have already been removed. However, in the case of basal rates, 0  mark basal suspends and should obviously be kept.
 - We often pbserved NaN values that had a meaning. For example when a suspend event occured the basal rate was NaN but in reality was paused and therefore should have been 0. 
 - Clearly document what meaning 0 and NaN values, or other magic numbers have.
 - Magic CGM Numbers such as 0/39/401 for outside/below/above measurement range should be clearly documented.

### Duplicates
 - Many datasets contain duplicates
 - Complete duplicates might be dropped but often the doses differ. 
 - Often these are Temporal duplicates (same patient and time) but other values differ:
	- Sometimes the basal rate is the same but other columns differ: Which information should we trust?
	- some doses differ by a fraction of the value
	- Somtimes the doses are completely different
 - Sometimes the same value is reported twice within close temporal distance 

Examples:   

 - Same extended bolus reported with 1 hour distance
 - Different basal rates at the same time (0 vs. 3, 2 vs. 3)
 - Almost identical basal rates at the same time but one is rounded: 1.25 vs. 1.3
 - same value reported with different duration format: 01:00 vs. 1:00 for basal duration
 - Same MDI injection reported twice within a few seconds: Duplicate or split bolus? (T1DEXi)
 
We expect this to be a result of:  

 - merging different data sources 
 - device reported a updated entry later on

The risks with duplicates are:  

  - duplicates are overseen and counted twice
  - wrong duplicate is dropped (at random)
  - or worse: always the wrong duplicate is kept (e.g. by using maximum value/id, latest,..)

## CGM, Basal and Boluses
### CGM
* Magic CGM Numbers (see above) (i.e. 38 and other values outside of the measurement range 40-400 mg/dl)
* Consistent handling of below/above range readings
* Below/Above Ranges
	* Some data is clamped (Replace BG limited to 39/401 mg/dl), others are encoded as below/above range)
* Report Calibrations (separately)
* Reduce the amount of files or describe the differences precisely. Which one should be used? Often we saw multiple files (e.g. Dexcom raw CGM, Clarity CGM, CGM from Pump,...) without documentation about which one was and should used for analysis or their differences. 

### Basal
- Ensure all basal changes are reported and that these reflect
  1. temporary basal rates
  2. pump suspends
  3. closed loop modes
- During Closed Loop Mode, are basal events still reported
	- We've seen cases where the pump reported zeros while others kept reporting the profile
 - If information about temporary basal rate changes is providede, this should be additional. The rate should be correct and trusted without having to be modified. 
- Duplciates: Ensure there are none because these are extremely difficult to investigate (see [Duplicates](#duplicates))
 - Basal Gaps should be marked
	- We've seen data gaps result in large basal durations which seems to be caused by retrospective processing (sometimes >250 days (Replace BG)). This makes it difficult to determine if the basal rate is active for more than a day, or if data was missing. 
	- Gaps in basal rate should be marked: Otherwise we don't know if the data is missing or no basal happened (see [Data Gaps](#data-gaps))

**Example**: In Flair, we had to manually add 0 events at suspends, and adopt the rate for temporary basal rates. Further, during closed loop modes basal rates were still reported and had to be shut off.

### Boluses

- **Extended Boluses**

  We've seen all sorts of things: Extended boluses reported upon completion or start, normal and extended part reported as two rows or in separate column, sometimes the total bolus didn't match the normal and extended part, sometimes different labels for extended parts (see [data consistency](#data-consistency)), etc.

Therefore, make sure to:   

 - Document if timestamp refers to delivery start or flair_suspends_with_cgm
 - Make sure that the duration reflects early stopped boluses
 - Provide the delivery duration (in DCLP5 this was missing)
 

## Data Gaps
Often unclear if data gaps are due to missing uploads, disconnected devices, other technical issues. Then it is unclear if the pump was still running and for example if we should trust the last basal event.This is especially difficult if we see gaps where some data types exist (e.g. CGM) while others are missing (basal rates).

 - A **watchdog signal** could help.
 - Documentation of the minimum reported frequency of pump events (does a pump report at least one basal rate per day?)

### Data Outside Study Period
- Excessive or missing data often appears before or after the defined study period
- Should be removed or correctly labeled
- A simple table could help to better interpret, trim and select the data:
  - Study period start and end
  - Device / intervention
  - device active/inactive 

## Validation measures (TDD)
 - Providing daily patient TDD split by basal and bolus is very helpful
 - In Flair, this allowed us spot wrong assumptions by comparing TDDs of our extracted data with the true TDDs
 - Make sure there is only one value per patient and day (we've seen it all)
 - Document how Basal TDD was calculated
