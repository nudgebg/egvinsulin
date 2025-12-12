# File: run_functions.py
# Author Jan Wrede, Rachel Brandt
# Copyright (c) 2025 nudgebg
# Licensed under the MIT License. See LICENSE file for details.
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
from babelbetes.studies import StudyDataset, dataset_initializer
import babelbetes.src.postprocessing as pp
from babelbetes.src.logger import Logger
from babelbetes.src.file_saver import save_dataframe, cleanup_study_output
from datetime import datetime
from tqdm import tqdm
import argparse
from time import time

logger = Logger.get_logger(__file__)

def current_time():
  return datetime.now().strftime("%H:%M:%S")

def main(load_subset=False, remove_repetitive=True, compressed=False, input_dir=None, output_dir=None, studies=None, data_types=None):
  """
  Main function to process study data folders.

  Args:
    load_subset (bool): If True, runs the script on a limited amount of data (e.g. skipping rows).
    compressed (bool): Whether to compress the output files.
    input_dir (str): Custom input directory path. Defaults to 'data/raw'.
    output_dir (str): Custom output directory path. Defaults to 'data/out'.
    studies (list): List of study names to process. If None, all available studies will be processed.
                   Available studies: IOBP2, Flair, PEDAP, DCLP3, DCLP5, ReplaceBG, Loop, T1DEXI, T1DEXIP
    data_types (list): List of data types to extract ['cgm', 'bolus', 'basal']. If None, all types are extracted.
  
  Logs:
    - Information about the current working directory and paths being used.
    - Warnings for folders that do not match any known study patterns.
    - Errors if no supported studies are found.
    - Progress of processing each matched study folder.
  """
  current_dir = os.getcwd()
  in_path = input_dir if input_dir else os.path.join(current_dir, 'data', 'raw')
  out_path = output_dir if output_dir else os.path.join(current_dir, 'data', 'out')

  if not os.path.exists(out_path):
    os.makedirs(out_path)
      
  if load_subset:
     logger.warning(f"ATTENTION: --test was provided: Running in test mode using a subset of the data.")

  logger.info(f"Looking for studies in  {in_path}")
  logger.info(f"Output will be saved to {out_path}")
  all_initialized_studies = dataset_initializer.initialize_datasets(in_path)
  
  # Filter studies if specific studies are requested
  if studies is not None:
    if not isinstance(studies, list):
      studies = [studies]  # Convert single string to list
    
    # Filter to only include requested studies
    filtered_studies = {name: study for name, study in all_initialized_studies.items() if name in studies}
    
    # Check if any requested studies were not found
    available_studies = set(all_initialized_studies.keys())
    requested_studies = set(studies)
    missing_studies = requested_studies - available_studies
    
    if missing_studies:
      logger.warning(f"Requested studies not found: {list(missing_studies)}")
      logger.info(f"Available studies: {list(available_studies)}")
    
    if not filtered_studies:
      logger.error("No requested studies were found. Exiting.")
      return
    
    initialized_studies = list(filtered_studies.values())
    logger.info(f"Processing only requested studies: {list(filtered_studies.keys())}")
  else:
    initialized_studies = list(all_initialized_studies.values())
    logger.info(f"Processing all available studies: {list(all_initialized_studies.keys())}")
  
  # Validate and process data_types parameter
  available_data_types = ['cgm', 'bolus', 'basal']
  if data_types is not None:
    if not isinstance(data_types, list):
      data_types = [data_types]  # Convert single string to list
    
    # Validate data types
    invalid_types = [dt for dt in data_types if dt not in available_data_types]
    if invalid_types:
      logger.error(f"Invalid data types: {invalid_types}. Available types: {available_data_types}")
      return
    
    logger.info(f"Processing only requested data types: {data_types}")
  else:
    data_types = available_data_types
    logger.info(f"Processing all data types: {data_types}")

  # Process matched folders with progress indicators
  logger.info(f"Start processing:")
  
  
  with tqdm(total=len(initialized_studies), desc=f"Processing studies", bar_format='Study {n_fmt}/{total_fmt} [{desc}]:|{bar}', unit="studies", leave=False) as progress:
    global_start_time = time()
    for study in initialized_studies:
      tqdm.write(f"[{current_time()}] {study.study_name} ...")
      
      # Clean up existing output for this study
      removed_paths = cleanup_study_output(out_path, study.study_name, data_types)
      if removed_paths:
        tqdm.write(f"[{current_time()}] Cleaned up existing output: {len(removed_paths)} items removed")
      
      start_time = time()
      try:
         process_folder(study, out_path, progress, load_subset=load_subset, remove_repetitive=remove_repetitive, compressed=compressed, data_types=data_types)
      except Exception as e:
          tqdm.write(f"[{current_time()}] Error processing {study.study_name}: {e}")
          logger.error(f"Error processing {study.study_name}: {e} \n" \
                       "Please make sure that you have the supported study dataset release. \n" \
                        "In some cases, newer or older versions of the data are incomtaible. \n" \
                        "Please check the README file for supported study datasets and releases. \n" \
                        "If you continue having issues, we are happy to help.")
          
          
      progress.update(1)
      tqdm.write(f"[{current_time()}] {study.study_name} completed in {time() - start_time:.2f} seconds.")

    tqdm.write(f"Processing completed in {time() - global_start_time:.2f} seconds.")

