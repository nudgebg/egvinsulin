!!! info
	This checklist is for **researchers implementing a new dataset parser** in BabelBetes. It is based on pitfalls, challenges, and errors encountered while processing clinical diabetes datasets, and ensures that important aspects are not overlooked. If you are a dataset provider or investigator looking for guidance on how to structure and distribute your data, see [Recommendations for Dataset Providers](recommendations.md) instead.

!!! tip "Guiding principle: impact-based decisions"
	The goal of every check here is to ensure the extracted data faithfully represents what actually happened clinically. Not every issue requires a fix. Before investing time in a complex resolution, ask: **how often does this occur, and how much does it affect downstream analysis?** An issue affecting <1% of events that is difficult or impossible to resolve and has negligible expected impact (e.g. duplicated CGMS with almost identical values) on population-level metrics should be **accepted and documented**.


## 1. Basal Rates

Basal rate data is the most complex data type — it requires assembling a continuous rate history from a mix of scheduled rates, temp basals, and suspend events.

In FLAIR, 72,424 suspend events are stored in a separate table and are *not* reflected in the basal rate history — they must be manually merged. Temp basals in FLAIR come in two modes: "Percent" (multiply scheduled rate by percentage) and "Rate" (replace with absolute rate). In LOOP, suspend events are reported as `NaN` basal rates and must be replaced with 0, not dropped. In some datasets (e.g. T1DEXI) we have seen basal rates overlapping with the next basal rate's start time — the duration must be recalculated. In PEDAP and DCLP3, there are no temp basals or suspends to handle.

- [ ] Determine how **suspends** are represented: separate table, NaN rate, or 0 rate — and handle accordingly
- [ ] Check for **temporary basal rates**: are they in absolute units or percent of scheduled rate?
- [ ] For percent temp basals: multiply the scheduled rate; for rate temp basals: replace the scheduled rate
- [ ] Check for basal rate **overlaps**: does a new rate start before the previous one expires? What could explain this? How often does it occur?
- [ ] Plot the daily moving average of basal rates — expect a physiological diurnal pattern
- [ ] Verify that basal data is consistent with the CGM and bolus data (same patients, same time range)


## 2. Boluses

Bolus data has three common sources of complexity: requested vs. delivered amounts, extended bolus duration, and duplicates from dual-source logging.

Extended bolus timestamps can sometimes represent the *completion* of delivery, sometimes the start of delivery. Sometimes, duration is not provided and must be inferred (In DCLP3 and DCLP5). In some datasets, the duration column values represent different units depending on the data source (milliseconds for Tidepool, minutes for Diasend imports).

- [ ] Determine whether reported values are **requested** or **delivered** — use delivered
- [ ] Check the timestamp meaning: is it the start or the end of delivery? (Especially for extended boluses)
- [ ] Check for extended/square/dual-wave boluses — how is duration provided or inferred?
- [ ] For datasets without explicit duration: implement matching logic; set outlier durations to median
- [ ] Check for orphan extended bolus parts (extended portion with no matching standard bolus)
- [ ] Validate bolus duration units: minutes, milliseconds, or ISO 8601?

??? note "Old reference items"
    5. [ ] Boluses
    	1. [ ] Requested vs. Delivered (check what timestamp means)
    	2. [ ] Extended bolus duration
            1. Are there overlaps with the next bolus? Why?


## 3. CGM Values

CGM sensors have hard physical limits, and different datasets encode out-of-range values differently.

DCLP3, DCLP5, and PEDAP store out-of-range CGM readings as `0`, with a separate `HighLowIndicator` column (1 = high/400, 2 = low/40). REPLACE BG and LOOP use sentinel values: 39 and 401 (or 38). LOOP had a handful of patients with values above and below these limits. One patient showed glucose values above 400, potentially from a modified CGM device (using a third party application such as xDrip or similar).

