"""
run_functions.py

This script performs data normalization on raw study data found in the `data/raw` directory.

Execution:
    python run_functions.py

Process Overview:
1. Identifies the appropriate handler class (subclass of studydataset) for each folder in the `data/raw` directory (see supported studies).
2. Loads the study data into memory.
3. Extracts bolus, basal, and CGM event histories into a standardized format (see Output Format).
4. Saves the extracted data as CSV files.

## Output format:
The outptut format is standardized across all studies and follows the definitions of the studydataset base class.

### Boluses

`bolus_history.csv`: Event stream of all bolus delivery events. Standard boluses are assumed to be delivered immediately.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the bolus event               |
  | bolus             | float          | Actual delivered bolus amount in units    |
  | delivery_duration | pd.Timedelta   | Duration of the bolus delivery            |


### Basal Rates

`basal_history.csv: `Event stream of basal rates, accounting for temporary basal adjustments, pump suspends, and closed-loop modes. The basal rates are active until the next rate is reported.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the basal rate start event    |
  | basal_rate        | float          | Basal rate in units per hour              |


### CGM (Continuous Glucose Monitor)

`cgm_history.csv`: Event stream of CGM values.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the CGM measurement           |
  | cgm               | float          | CGM value in mg/dL                        |

### Output Files:
For each study, the dataframes are saved in the `data/out/<study-name>/` folder:
 - To reduce file size, the data is saved in a compressed format using the `gzip`
 - datetimes and timedeltas are saved as unix timestamps (seconds) and integers (seconds) respectively.
 - boluses and basals are rounded to 4 decimal places
 - cgm values are converted to integers

"""
import os
from studies import IOBP2,Flair,PEDAP,DCLP3,DCLP5,Loop,StudyDataset,T1DEXI,T1DEXIP, ReplaceBG

import src.postprocessing as pp
from src.logger import Logger
from datetime import datetime
from tqdm import tqdm
import argparse
from time import time

logger = Logger.get_logger(__file__)

def current_time():
  return datetime.now().strftime("%H:%M:%S")


def main(load_subset=False):
  """
  Main function to process study data folders.

  Args:
    load_subset (bool): If True, runs the script on a limited amount of data (e.g. skipping rows)
  
  Logs:
    - Information about the current working directory and paths being used.
    - Warnings for folders that do not match any known study patterns.
    - Errors if no supported studies are found.
    - Progress of processing each matched study folder.
  
  The function performs the following steps:
    1. Determines the input and output paths based on the `test` flag.
    2. Identifies study folders in the input path.
    3. Matches study folders to predefined patterns and logs unmatched folders.
    4. Processes each matched study folder and logs the progress using `tqdm`.
  """

  #run_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
  current_dir = os.getcwd()
  in_path = os.path.join(current_dir, 'data/raw')
  out_path = os.path.join(current_dir, 'data/out')

  if load_subset:
     logger.warning(f"ATTENTION: --test was provided: Running in test mode using a subset of the data.")

  logger.info(f"Looking for study folders in {in_path} and saving results to {out_path}")

  #define how folders are identified and processed
  patterns = {'IOBP2 RCT Public Dataset': IOBP2,
              'FLAIRPublicDataSet': Flair,
              'PEDAP Public Dataset - Release 3 - 2024-09-25': PEDAP,
              'DCLP3 Public Dataset - Release 3 - 2022-08-04': DCLP3,
              'DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53': DCLP5,
              'Loop study public dataset 2023-01-31': Loop,
              'T1DEXI': T1DEXI,
              'T1DEXIP': T1DEXIP,
              'REPLACE-BG Dataset-79f6bdc8-3c51-4736-a39f-c4c0f71d45e5': ReplaceBG}

  # Filter and log folders that cannot be matched
  study_folder_names = [f for f in os.listdir(in_path) if os.path.isdir(os.path.join(in_path, f))]
  unmatched_folders = []
  matched_folders = []

  for folder in study_folder_names:
      study_class = None
      for pattern, handler in patterns.items():
          if pattern == folder:
              study_class = handler
              matched_folders.append((folder, study_class))
              break
      if study_class is None:
          unmatched_folders.append(folder)
  
  if unmatched_folders:
      logger.warning(f"The folders '{unmatched_folders}' are not recognized as a supported studies. Did you accidentally rename them? Please check the documentation for supported studies.")
  if not matched_folders:
      logger.error("No supported studies found in the data/raw folder. Exiting.")
      exit()

  # Process matched folders with progress indicators
  logger.info(f"Start processing supported study folders:")
  for i,(folder, study_class) in enumerate(matched_folders):
      logger.info(f'\'{folder}\' using {study_class.__name__} class')
  logger.info("")

  num_steps_per_folder = 4
  with tqdm(total=len(matched_folders)*num_steps_per_folder, desc=f"Processing studies", bar_format='Step {n_fmt}/{total_fmt} [{desc}]:|{bar}', unit="step", leave=False) as progress:
    for folder, study_class in matched_folders:
      tqdm.write(f"[{current_time()}] Processing {folder} ...")
      
      study_output_path = os.path.join(out_path, folder)
      if not os.path.exists(study_output_path):
          os.makedirs(study_output_path)
      
      start_time = time()
      study = study_class(study_path=os.path.join(in_path, folder))
      process_folder(study, study_output_path, progress, load_subset=load_subset)
      tqdm.write(f"[{current_time()}] {folder} completed in {time() - start_time:.2f} seconds.")

    tqdm.write("Processing complete.")

def process_folder(study: StudyDataset, out_path_study, progress, load_subset):
      """Processes the data for a given study by loading, extracting, and resampling bolus, basal, and glucose events.

        Args:
          study (object): An instance of a study class that contains methods to load and extract data.
          out_path_study (str): The output directory path where the processed data will be saved.
          progress (tqdm): A tqdm progress bar object to display the progress of the processing steps.
        
        Steps:
          1. Loads the study data.
          2. Extracts bolus event history and saves it as a CSV file.
          3. Extracts basal event history and saves it as a CSV file.
          4. Extracts continuous glucose monitoring (CGM) history and saves it as a CSV file.
          Each step updates the progress bar and logs the current status.
        """
      progress.set_description_str(f"{study.__class__.__name__}: (Loading data)")
      study.load_data(subset=load_subset)
      progress.update(1)
      tqdm.write(f"[{current_time()}] [x] Data loaded"); 

      #boluses
      progress.set_description_str(f"{study.__class__.__name__}: Extracting boluses")
      study.save_bolus_event_history_to_file(out_path_study,True)
      progress.update(1)
      tqdm.write(f"[{current_time()}] [x] Boluses extracted"); 

      #basals
      progress.set_description_str(f"{study.__class__.__name__}: Extracting basals")
      study.save_basal_event_history_to_file(out_path_study, True)
      progress.update(1)
      tqdm.write(f"[{current_time()}] [x] Basal extracted"); 

      #cgm
      progress.set_description_str(f"{study.__class__.__name__}: Extracting glucose")
      study.save_cgm_to_file(out_path_study, True)
      progress.update(1); tqdm.write(f"[{current_time()}] [x] CGM extracted"); 
      

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Run data normalization on raw study data.")
  parser.add_argument('--test', action='store_true', help="Run the script in test mode using test data.")
  args = parser.parse_args()
  main(load_subset=args.test)