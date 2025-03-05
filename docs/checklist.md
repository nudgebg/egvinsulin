## Checklist Template
- [ ] Things to check in every dataset
0. [ ] Data
	1. [ ] Glossary
		1. [ ] List all relevant files and columns
			1. [ ] check if they exist
			2. [ ] Check if there are more column names
			3. [ ] Are there other files, not mentioned?
	2. [ ] Missing data
		1. [ ] Check for null values
	3. [ ] Handle duplicates
        1. Obvious duplicates: Decide which columns are relevant (e.g. datetime, patient, bolus amount, duration?) and drop duplicates. 
            1. Ask: Why are there duplicates? Did I miss including a relevant column that explains this?
		1. [ ] Subset Duplicates (subset of columns)
            1. Temporal duplicates (e.g. patient id, datetime)
                1. Which one to pick?
			1. [ ] How often? Is it worth investigating?
				1. Check for correlation (e.g. CGM duplicates)
				2. [ ] Drop (keep first, max, record ID, or a different resolution technique might be better?)
	4. [ ] Incomplete Patients
		1. [ ] Keep only patients with data in all datasets (`total_ids = reduce(np.intersect1d, (df_basal.PtID.unique(), df_bolus.PtID.unique(), df_cgm.PtID.unique()))`)
2. [ ] Datetime Strings
	1. [ ] Datetime strings consistent?
		1. [ ] If not, check how to parse efficiently and correctly. Use `parse_flair_dates` if applicable
	2. [ ] Adjustments made?
		1. [ ] Which one to use?
		2. [ ] Check if adjustments make sense 
			1. [ ] Visually inspect gaps (sample)
			2. [ ] Check summary statistics (do gaps get smaller?)
3. [ ] Timestamps
	1. [ ] All in local time?
		1. [ ] Glossary mentions UTC, timezones?
        2. [ ] If times are not local (or only small set), and we don't know the location for all patients,  how much time zone error are we expecting? Can we estimate it? (Check out the Loop jupyter notebook).

	2. [ ] Check daily moving avererage distributions
		1. [ ] Breakfast, lunch, dinner peaks? Over-night drop?
		2. [ ] Data consistent with bolus and CGM?
4. [ ] CGMS
	1. [ ] Special Numbers (e.g. 38, 39)
		1. [ ] Replaced?
5. [ ] Boluses
	1. [ ] Requested vs. Delivered (check what timestamp means)
	2. [ ] Extended bolus duration
        1. Are there overlaps with the next bolus? Why?
6. [ ] Basals
    1. Are suspends and temporary basals already reflected?
	    1. [ ] Suspends?
	    2. [ ] Temporary Basals?
    3. [ ] Basal Durations
        1. Do the basal rates overlap with the next one? Why?
