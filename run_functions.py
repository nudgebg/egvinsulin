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

run_time = datetime.now().strftime("%Y%m%d%H%M%S")
current_dir = os.getcwd()
in_path = os.path.join(current_dir, 'data/raw')
out_path = os.path.join(current_dir, 'data/out')
logging.info(f"Current directory: {current_dir}, looking for data in 'data/raw' and saving results to data/out")

#define how folders are identified and processed
patterns = {'IOBP2 RCT Public Dataset': IOBP2StudyData,
            'FLAIRPublicDataSet': Flair}
study_folders = [f for f in os.listdir(in_path) if os.path.isdir(os.path.join(in_path, f))]
logging.info("Found the following folders:\n  * " + "\n  * ".join(study_folders))
logging.info(f"Processing {len(study_folders)} folders ...")

for folder in study_folders:
    #identify study class
    study_class = None
    for pattern, handler in patterns.items():
        if pattern in folder:
            study_class = handler
            break
    if study_class is None:
        logging.warning(f"Skipping folder '{folder}' as no handler is defined.")
        continue
    logging.info(f"Processing {folder} folder using {study_class.__name__} class ...")

    out_path_study = os.path.join(out_path, folder)
    if not os.path.exists(out_path_study):
        os.makedirs(out_path_study)
        logging.info(f"Created folder {out_path_study}")

    #loading study data
    absolute_folder_path = os.path.join(in_path, folder)
    study = study_class(study_path=absolute_folder_path)
    study.load_data()
    logging.info(f"[x] Study data loaded")


    #data extraction: bolus, basal and cgm events in standardized format
    bolus_history = study.extract_bolus_event_history()
    out_file_path = save_data_as(bolus_history, 'CSV', os.path.join(out_path_study, f"{run_time}-bolus_history"))
    logging.info(f"[x] Bolus events extracted and saved to {out_file_path.split('/')[-1]}")
    
    basal_history = study.extract_basal_event_history()
    out_file_path = save_data_as(basal_history, 'CSV', os.path.join(out_path_study, f"{run_time}-basal_history"))
    logging.info(f"[x] Basal events extracted and saved to {out_file_path.split('/')[-1]}")
    
    cgm_history = study.extract_cgm_history()
    out_file_path = save_data_as(cgm_history, 'CSV', os.path.join(out_path_study, f"{run_time}-cgm_history"))
    logging.info(f"[x] CGM events extracted and saved to {out_file_path.split('/')[-1]}")
    
    #data transformation: resampling to 5 minute intervals and time alignment at midnight
    cgm_history_transformed = cgm_history.groupby('patient_id').apply(pp.cgm_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(cgm_history_transformed, 'CSV', os.path.join(out_path_study, f"{run_time}-cgm_history-transformed"))
    logging.info(f"[x] CGM events transformed and saved to {out_file.split('/')[-1]}")
    
    bolus_history_transformed = bolus_history.groupby('patient_id').apply(pp.bolus_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(bolus_history_transformed, 'CSV', os.path.join(out_path_study, f"{run_time}-bolus_history-transformed"))
    logging.info(f"[x] Bolus events transformed and saved to {out_file.split('/')[-1]}")

    basal_history_transformed = basal_history.groupby('patient_id').apply(pp.basal_transform, include_groups=False).reset_index(level=0)
    out_file = save_data_as(basal_history_transformed, 'CSV', os.path.join(out_path_study, f"{run_time}-basal_history-transformed"))
    logging.info(f"[x] Basal events transformed and saved to {out_file.split('/')[-1]}")

logging.info("All studies processed.")