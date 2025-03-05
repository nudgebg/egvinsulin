# Babelbetes README
`Babelbetes` is a project designated to standardized public clinical diabetes data to support researchers, companies, and regulators around the world. 

Babelbetes is not only a script that extracts data from clinical studies. We've deliberately build it in a **modular** way including full traceability on the conducted analysis as well as a summary of findings and recommendations for researchers and investigators. Babelbetes provides:

 **1. Analaysis scripts and and documentation**  
 You can learn about the datasets and what chalanges came with normalizing tem by consulting the dataset summaries. You might also consult and review the jupyter notebooks that document our analysis.

 **2. Python modules**
 You can use the python modules to extract standardized continuous glucose monitor (CGM) and insulin pump data from the supported study datasets. Reuse the helper and drawing functions to work with the data.
  - Extend the functionality of existing study classes or add new implementations of the StudyDataset base class to support additional study datasets. 

 **3. Summary of learnings and recommendations**
Review the [recommendations](./recommendations.md) to understand what challenges we faced and learn how investigators can improve the data quality.

## Supported Studies
The goal is to work with as many clinical diabetes trial datasets as possible. At the moment, the following datasets from the diabetes [JAEB database](https://public.jaeb.org/datasets/diabetes) are supported. 

For each of these studies, we've spent hundreds of hours analyzing the data to ensure that the class correctly loads and extracts the data. Please refer to the study analysis pages for a summary of the analysis and findings that went into each dataset. While we operated with great care, some asumptions had to be made and other details remain unknown which are also documented.

|Our Analysis|JAEB|Retrieved Date|Folder Name *|Note|
|-|-|-|-|-|
|[Flair](./data_sets/FLAIR.md)|[JAEB](https://public.jaeb.org/dataset/566)| April 17th, 2024|FLAIRPublicDataSet|In the newest version (September, 2024) JAEB insulin pump data was removed from the study dataset.|
|[DCLP3](./data_sets/DCLP3.md)|[JAEB](https://public.jaeb.org/dataset/573)|April 17th, 2024|DCLP3 Public Dataset - Release 3 - 2022-08-04 |-|
|[DCLP5](./data_sets/DCLP5.md)|[JAEB](https://public.jaeb.org/dataset/535)|April 17th, 2024|DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53|-|
|[IOBP2](./data_sets/IOBP2.md)|[JAEB](https://public.jaeb.org/dataset/579)|April 17th, 2024|IOBP2 RCT Public Dataset|-|
|[PEDAP](./data_sets/PEDAP.md)|[JAEB](https://public.jaeb.org/dataset/599)|September, 26th, 2024|PEDAP Public Dataset - Release 3 - 2024-09-25|Our investigation resulted in this updated version with corrected patient ids.|
|[T1DEXI](./data_sets/T1DEXI.md)|[JAEB](https://public.jaeb.org/dataset/589)|October 1st, 2022|T1DEXI|-|
|[T1DEXIP](./data_sets/T1DEXIP.md)|[JAEB](https://public.jaeb.org/dataset/590)|March 16th, 2023|T1DEXIP|-|
|[REPLACE BG](./data_sets/REPLACE_BG.md)|[JAEB](https://public.jaeb.org/dataset/546)|February 2nd, 2025|REPLACE-BG Dataset-79f6bdc8-3c51-4736-a39f-c4c0f71d45e5|The currently hosted version misses the Basal file.|
|[Loop](./data_sets/LOOP.md)|[JAEB](https://public.jaeb.org/dataset/560)|September 2nd, 2024|Loop study public dataset 2023-01-31|-|

\* We have only tested our code on the respective versions. Therefore, the folder names are currently hard-coded and should match with the names above. 

## Data Standardization
The ultimate purpose of this toolbox is to bring CGM and insulin data into a common standardized format. We chose to abstract study datasets as objects. Each study class derives from the parent `StudyDataset` class and overrides methods to extract cgm, bolus and basal data. 

![](./assets/classes_Studies.svg)

Please refer to the [Code Reference](./reference.md) for more details. 

### Output Format
The StudyDataset base class defineds methods to extract cgm, basal and bolus data in standardized pandas dataframes of the following format. See the [StudyDataset](./reference.md/#studies.studydataset.StudyDataset) class documentation. All datetimes are expressed as https://en.wikipedia.org/wiki/Unix_time (seconds since 00:00:00 UTC on 1 January 1970). The pandas dataframes format is as follows:

#### Boluses
`bolus_history.csv`: These are all bolus delivery events as a event stream. Standard boluses are assumed to be commanded to be delivered immediately. Note we do not attempt to characterize when insulin was actually delivered, as each pump delivers commanded basal and bolus insulin in different ways.

| Column Name | Type| Description|
|----|----|----|
| `patient_id`       | `str`              | Patient ID|
| `datetime`         | `pd.Timestamp`     | Datetime of the bolus event  |
| `bolus`            | `float`            | Actual delivered bolus amount in units|
| `delivery_duration`| `pd.Timedelta`     | Duration of the bolus delivery|

#### Basal Rates
`basal_history.csv`: Event stream of basal rates. The basal rates are active until the next rate is reported. The rates account for temporaral basal adjustments and pump suspends as well as closed loop modes (e.g. by adding zero basal rate events). For pumps that do not distinguish between boluses and basals, this event stream is empty.

| Column Name  | Type| Description|
|----|----|----|
| `patient_id` | `str`              | Patient ID|
| `datetime`   | `pd.Timestamp`     | Datetime of the basal rate start  event|
| `basal_rate` | `float`            | Basal rate in units per hour|

#### CGM
`cgm_history.csv`: CGM values

| Column Name | Type| Description|
|----|----|----|
| `patient_id` | `str`              | Patient ID|
| `datetime`   | `pd.Timestamp`     | Datetime of the CGM measurement|
| `cgm`        | `float`            | Estimated Glucose Value in mg/dL|

## Using the toolbox
Here, we explain how to install the toolbox and how to use the `run_functions.py` script to extract standardized data from the supported studies. 

### Build the documentation (Optional)
This is the project README providing a condensed overview of the toolbox and how to use it. To access the full documentation, follow the installation instructions below and run mkdocs. Alternatively, you can download a pdf export `document.pdf` from the repository.

``` bash
> cd egvinsulin  # navigate to repository
> mkdocs serve   # run the local webserver, this will prompt a link
# open the link in the browser (e.g. http://127.0.0.1:8000)
```

### Setup Python
* Make sure you have python version > 3.X installed.
* We recommend using a python virtual environment (see [Python setup instructions](python-setup.md))

### Installation
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

### Prepare the raw data
 1. Download the study data zip files from [jaeb.org](https://public.jaeb.org/datasets/diabetes) (see [supported studies](#supported-studies)).
 2. Extract and move the folders inside the `data/raw` directory. Do not rename the folder names, otherwise the `run_functions.py` won't know how to process them.
 3. Depending on which studies you downloaded, the folder structure should look something like this.
```
    egvinsulin/
    ├── data/
    │   └── raw/
    │       └── FLAIRPublicDataSet
    │       └── DCLP3 Public Dataset - Release 3 - 2022-08-04
    │       └── IOBP2 RCT Public Dataset
    └── run_functions.py
```

### Run run_functions.py to batch Extract data
The `run_functions.py` script is the entry point for users that simply want to extract standardized data from the supported studies. It performs data extraction and standarization. For each folder in the `data/raw` directory the script: 
 1. Identifies the appropriate handler class (see [supported studies](#supported-studies))
 2. Loads the study data
 3. Extracts bolus, basal, and CGM event histories to a standardized Format (see [output-format](#output-format))
 4. Saves the extracted data in CSV format. 

Example terminal output:
``` bash
> python run_functions.py
[15:26:22] Looking for study folders in /data/raw and saving results to /data/out
[15:26:22] Start processing supported study folders:
[15:26:22] 'T1DEXI' using T1DEXI class
[15:26:22] 'REPLACE-BG Dataset-79f6bdc8-3c51-4736-a39f-c4c0f71d45e5' using ReplaceBG class
...
[15:26:22] Processing T1DEXI ...
[15:26:56] [x] Data loaded
[15:26:56] [x] Boluses extracted
[15:27:00] [x] Basal extracted
[15:27:12] [x] CGM extracted
[15:27:12] T1DEXI completed in 49.96 seconds.
...
Processing complete.
```

### Execution Times
These are approximate execution times   

||MacBook Pro M3|
|----|----|
|Flair|97.80 seconds|
|IOBP2|103.07 seconds|
|PEDAP|35.07 seconds|
|DCLP3|36.16 seconds|
|DCLP5|54.64 seconds|
|T1DEXI|49.96 seconds|
|T1DEXIP|9.99 seconds|
|Replace BG|61.38 seconds|
|Loop|587.22 seconds*|

\* Loop raw data files are very large which requires the use of `dask`. `dask` builds upon pandas and processes chunks of the data in parallel. However, the routine to save the data to csv - at the moment - still requires the whole dataframe to be loaded before storing it which might fail if your machine has insufficient memory. We will change this in the future.


## Troubleshooting
- Ensure the raw data folders are named correctly to match the patterns in the script. You shouldn't need to rename the folders after you extracted the study datasets from jaeb.
- Check the console output for any warning or error messages.