- [ ] Check the distribution of CGM values — are there values below 40 or above 400?
- [ ] Check for sentinel values (0, 38, 39, 401) used to represent out-of-range readings or error codes
- [ ] Determine how to handle each out-of-range case: replace with boundary value, or drop
- [ ] Check the unit: mg/dL or mmol/L? Convert if necessary
- [ ] Remove or flag any non-physiological values that are likely sensor artifacts


## 4. Timestamps and Timezones

Diabetes physiology follows a daily pattern (circadian rhythm). Having datetimes in local time is absolutely mandatory — having only UTC time or incorrect timezone information will have a major impact on analysis.

Most JAEB datasets store local time — and we confirmed this by checking the diurnal patterns. LOOP was an exception: datetimes were in UTC and required a static per-patient offset from the patient roster. The question was whether using a static value would cause large errors (e.g. are patients traveling much?). Fortunately, 37% of patients came with a `TmZnOffset` in the CGM records, which we used to estimate an expected error of less than 2 hours for >96% of cases. After adjustment, the diurnal patterns confirmed times were local, showing postprandial glucose peaks in the morning, noon, and evening; stable overnight basal. This diurnal validation is the most reliable way to confirm timezone correctness.

- [ ] Check the glossary for any mention of UTC, local time, or timezone
- [ ] Verify with a diurnal CGM or bolus plot — expect peaks in the morning ~6–9am, ~12pm, ~6–8pm (for US patients)
- [ ] If UTC or unknown: determine how timezone correction will be applied and for how many patients it is possible
- [ ] If timezone data is incomplete, document the expected error and how many patients are affected


## 5. Datetime Adjustments

Sometimes timestamps are corrupted due to device clock errors or incorrect timezone handling. FLAIR, DCLP3, and DCLP5 include a `DataDtTm_adjusted` column where JAEB already corrected such errors. These adjusted values need to be merged with the remaining unadjusted datetimes.

- [ ] Check whether an adjusted datetime column exists
- [ ] Check for strong jumps or overlapping data in the CGM trace that could indicate a clock correction
- [ ] Verify that adjusted datetimes correctly close the gaps (inspect time-difference distributions before/after)
- [ ] Document your decision: which column you used and why


## 6. Datetime Parsing

Datetime strings in clinical datasets often come in different formats and sometimes differ even within the same file.

Some datasets have datetime strings where the time component is omitted entirely when the event occurs at midnight — `2020-01-01` instead of `2020-01-01 00:00:00`. T1DEXI stores datetimes as seconds offset from `1960-01-01`. REPLACE BG provides no absolute dates at all — only days elapsed since enrollment.

- [ ] Check whether datetime strings are consistent across all rows — inspect format, length, leading zeros, 12/24h
- [ ] Check whether the time component can be missing (midnight entries)
- [ ] Use `parse_flair_dates()` where applicable (FLAIR/DCLP5/PEDAP midnight-truncation pattern)
- [ ] If multiple formats exist in the same column, split and parse separately
- [ ] Confirm parsed values are reasonable (no year 1960, no year 2099, no NaT at unexpected rates)

??? note "Old reference items"
    2. [ ] Datetime Strings
    	1. [ ] Datetime strings consistent?
    		1. [ ] If not, check how to parse efficiently and correctly. Use `parse_flair_dates` if applicable
    	2. [ ] Adjustments made?
    		1. [ ] Which one to use?
    		2. [ ] Check if adjustments make sense
    			1. [ ] Visually inspect gaps (sample)
    			2. [ ] Check summary statistics (do gaps get smaller?)


## 7. Duplicates

Duplicates are universal. Every dataset we have processed contains them in some form. For example, FLAIR had ~9.2% temporal bolus duplicates (same patient + datetime, differing only in `BolusSource`). ~1/3 of temporal basal duplicates differ by exactly 0.005 U/h, and bolus duplicates from `CLOSED_LOOP_MICRO_BOLUS` are rounded up to the nearest 0.005 U increment while `CL_MICRO_BOLUS` entries are not. Another example is the LOOP dataset which contains 34.70% exact CGM duplicates (identical rows) but much more (38.41%) temporal duplicates (checking timestamp alone) which a normal `drop_duplicates()` would have missed.

