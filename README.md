# Babelbetes README
`Babelbetes` is a set of python functions that extract and transform glucose and insulin data from publicly available diabetes study datasets available at jaeb.org into a common format to support researchers, companies and regulators around the world.

### Full Documentation
Below is the project readme providing a condensed overview of the toolbox and how to use it. The full documentation is built using mkdocs. Unless the ([Full Documentation ](index.md) including the [Code Reference](reference.md)) is hosted on the server that you are reading this readme, some of the following links might not work. To access the full documentation, install the following the instructions below, navigate to the repository folder, and run mkdocs:
``` bash
> cd egvinsulin  # navigate to repository
> mkdocs serve   # run the local webserver, this will prompt a link
# open the link in the browser (e.g. http://127.0.0.1:8000)
```


## Supported Studies
The goal is to work with as many clinical diabetes trial datasets as possible. At the moment, the following datasets are supported.
https://public.jaeb.org/datasets/diabetes

 - [x] **FLAIR** - Fuzzy Logic Automated Insulin Regulation: A Crossover Study Comparing Two Automated Insulin Delivery System Algorithms (PID vs. PID + Fuzzy Logic) in Individuals with Type 1 Diabetes, NCT03040414, FLAIRPublicDataSet.zip, Retrieved April 17th, 2024 
 - [x] **IOBP2** - The Insulin-Only Bionic Pancreas Pivotal Trial: Testing the iLet in Adults and Children with Type 1 Diabetes,	NCT04200313, IOBP2 RCT Public Dataset.zip, Retrieved April 17th, 2024

### Setup Python
* Make sure you have python version > 3.X installed.
* We recommend using a python virtual environment (see [Python setup instructions](python-setup.md))

### Install Bebelbetes
1. **Clone the repository:**
    ```sh
    git clone git@github.com:nudgebg/egvinsulin.git
    ```
