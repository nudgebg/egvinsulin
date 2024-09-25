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
import src.postprocessing as pp
from src.save_data_as import save_data_as
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # Remove milliseconds
    handlers=[
        #logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

#run_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
current_dir = os.getcwd()
in_path = os.path.join(current_dir, 'data/raw')
out_path = os.path.join(current_dir, 'data/out')
logging.info(f"Current directory: {current_dir}, looking for data in 'data/raw' and saving results to data/out")

#define how folders are identified and processed
patterns = {'IOBP2 RCT Public Dataset': IOBP2StudyData,
            'FLAIRPublicDataSet': Flair}
study_folders = [f for f in os.listdir(in_path) if os.path.isdir(os.path.join(in_path, f))]
logging.info("Found the following folders:\n  * " + "\n  * ".join(study_folders))

for folder in study_folders:
    #identify study class
    study_class = None
    for pattern, handler in patterns.items():
        if pattern in folder:
            study_class = handler
            break
    if study_class is None:
        logging.warning(f"The folder '{folder}' is not recognized as a supported study yet. \n Did you accidentally rename the folder?. \n Please check the documentation for supported studies.")
        continue
    logging.info(f"Start processing {folder} with class {study_class.__name__}...")

    out_path_study = os.path.join(out_path, folder)
    if not os.path.exists(out_path_study):
        os.makedirs(out_path_study)
        logging.info(f"Created folder {out_path_study}")

    #loading study data
    absolute_folder_path = os.path.join(in_path, folder)
    study = study_class(study_path=absolute_folder_path)
    study.load_data()
    logging.info(f"[x] Loaded data into memory")


    #data extraction: bolus, basal and cgm events in standardized format
    bolus_history = study.extract_bolus_event_history()
    out_file_path = save_data_as(bolus_history, 'CSV', os.path.join(out_path_study, f"bolus_history"))
    logging.info(f"[x] Bolus events extracted and saved to {out_file_path.split('/')[-1]}")
    
    basal_history = study.extract_basal_event_history()
    out_file_path = save_data_as(basal_history, 'CSV', os.path.join(out_path_study, f"basal_history"))
    logging.info(f"[x] Basal events extracted and saved to {out_file_path.split('/')[-1]}")
    
    cgm_history = study.extract_cgm_history()
    out_file_path = save_data_as(cgm_history, 'CSV', os.path.join(out_path_study, f"cgm_history"))
    logging.info(f"[x] CGM events extracted and saved to {out_file_path.split('/')[-1]}")
    
    #data transformation: resampling to 5 minute intervals and time alignment at midnight
    cgm_history_transformed = cgm_history.groupby('patient_id').apply(pp.cgm_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(cgm_history_transformed, 'CSV', os.path.join(out_path_study, f"cgm_history-transformed"))
    logging.info(f"[x] CGM events transformed and saved to {out_file.split('/')[-1]}")
    
    bolus_history_transformed = bolus_history.groupby('patient_id').apply(pp.bolus_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(bolus_history_transformed, 'CSV', os.path.join(out_path_study, f"bolus_history-transformed"))
    logging.info(f"[x] Bolus events transformed and saved to {out_file.split('/')[-1]}")

    basal_history_transformed = basal_history.groupby('patient_id').apply(pp.basal_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(basal_history_transformed, 'CSV', os.path.join(out_path_study, f"basal_history-transformed"))
    logging.info(f"[x] Basal events transformed and saved to {out_file.split('/')[-1]}")

logging.info("All studies processed.")