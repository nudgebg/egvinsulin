# Recommendations for Dataset Providers

!!! info "For researchers"
    If you are a researcher looking for a checklist to guide the implementation of a new dataset parser, see the [Dataset Processing Checklist](checklist.md) instead.

This page is addressed to **clinical study investigators and dataset distributors**. It summarizes learnings from the complex task of processing publicly available diabetes datasets and provides actionable recommendations that we believe would make future datasets easier to process and therefore positively impact diabetes innovation.

---

## Access

Most datasets are readiliy available such as the ones hosted by JAEB. However, other datasets often require complicated request forms and approval processes. The friction introduced by complex access procedures limits research throughput — especially for multi-study comparative analyses.

- Approval processes should be avoided where possible.
- Data should be **click-to-download ready** once access is granted, without requiring additional coordination steps.

---

## File Structure and Glossary

To avoid ambiguity, filenames and column names should match the glossary exactly. Researchers should be able to understand what data is available and how to use it without having to make assumptions or contact the study team.

- **One file per data type** is strongly preferred. When multiple files exist for the same data type, each file's origin and intended use should be clearly described.
- Avoid very large files. They require out-of-memory computation and create friction for researchers with limited hardware. Prefer **splitting files by patient** and using **Parquet over CSV**: Parquet is more storage-efficient and preserves column data types, eliminating a common class of parsing errors.

### Redundant Data

When multiple files or columns contain the same information, document clearly which is authoritative. Without this, researchers are left guessing which source to trust.

Documentation should clearly specify:

- Which files should be used for analysis  
- How each file was generated (device export, investigator post-processing, etc.)
- Explain which post-processing steps were already taken and therefore which columns to rely on. Consider flagging or removing corrupt columns and files altogether to avoid ambiguity. 

### Patient Counts

There can be discrepancies between the number of patients enrolled in a study and the number of patients represented in the distributed dataset. Some datasets include more patients than reported in the publicaiton (e.g. Loop). Document the expected number of patients and flag any known exclusions or exceptions or missing data types (e.g. import error). This helps resolve uncertainties and would allow repeat previously published results that can serve as a means to verify the extraction was performed correctly.

---

## Datetimes

Datetime handling is one of the most error-prone areas in clinical datasets. Errors here often go undetected for a long time because they produce plausible-looking results rather than immediate failures.

**Prefer local datetimes.** Since diabetes physiology follow diurnal patterns, local time information is absolutely necessary. It should be clear from the documentation which times are local and if they are synchronized. When UTC timestamps with offsets are provided instead, include the locale so that Daylight Saving Time shifts and travel-related timezone changes can be correctly applied. Ensure that locale information is avilable when traveling timezones. Ideally, provide local times at all times.

**Handle device resets and time corrections before distribution.** When timezones were corrected (e.g. for device resets or other sources of errors) it can become unclear which columns to trust and if these corrections have been applied everywhere. Provide only the corrected timestamps or if corrupt data is included for transparency, document clearly which corrections have been applied.

**Use a consistent format throughout.** Follow ISO 8601 for all datetimes. Mixed formats — such as some columns using `YYYY-MM-DD HH:MM:SS` and others using separate date and time columns, or timestamps expressed as days relative to study start — introduce parsing complexity and can silently compromise analyses that depend on calendar effects (e.g., weekday vs. weekend patterns, seasonal variation). Ensure that midnight times follow the same schema.

---

## Data Consistency

To ensure automated pipelines can parse data reliably, column values should carry consistent meanings and use consistent labels throughout. Inconsistencies — different units in the same column, or different labels for the same concept — cause parsers to either fail visibly or, worse, silently misclassify data. 

