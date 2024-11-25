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
5. Resamples and time-aligns basal and bolus deliveries into 5-minute equivalent intervals.
6. Saves the resampled and aligned data in CSV format.

## Output format:
The outptut format is standardized across all studies and follows the definitions of the studydataset base class.
For each study, the following files are saved in the `data/out/<study-name>/` folder:

### Boluses

`bolus_history.csv`: Event stream of all bolus delivery events. Standard boluses are assumed to be delivered immediately.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the bolus event               |
  | bolus             | float          | Actual delivered bolus amount in units    |
  | delivery_duration | pd.Timedelta   | Duration of the bolus delivery            |

`bolus_history-transformed.csv`: Actual bolus insulin deliveries time-aligned at midnight and resampled to 5-minute intervals. This combines immediate and extended boluses.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | datetime          | pd.Timestamp   | Datetime of the bolus event               |
  | bolus             | float          | Actual delivered bolus amount in units    |

### Basal Rates

`basal_history.csv: `Event stream of basal rates, accounting for temporary basal adjustments, pump suspends, and closed-loop modes. The basal rates are active until the next rate is reported.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the basal rate start event    |
  | basal_rate        | float          | Basal rate in units per hour              |

`basal_history-transformed.csv`: Basal rate equivalent insulin deliveries, time-aligned at midnight, and resampled at 5-minute intervals.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | datetime          | pd.Timestamp   | Datetime of the basal event               |
  | basal_rate        | float          | Basal rate in units per hour              |
  | basal_delivery    | float          | Basal rate equivalent delivery amount in units |

### CGM (Continuous Glucose Monitor)

`cgm_history.csv`: Event stream of CGM values.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | patient_id        | str            | Patient ID                                |
  | datetime          | pd.Timestamp   | Datetime of the CGM measurement           |
  | cgm               | float          | CGM value in mg/dL                        |

`cgm_history-transformed.csv`: CGM values time-aligned at midnight and resampled at 5-minute intervals.

  | Column Name       | Type           | Description                               |
  |-------------------|----------------|-------------------------------------------|
  | datetime          | pd.Timestamp   | Datetime of the CGM measurement           |
  | cgm               | float          | CGM value in mg/dL                        |

"""
import os
from studies.iobp2 import IOBP2StudyData
from studies.flair import Flair
from studies.pedap import PEDAP
from studies.dclp import DCLP3
from studies.dclp import DCLP3, DCLP5

import src.postprocessing as pp
from src.save_data_as import save_data_as
import logging
from datetime import datetime
from tqdm import tqdm


def current_time():
  return datetime.now().strftime("%H:%M:%S")


def main(test=False):
  logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s %(message)s',
      datefmt='[%H:%M:%S]',  # Remove milliseconds
      handlers=[
          #logging.FileHandler("app.log"),  # Log to a file
          logging.StreamHandler()  # Also log to console
      ]
  )

  #run_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
  current_dir = os.getcwd()
  if test:
      in_path = os.path.join(current_dir, 'data/test')
  else:
     in_path = os.path.join(current_dir, 'data/raw')
  out_path = os.path.join(current_dir, 'data/out')
  logging.info(f"Looking for study folders in {in_path} and saving results to {out_path}")

  #define how folders are identified and processed
  patterns = {'IOBP2 RCT Public Dataset': IOBP2StudyData,
              'FLAIRPublicDataSet': Flair,
              'PEDAP Public Dataset - Release 3 - 2024-09-25': PEDAP,
              'DCLP3 Public Dataset - Release 3 - 2022-08-04': DCLP3,
              'DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53': DCLP5}

  # Filter and log folders that cannot be matched
  study_folder_names = [f for f in os.listdir(in_path) if os.path.isdir(os.path.join(in_path, f))]
  unmatched_folders = []
  matched_folders = []

  for folder in study_folder_names:
      study_class = None
      for pattern, handler in patterns.items():
          if pattern in folder:
              study_class = handler
              matched_folders.append((folder, study_class))
              break
      if study_class is None:
          unmatched_folders.append(folder)

  if unmatched_folders:
      logging.warning(f"The folders '{unmatched_folders}' are not recognized as a supported studies. \n Did you accidentally rename them? \n Please check the documentation for supported studies.")
  if not matched_folders:
      logging.error("No supported studies found in the data/raw folder. Exiting.")
      exit()

  # Process matched folders with progress indicators
  logging.info(f"Start processing supported study folders:")
  for i,(folder, study_class) in enumerate(matched_folders):
      logging.info(f'{i}: {folder} using {study_class.__name__}')
  logging.info("")

  with tqdm(total=len(matched_folders)*7, desc=f"Processing studies", bar_format='Step {n_fmt}/{total_fmt} [{desc}]:|{bar}', unit="step", leave=False) as progress:
    for folder, study_class in matched_folders:
      tqdm.write(f"[{current_time()}] Processing {folder} ...")

      study_output_path = os.path.join(out_path, folder)
      if not os.path.exists(study_output_path):
          os.makedirs(study_output_path)
      
      study = study_class(study_path=os.path.join(in_path, folder))
      process_folder(study, out_path, progress)
    tqdm.write("Processing complete.")

def process_folder(study,  out_path_study, progress):
    
      progress.set_description_str(f"{study.__class__.__name__}: (Loading data)")
      study.load_data()
      tqdm.write(f"[{current_time()}] [x] Data loaded")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Extracting boluses")
      bolus_history = study.extract_bolus_event_history()
      out_file_path = save_data_as(bolus_history, 'CSV', os.path.join(out_path_study, f"bolus_history"))
      tqdm.write(f"[{current_time()}] [x] Boluses extracted: {out_file_path.split('/')[-1]}")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Resampling boluses")
      bolus_history_transformed = bolus_history.groupby('patient_id').apply(pp.bolus_transform, include_groups=False).reset_index(level=0)
      out_file = save_data_as(bolus_history_transformed, 'CSV', os.path.join(out_path_study, f"bolus_history-transformed"))
      tqdm.write(f"[{current_time()}] [x] Boluses resampled: {out_file.split('/')[-1]}")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Extracting basals")
      basal_history = study.extract_basal_event_history()
      out_file_path = save_data_as(basal_history, 'CSV', os.path.join(out_path_study, f"basal_history"))
      tqdm.write(f"[{current_time()}] [x] Basal events extracted: {out_file_path.split('/')[-1]}")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Resampling basals")
      basal_history_transformed = basal_history.groupby('patient_id').apply(pp.basal_transform, include_groups=False).reset_index(level=0)
      out_file = save_data_as(basal_history_transformed, 'CSV', os.path.join(out_path_study, f"basal_history-transformed"))
      tqdm.write(f"[{current_time()}] [x] Basal events resampled: {out_file.split('/')[-1]}")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Extracting glucose")
      cgm_history = study.extract_cgm_history()
      out_file_path = save_data_as(cgm_history, 'CSV', os.path.join(out_path_study, f"cgm_history"))
      tqdm.write(f"[{current_time()}] [x] CGM extracted: {out_file_path.split('/')[-1]}")
      progress.update(1)

      progress.set_description_str(f"{study.__class__.__name__}: Resampling glucose")
      cgm_history_transformed = cgm_history.groupby('patient_id').apply(pp.cgm_transform, include_groups=False).reset_index(level=0)
      out_file = save_data_as(cgm_history_transformed, 'CSV', os.path.join(out_path_study, f"cgm_history-transformed"))
      tqdm.write(f"[{current_time()}] [x] CGM resampled: {out_file.split('/')[-1]}")
      progress.update(1)


if __name__ == "__main__":
    main()