- [ ] Check for **exact duplicates** across all relevant columns — why do they exist?
- [ ] Check for **temporal duplicates** (same patient + datetime, differing values) — which record to keep?
- [ ] Use a tolerance margin when checking for duplicates to uncover near-exact duplicates that differ only by a small rounding or precision error
- [ ] For each duplicate type, try to understand the root cause
- [ ] Determine and document the resolution technique: drop, keep first, keep max, keep by RecordID, etc.
- [ ] For temporal duplicates, check whether another column explains the difference (e.g., `BolusType` in DCLP3/DCLP5 explains apparent bolus duplicates that had distinct meanings)
- [ ] Quantify: how often do duplicates occur overall and per patient? Is it acceptable to document and move on?
- [ ] Are temporal duplicates correlated? Do they contain the same or similar value? CGM duplicates are often near-identical, possibly from multiple export sources with slight post-processing differences

??? note "Old reference items"
    	3. [ ] Handle duplicates
            1. Obvious duplicates: Decide which columns are relevant (e.g. datetime, patient, bolus amount, duration?) and drop duplicates.
                1. Ask: Why are there duplicates? Did I miss including a relevant column that explains this?
    		1. [ ] Subset Duplicates (subset of columns)
                1. Temporal duplicates (e.g. patient id, datetime)
                    1. Which one to pick?
    			1. [ ] How often? Is it worth investigating?
    				1. Check for correlation (e.g. CGM duplicates)
    				2. [ ] Drop (keep first, max, record ID, or a different resolution technique might be better?)


## 8. Missing Data and Special Values

Understand the meaning of special values before doing any computation.

Often, the value of 0 or NaN is not obvious. By no means should such values be dropped before checking! Examples: In DCLP3 and DCLP5, a CGM value of `0` indicates an out-of-range reading (use `HighLowIndicator` to determine whether to replace with 40 or 400 mg/dL). In IOBP2, a missing time component in `DeviceDtTm` means midnight, not an error. In LOOP, a NaN basal rate actually refers to a pump suspend and should be replaced with 0. In T1DEXI, some FAORRES values appear as `5.397605e-79` — effectively zero but stored with a floating-point precision error, which makes finding duplicates with other zero values difficult.

- [ ] Profile every numeric column: check value ranges, count zeros, NaNs, and empty strings
- [ ] Profile every categorical column: check value counts and look for unexpected categories
- [ ] For each special value (0, NaN, empty string): determine what it actually represents — is it truly zero, missing, or an out-of-range sentinel?
- [ ] Document the frequency and per-patient/per-day impact of each special value
- [ ] Confirm your interpretation is documented somewhere in the glossary or study documentation


## 9. Incomplete Patients

Not all patients have data across all modalities. Including patients with partial data will silently corrupt downstream analysis.

In DCLP3, 125 patients appear in the basal and bolus files, but only 112 appear in the CGM file — 13 patients have no CGM data and must be excluded. In REPLACE BG, 208 of 226 patients have basal data, leaving 18 to exclude. In PEDAP (Release 3), the SC group had no complete basal data at all; this was only resolved in Release 4.

- [ ] Compute the set of unique patient IDs in each data type (CGM, bolus, basal)
- [ ] Identify patients missing from one or more datasets
- [ ] Decide and document which patients to include


## 10. Data Inventory

Before writing any extraction logic, verify that the data actually matches what is described.

Datasets rarely document themselves completely. DCLP3 contained additional columns not listed in the glossary. LOOP's suppressed basal records came without detailed explanation.

- [ ] Cross-check all files and columns listed in the glossary against what is actually on disk
- [ ] Look for files not mentioned in the glossary that may contain relevant data
- [ ] Check for undocumented columns in known files