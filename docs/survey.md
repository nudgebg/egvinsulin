# Output Survey

The survey framework computes quality metrics over a BabelBetes output directory and generates an HTML report. It is built around *surveys* — immutable Parquet files that capture patient and study metric aggregates at a point in time. This is useful to describe and compare study outputs as well as to check for (un)intended changes in the output for example after making changes to the code base.

---

## Usage

### Compute and report

```bash
# Compute all metrics and save a survey
python -m babelbetes.survey survey --data-dir data/out

# Generate an HTML report from the latest survey
python -m babelbetes.survey report

# Include circadian and gap/chunk figures (requires raw time series data)
python -m babelbetes.survey report --data-dir data/out
```

!!! note "Why `--data-dir` is optional for `report`"
    Most figures are generated from the pre-computed survey files.
    `--data-dir` is only needed for figures that cannot be computed from aggregated stats:
    **circadian patterns** (moving average by hour of day) and **gap/chunk CDFs** —
    both require access to individual timestamps.

Surveys are saved to `data/out/survey/surveys/` and the HTML report is written to `data/out/survey/reports/report_<timestamp>.html`.

### Track changes with `diff`

```bash
# Compare the two most recent surveys — flags changes > 5%
python -m babelbetes.survey diff

# Or compare two specific surveys
python -m babelbetes.survey diff \
    --a data/out/survey/surveys/20250101_000000_study_stats.parquet \
    --b data/out/survey/surveys/20250201_000000_study_stats.parquet
```

The diff covers all study-level metrics, including the per-patient aggregates (e.g. `tir_study_gm` — geometric mean of individual patient TIR values across a study). Metrics that changed by more than 5% are flagged with `⚠️`.

!!! note
    The diff currently operates on study-level surveys only. Patient-level diffing is not yet implemented.

### Explore a single study or patient

For targeted exploration without saving a survey, call the compute functions directly:

```python
from babelbetes.src import data_store
from babelbetes.survey import compute
import pandas as pd

# Scope to one study, or filter further to one patient
store = data_store.load("data/out", studies=["DCLP3"])
store = {dt: df[df["patient_id"] == "P001"] for dt, df in store.items()}

patient_records = (
    compute.compute_cgm_stats(store["cgm"])
    + compute.compute_basal_stats(store["basal"])
    + compute.compute_bolus_stats(store["bolus"])
    + compute.compute_complete_days(store)
)
tdd_df      = compute.compute_tdd_per_patient(store)
tdd_records = compute.compute_tdd_stats(tdd_df)

stats = pd.DataFrame(patient_records + tdd_records)
print(stats[stats["data_type"] == "cgm"].pivot_table(
    index="patient_id", columns="metric", values="value"
))
```

---

## Architecture

The framework is split into four modules:

| Module | Responsibility |
|---|---|
| `compute` | Pure functions that take DataFrames and return metrics as `list[dict]` |
| `survey` | Save and load metric surveys as Parquet files |
| `figures` | Matplotlib/seaborn figures that accept pre-computed metric DataFrames |
| `diff` | Compare two study-level surveys and flag significant changes |

`__main__.py` wires these together for the CLI. The `report` module renders surveys into a self-contained HTML file.

Metrics are stored in **long format** — one row per `(study, [patient_id,] data_type, metric, value)` — so any metric can be filtered, pivoted, or plotted without schema changes.

### Survey files

Each `survey` run produces four Parquet files, all stamped with the same `YYYYMMDD_HHMMSS` timestamp:

| File | Contents |
|---|---|
| `<ts>_study_stats.parquet` | Study-level aggregates: columns `study`, `data_type`, `metric`, `value`, `survey_id` |
| `<ts>_patient_stats.parquet` | Per-patient metrics: columns `study`, `patient_id`, `data_type`, `metric`, `value`, `survey_id` |
| `<ts>_tdd.parquet` | Daily TDD per patient: columns `study`, `patient_id`, `date`, `basal`, `bolus`, `total`, `survey_id` |
| `<ts>_cdf_quantiles.parquet` | Pre-computed CDF quantiles: columns `study`, `data_type`, `quantile_level`, `value`, `survey_id` |

### Metrics reference

**Per-patient metrics** (in `patient_stats`) — present for each of `cgm`, `basal`, `bolus`:

| Metric | Description |
|---|---|
| `row_count` | Total rows including NaN |
| `nan_count` | Rows with a missing value |
| `duplicate_count` | Rows with a duplicated timestamp |
| `min`, `max` | Range of non-NaN values |
| `gm`, `gs` | Geometric mean and std of non-NaN values |
| `patient_days` | Number of unique calendar days with at least one measurement |
| `data_fraction_days` | `patient_days / calendar_span` (0–1) |
| `missing_days` | Calendar days in the span with no data |
| `samples_per_day` | `row_count / calendar_span` |
| `data_fraction` | Fraction of the total timespan covered by chunks |
| `chunk_count` | Number of continuous data segments |
| `gm_chunk_dur_hrs`, `gs_chunk_dur_hrs` | Geometric mean/std of chunk durations (hours) |
| `gm_gap_dur_hrs`, `gs_gap_dur_hrs` | Geometric mean/std of gap durations (hours) |

CGM-specific additions:

| Metric | Description |
|---|---|
| `tir` | Time-in-range fraction (70–180 mg/dL) |
| `tar` | Time-above-range fraction (> 180 mg/dL) |
| `tbr` | Time-below-range fraction (< 70 mg/dL) |
| `outlier_low` | Count of readings < 40 mg/dL |
| `outlier_high` | Count of readings > 400 mg/dL |

Gap thresholds used to split continuous chunks: CGM = 30 min, basal = 6 hr, bolus = 16 hr.

**TDD metrics** (in `patient_stats`, `data_type="tdd"`):

`basal_gm`, `basal_gs`, `basal_min`, `basal_max`, `basal_nan_count`, `bolus_gm`, `bolus_gs`, `bolus_min`, `bolus_max`, `bolus_nan_count`, `tdd_gm`, `tdd_gs`, `tdd_min`, `tdd_max`, `tdd_nan_count`, `bolus_basal_ratio`.

**Study-level metrics** (in `study_stats`):

Every per-patient metric is aggregated across patients as a geometric mean (`_study_gm`) and geometric std (`_study_gs`). Additionally:

| Metric | Description |
|---|---|
| `patient_count` | Number of patients per `(study, data_type)` |
| `patient_days` | Sum of per-patient `patient_days` |
| `complete_days` | Sum of days where CGM + bolus + basal all present |
| `age_min`, `age_max`, `age_gm`, `age_std` | Age statistics (when age data is available) |

!!! note "NaN in study-level stats"
    `_study_gs` is NaN for studies with a single patient (std is undefined for n=1).
    `_study_gm` for metrics that are zero or negative for all patients (e.g. `duplicate_count`)
    will be absent from the output — geometric mean requires positive values.

---

## API Reference

::: babelbetes.survey.compute

::: babelbetes.survey.figures

::: babelbetes.survey.survey

::: babelbetes.survey.diff
