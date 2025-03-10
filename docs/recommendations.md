## Recommendations for Better Datasets

We have spend hundreds of hours processing and reverse-engineering clinical diabetes study datasets. In this process we often came accross similar challenges and unknowns. Often, we were not able to resolve these and had to make small or large assumptions. This page summarizes these challenges and provides suggestions for improvements. This should act as a guide for other researchers when processing datasets as well as investigators to improve the quality and utility of their datasets. 

### Consistency in units
Avoid using different units in the same column: For example, Replace BG bolus durations are given in ms or minutes depending on the data source not obvious and resides in a different table.  Sometimes glucose values are expressed in both/either mg/dl and mmol/dl, requiring assumptions to be made.

### File Structure and Glossary
- Glossary filenames and column names often don't align
- One file per data type. DCLP3 is by far the worst: 5 CGM files from different sources with poor descriptions [[#DCLP3 vs. 5 Datafiles]]
- Split files by patient or use parquet structures

### Datetimes
* Ideally: local datetime! 
	* Alternatively: UTC + offset 
		* DST (Geographical Location)
		* Travels
* Datetime device resets: should be integrated and duplicate events removed

### CGM
* Magic CGM Numbers (i.e. 38 and other values outside of the measurement range 40-400 mg/dl)
* Consistent handling of below/above range readings
* Below/Above Ranges
	* Some data is clamped (Replace BG limited to 39/401 mg/dl), others are encoded as below/above range)
* Report Calibrations (separately)
* Reduce the amount of files or describe the differences precisely. Which one should be used? Often we saw multiple files (e.g. Dexcom raw CGM, Clarity CGM, CGM from Pump,...) without documentation about which one was and should used for analysis or their differences. 

### Basal
* Suspends should already be integrated
* Temporary Basals should already be integrated

### Boluses
* Provided clarity on extended boluses timestamps 
* Record the delivered portion, not the requested portion

### File Sizes
* Datasets split by patient if large
* Only one unit! (mmol/dL vs. mg/dl no extra column for the unit)
### Gaps 
* Often data gaps result in large basal durations which seems to be caused by retrospective processing (sometimes >250 days (Replace BG). This makes it difficult to determine if the basal rate is active for more than a day, or if data is missing. 
* Mention of missing data
* Remove data before study started (orphan pump events)
- If there is no data is this because no boluses occurred or because they are not reported? (Watchdog)
### Other
* Remove duplicates
### Validation measures
* Report of TDD for verification split by basal and bolus
* Report of CGM TIR, mean, std
### Duplicates
Many datasets contain duplicates and NaN Values
It is unclear often how these should be interpreted. Complete duplicates might be dropped but often the dose is different. Or the same value is reported twice within close temporal distance (e.g. T1DEXI basal injections). Then, it is unclear wether these are double injections or duplicate imports. Also, priming doses are not marked as such. Often, MDI doses seem to be missing.
