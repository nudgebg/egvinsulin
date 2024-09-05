# egvinsulin

## Overview

This project processes clinical diabetes study datasets, extracts glucose and insulin event histories in a standardized format (extraction) and additionally transforms the data into time aligned, and 5 minute resampled time series data (transform). The main script for running these operations is `run_functions.py`.

### Supported Studies

https://public.jaeb.org/datasets/diabetes

**FLAIR** - Fuzzy Logic Automated Insulin Regulation: A Crossover Study Comparing Two Automated Insulin Delivery System Algorithms (PID vs. PID + Fuzzy Logic) in Individuals with Type 1 Diabetes, NCT03040414, FLAIRPublicDataSet.zip, Retrieved April 17th, 2024 

**IOBP2** - The Insulin-Only Bionic Pancreas Pivotal Trial: Testing the iLet in Adults and Children with Type 1 Diabetes,	NCT04200313, IOBP2 RCT Public Dataset.zip, Retrieved April 17th, 2024


## Prerequisites
- Python 3.x
- pip (Python package installer)
- Required Python packages listed in `requirements.txt`

## Usage

1. **Clone the repository:**
    ```sh
    git clone git@github.com:nudgebg/egvinsulin.git
    ```

2. **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

3. **Prepare the raw data:**
    - Download the study data files from https://public.jaeb.org/datasets/diabetes
    extract and move them inside the `data/raw` directory. 
    - Ensure the folder names match the patterns defined in the `patterns` dictionary in `run_functions.py`

4. **Run the script:**
    ```sh
    python run_functions.py
    ```

5. **Check the output:**
    - Processed data will be saved in the `data/out` directory, organized by study folder names and further divided into `extracted` and `transformed` subdirectories.


## Source Overview

### Directory Structure

- `studies` Contains modules for handling different study datasets.
- `src`: Contains source code for postprocessing and saving data.
- `data/raw` Directory where raw study data should be placed.
- `data/out`: Directory where processed data will be saved.
- `run_functions.py`: This script performs the data normalization and transformation
    - For each folder, it identifies the appropriate handler class based on predefined patterns.
    - Loads the study data using the handler class.
    - Extracts bolus, basal, and CGM event histories.
    - Saves the extracted data in CSV format.
    - Transforms the extracted data.
    - Saves the transformed data in CSV format.

## Troubleshooting
- Ensure the raw data folders are named correctly to match the patterns in the script. You shouldn't need to rename the folders after you extracted the study datasets from jaeb.
- Check the console output for any warning or error messages.