- **Avoid mixed units within a single column.** For example, bolus durations should use a single unit consistently (not milliseconds in some rows and minutes in others). Similarly, glucose values should use a single unit (mg/dL or mmol/L, not both).
- **Document all unique values in every categorical column**, including NaN. To prevent filtering logic from silently missing rows, every possible value — including edge cases — should be described. Synonyms and abbreviation variants for the same concept are a common source of silent data loss.
- **Avoid column interdependencies**, where the meaning or unit of one column depends on the value of another. For example, a `type` column (with values like `cgm`, `calibration`, `bgm`) that changes what the `glucose` column represents forces the parser to split and re-join data to interpret it correctly — and any undocumented type value silently corrupts the result. Even more problematic is when the *unit* of a value in one column depends on a field in a different table or row (e.g., bolus duration in milliseconds vs. minutes depending on data source). Each column should have a single, unambiguous meaning regardless of context.

- Examples: Flair dataset the bolus source sometimes was CLOSED_LOOP_MICRO_BOLUS and sometimes CL_MICRO_BOLUS. T1DEXI: used different wording for the same bolus types: combination vs. dual, standard vs. normal.

### Special Values and NaNs

Magic numbers and NaN values require explicit documentation. Their meaning often depends on context and is easy to get wrong.

- **Zero deliveries in bolus data** are generally unnecessary to report. However, zero basal rates carry meaningful information (a basal suspend) and must be preserved.
- **NaN basal rates** can be ambiguous. During a pump suspend, a NaN rate may need to be interpreted as zero — a distinction that changes TDD calculations significantly. Document the value ranges and NaN meanings in the data glossary.
- **CGM magic numbers** (e.g., 0, 39, 401 used to signal out-of-range readings) must be documented. Some datasets clamp values at 39 or 401 mg/dL; others encode out-of-range readings separately. 

### Duplicates

Duplicates are difficult to resolve after the fact and should be addressed before distribution. They can arise from various reasons such as merging data from multiple sources, post-processing or from devices issuing updated records after initial submission.

The most challengging deduplication is resolving **temporal duplicates**: records for the same patient and timestamp but with different values. But there are many other challengging duplications:

- The same extended bolus reported twice, one hour apart
- Conflicting basal rates at the same timestamp (e.g., 0 vs. 3 units/hour, or 2 vs. 3 units/hour)
- Near-identical basal rates that differ only due to rounding (e.g., 1.25 vs. 1.3 units/hour)
- Inconsistent duration formats for the same record (e.g., `01:00` vs. `1:00`)
- The same injection logged twice within seconds — ambiguous as to whether it is a duplicate or a split bolus

The risks with unresolved duplicates are significant: they may be counted twice, the wrong record may be dropped at random, or a deterministic deduplication rule may systematically retain the wrong entry (e.g., always keeping the maximum or the latest value).

Wherever possible, duplicates should be resolved before distribution, with documentation explaining the resolution strategy.

---

## CGM, Basal, and Boluses

### CGM

To avoid downstream parsing errors, out-of-range readings should be handled consistently and the chosen approach documented. Some datasets clamp values at 39 and 401 mg/dL; others use special codes. Both approaches are acceptable, but the choice must be clearly documented. Calibration events should be reported separately from glucose readings. When multiple CGM sources are available (e.g., raw device export, cloud platform export, pump-side CGM), document the differences.


### Basal

Obtaining the true patient's basal rate at all times is a very complex and time consuming challenge, often with many ambiguities. This is because temporary basal rate changes and pump suspends are often reported separtely. Also, pump suspends are often indistinguishable from missing data. And this varies based on the dataset and device type.. Therefore, it is important that the glossary explains which data is required or if the basal rate change events are already corrected for these effects.

Ideally, pump suspends appear as explicit zero-rate events in the basal rate, not as separte events or NaN values.

Closed loop mode introduces particular ambiguity: some pumps continue to report basal rates during closed loop operation, while others report zeros or stop reporting entirely. This must be documented.

**Gaps in basal data** are especially problematic. When no basal event is recorded for an extended period, it is unclear whether the pump was inactive, data is missing, or the last known rate persisted. Without explicit gap markers, downstream tools cannot safely distinguish these cases and are forced to make assumptions that may be wrong.