def process_folder(study: StudyDataset, out_path_study, progress, load_subset, remove_repetitive, compressed, data_types):
      """Processes the data for a given study by loading, extracting, and resampling bolus, basal, and glucose events.

        Args:
          study (object): An instance of a study class that contains methods to load and extract data.
          out_path_study (str): The output directory path where the processed data will be saved.
          progress (tqdm): A tqdm progress bar object to display the progress of the processing steps.
          compressed (bool): Whether to compress the output files.
          data_types (list): List of data types to extract ['cgm', 'bolus', 'basal'].
        
        Steps:
          1. Loads the study data.
          2. Extracts the requested data types and saves them as parquet files.
          Each step updates the progress bar and logs the current status.
        """
      progress.set_description_str(f"{study.__class__.__name__}: (Loading data)")
      study.load_data(subset=load_subset)
      tqdm.write(f"[{current_time()}] [x] Data loaded"); 

      # Process each requested data type
      if 'bolus' in data_types:
          progress.set_description_str(f"{study.__class__.__name__}: Extracting boluses")
          df = study.extract_bolus_event_history()
          save_dataframe(df, out_path_study, "parquet", compressed, study.study_name, 'bolus')
          tqdm.write(f"[{current_time()}] [x] Boluses extracted"); 

      if 'basal' in data_types:
          progress.set_description_str(f"{study.__class__.__name__}: Extracting basals")
          df = study.extract_basal_event_history()
          if remove_repetitive:
             progress.set_description_str(f"{study.__class__.__name__}: Removing repetitive basals")
             df = df.groupby(StudyDataset.COL_NAME_PATIENT_ID).apply(pp.drop_repetitive_basals,include_groups=False).reset_index(level=0)
          save_dataframe(df, out_path_study, "parquet", compressed, study.study_name, 'basal')
          tqdm.write(f"[{current_time()}] [x] Basal extracted"); 

      if 'cgm' in data_types:
          progress.set_description_str(f"{study.__class__.__name__}: Extracting glucose")
          df = study.extract_cgm_history()
          save_dataframe(df, out_path_study, "parquet", compressed, study.study_name, 'cgm')
          tqdm.write(f"[{current_time()}] [x] CGM extracted"); 
      

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Run data normalization on raw study data.")
  parser.add_argument('--test', action='store_true', help="Run the script in test mode using test data.")
  parser.add_argument('--compressed', action='store_true', help="Enable compression for the output files.")
  parser.add_argument('--input-dir', type=str, help="Specify a custom input directory. Defaults to 'data/raw'.")
  parser.add_argument('--output-dir', type=str, help="Specify a custom output directory. Defaults to 'data/out'.")
  parser.add_argument('--remove-repetitive', action='store_true', help="Remove repetitive values from the basal output dataframes.")
  parser.add_argument('--studies', nargs='*', help="Specify which studies to process. Available: IOBP2, Flair, PEDAP, DCLP3, DCLP5, ReplaceBG, Loop, T1DEXI, T1DEXIP. If not specified, all available studies will be processed.")
  parser.add_argument('--data-types', nargs='*', choices=['cgm', 'bolus', 'basal'], help="Specify which data types to extract. Available: cgm, bolus, basal. If not specified, all data types will be extracted.")
  args = parser.parse_args()

  logger.info(f"Using arguments:")
  for arg, value in vars(args).items():
      logger.info(f"  {arg}: {value}")
  main(load_subset=args.test, remove_repetitive=args.remove_repetitive, compressed=args.compressed, input_dir=args.input_dir, output_dir=args.output_dir, studies=args.studies, data_types=args.data_types)