2. Install all dependencies (we recommend using a python virtual environment (see [Python setup instructions](python-setup.md))
* In your terminal, navigate to the repository
* (Optional) activate your python virtual environment 
* Run this command to install all packages required by bebelbetes
```bash 
pip install -r requirements.txt
```

### 2. Download and Prepare the raw data
 1. Download the study data files from [jaeb.org](https://public.jaeb.org/datasets/diabetes) (see [supported studies](#supported-studies)).
 2. Extract and move the folders inside the `data/raw` directory. Do not rename the folder names, otherwise the `run_functions.py` won't know how to process them.
 3. Depending on which studies you downloaded, the folder structure should look something like this.
```
    egvinsulin/
    ├── data/
    │   └── raw/
    │       └── FLAIRPublicDataSet
    │       └── DCLP3 Public Dataset - Release 3 - 2022-08-04
    │       └── DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53
    │       └── IOBP2 RCT Public Dataset
    └── run_functions.py
```

### 3. Running run_functions.py

```sh
python run_functions.py
```
This will perform the data normalization. For each folder in the `data/raw` directory it 
 1. identifies the appropriate handler class (see [supported studies](#supported-studies))
 2. Loads the study data
 3. Extracts bolus, basal, and CGM event histories ito standardized Format (see [Output Format](#output-format))
 4. Saves the extracted data in CSV format.
 5. Resamples and time-alignes basal and bolus into 5 minute equivalent deliveries.
 6. Saves the transformed data in CSV format.

For each study, the basal, bolus and cgm event histories are extracted and saved in a standardized format as .csv files, along with a resampled and time-aligned version, to the `data/out/<study-name>/` folder. See [output format](#output-format).

Example output:
``` bash
> python run_functions.py
[19:00:14] Looking for study folders in /<...>/egvinsulin/data/raw and saving results to /<...>/egvinsulin/data/out
[19:00:14] Start processing supported study folders: ['FLAIRPublicDataSet', 'IOBP2 RCT Public Dataset']

[19:00:14] Processing FLAIRPublicDataSet ... 
[19:01:10] [x] Data loaded 
[19:01:49] [x] Boluses extracted: bolus_history.csv
[19:07:07] [x] Boluses resampled: bolus_history-transformed.csv
[19:07:37] [x] Basal events extracted: basal_history.csv 
[19:09:46] [x] Basal events resampled: basal_history-transformed.csv
[19:09:58] [x] CGM extracted: cgm_history.csv
[19:12:36] [x] CGM resampled: cgm_history-transformed.csv

[19:12:36] Processing IOBP2 RCT Public Dataset ... 
[19:13:20] [x] Data loaded 
[19:14:52] [x] Boluses extracted: bolus_history.csv
[19:27:55] [x] Boluses resampled: bolus_history-transformed.csv
[19:27:55] [x] Basal events extracted: basal_history.csv 
[19:27:55] [x] Basal events resampled: basal_history-transformed.csv
[19:28:10] [x] CGM extracted: cgm_history.csv
[19:31:58] [x] CGM resampled: cgm_history-transformed.csv
Processing complete. 
```

## Execution Times
These are approximate execution times (without parallelization).
||MacBook Pro M3|
|----|----|
|Flair|12 min|
|IOBP2|20 min|

## Output Format
### Boluses
`bolus_history.csv`: These are all bolus delivery events as a event stream. Standard boluses are assumed to be delivered immediately. 

| Column Name | Type| Description|
|----|----|----|
| `patient_id`       | `str`              | Patient ID|
| `datetime`         | `pd.Timestamp`     | Datetime of the bolus event  |
| `bolus`            | `float`            | Actual delivered bolus amount in units|
| `delivery_duration`| `pd.Timedelta`     | Duration of the bolus delivery   |

`bolus_history-transformed.csv`:Actual bolus insulin deliveries time-aligned at midnight and resampled to 5 minutes. This combines immediate and extended boluses. 

| Column Name | Type| Description|
|----|----|----|
| `datetime`  | `pd.Timestamp` | Datetime of the bolus event  |
| `bolus`     | `float`        | Actual delivered bolus amount in units |

### Basal Rates
`basal_history.csv`: Event stream of basal rates. The basal rates are active until the next rate is reported. The rates account for temporaral basal adjustments and pump suspends as well as closed loop modes (e.g. by adding zero basal rate events). For pumps that do not distinguish between boluses and basals, this event stream is empty.

| Column Name  | Type| Description|
|----|----|----|
| `patient_id` | `str`              | Patient ID|
| `datetime`   | `pd.Timestamp`     | Datetime of the basal rate start  event|
| `basal_rate` | `float`            | Basal rate in units per hour|


`basal_history-transformed.csv`: Basal rate equivalent insulin deliveries, time-aligned at midnight, resampled at 5 minutes.

| Column Name | Type| Description|
|----|----|----|
| `datetime`       | `pd.Timestamp` | Datetime of the basal event  |
| `basal_rate`     | `float`        | Basal rate in units/hour |
| `basal_delivery` | `float`        | Basal rate equivalent delivery amount in units|

### CGM
`cgm_history.csv`: CGM values

| Column Name | Type| Description|
|----|----|----|
| `patient_id` | `str`              | Patient ID|
| `datetime`   | `pd.Timestamp`     | Datetime of the CGM measurement|
| `cgm`        | `float`            | CGM value in mg/dL|


`cgm_history-transformed.csv`: CGM values time-aligned at midnight and resampled at 5 minutes.

| Column Name | Type| Description|
|----|----|----|
| `datetime`  | `pd.Timestamp` | Datetime of the CGM measurement|
| `cgm`       | `float`        | CGM value in mg/dL|



## Troubleshooting
- Ensure the raw data folders are named correctly to match the patterns in the script. You shouldn't need to rename the folders after you extracted the study datasets from jaeb.
- Check the console output for any warning or error messages.