- **Do not ship both original and corrected basal rates.** Only the corrected, trusted values should be distributed.
- **Mark data gaps explicitly** so that downstream tools can distinguish missing data from periods of inactivity.

### Boluses

Extended boluses can appear in many forms — upon completion or at delivery start; with the normal and extended parts in separate rows or separate columns; with the extended portion labeled or not. This can cause a parser to silently misattribute dose amounts or timings. To ensure consistent parsing, extended boluses deserve special attention in the documentation. 

For boluses, please ensure:

- The timestamp is documented as referring to delivery **start** or **completion**
- The duration reflects early-stopped boluses accurately
- The delivery duration is always included
- The documentation explains if early stopped boluses (also pump suspend related) are reflected in the delivered dose

---

## Data Gaps

Data gaps create fundamental uncertainty: was the device off, disconnected, not uploading, or was the pump still running with no events to report? This ambiguity is compounded when only some data types are missing during a gap period (e.g., CGM is present but basal rates are absent).

A **watchdog signal** — a periodic heartbeat record from the device — would allow downstream tools to distinguish device inactivity from missing uploads. Documenting the minimum expected reporting frequency for each data type (e.g., "the pump reports at least one basal event per day") would also help.

Where data gaps are known and their cause is understood (e.g., a scheduled device download, a sensor warm-up period, or a planned device removal), **flag them explicitly with the reason**. This makes them distinguishable from gaps caused by unknown device failures or upload issues, which require different handling in downstream analysis.

### Study Period and Intervention Timeline

It is common to find data before or after the defined study period — collected during run-in phases, device familiarization, or post-study follow-up. Without context, researchers cannot tell whether this data is valid, should be excluded, or reflects a different treatment condition. Data outside the study period should either be removed before distribution or clearly labeled so it can be excluded.

Crossover studies are particularly challenging: each patient transitions between interventions, and the timing of these transitions varies per patient. Incorrectly attributing data to the wrong arm of a crossover can invalidate the analysis espceially when the data needs to be processed differently (see section on Basal Rates for an example.)

A per-patient record with should include the patient's start and stop datetimes of different study periods, along with the intervention types. This allows researchers to correctly interpret and trim the data without ambiguities.
---

## Validation Measures (TDD)

Providing **daily Total Daily Dose (TDD)** values — broken down by basal and bolus — is one of the most useful validation aids a dataset can include. Comparing extracted TDDs against a provider-supplied reference is an effective way for researchers to catch incorrect assumptions about basal rate handling early in their analysis.

- Ensure there is exactly one TDD value per patient per day.
- Document how basal TDD was calculated (e.g., whether it integrates delivered rates or uses a scheduled profile).

---

## Dataset History

Datasets are not static artifacts. Errors are discovered, data is added, and file schemas are updated — sometimes years after initial distribution. For downstream processing pipelines like BabelBetes, this introduces a silent but serious compatibility problem: a parser written against one version of a dataset may fail or produce incorrect results when run against a revised version.

BabelBetes currently supports exactly one version of each dataset. The retrieval date is documented in each dataset's page, and users are expected to obtain the same version. When datasets change, parsers may fail with an explicit error — or, in the case of schema changes, silently produce incorrect output.

A good example of how this can work well: in collaboration with JAEB, missing basal data was identified in one of their distributed datasets. JAEB promptly updated the dataset with complete basal records.

However, changes in the dataset can also introduce inconsistencies. Therefore, we recommend that dataset distributors maintain a **versioned release history**, similar to software release notes. This should include:

- A version identifier or release date for each dataset 
- A file hash
- A description of what changed (added data, corrected values, renamed columns, restructured files)
- Which files or columns were affected

Such a changelog would allow processing pipelines to detect version mismatches and prompt users to obtain the correct version before running — rather than failing silently or producing subtly wrong results.
