import os
from studies.iobp2 import IOBP2StudyData
from studies.flair import Flair
import src.postprocessing as pp
from src.save_data_as import save_data_as
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, 
    format='%(levelname)s - %(message)s', 
    handlers=[
        #logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

run_time = datetime.now().strftime("%Y%m%d%H%M%S")
current_dir = os.getcwd()
in_path = os.path.join(current_dir, 'data/raw')
out_path = os.path.join(current_dir, 'data/out')

logging.info(f"Input path: {in_path}")
logging.info(f"Output path: {out_path}")

#define how folders are identified and processed
patterns = {'IOBP2 RCT Public Dataset': IOBP2StudyData,
            'FLAIRPublicDataSet': Flair}
study_folders = [f for f in os.listdir(in_path) if os.path.isdir(os.path.join(in_path, f))]

for folder in study_folders:
    study_class = None
    for pattern, handler in patterns.items():
        if pattern in folder:
            study_class = handler
            break
    if study_class is None:
        logging.warning(f"Skipping folder '{folder}' as no handler is defined.")
        continue

    absolute_folder_path = os.path.join(in_path, folder)
    logging.info(f"Using {study_class} class to process {absolute_folder_path} data.")

    #load
    study = study_class(study_path=absolute_folder_path)
    study.load_data()

    #extract
    bolus_history = study.extract_bolus_event_history()
    basal_history = study.extract_basal_event_history()
    cgm_history = study.extract_cgm_history()

    #save
    out_extracted = os.path.join(out_path, folder, 'extracted')
    if not os.path.exists(out_extracted):
        os.makedirs(out_extracted, exist_ok=True)
    save_data_as(cgm_history, 'CSV', os.path.join(out_extracted, f"{run_time}-cgm_history"))
    save_data_as(bolus_history, 'CSV', os.path.join(out_extracted, f"{run_time}-bolus_history"))
    save_data_as(basal_history, 'CSV', os.path.join(out_extracted, f"{run_time}-basal_history"))

    #transform
    cgm_history_transformed = cgm_history.groupby('patient_id').apply(pp.cgm_transform).reset_index(drop=True)
    bolus_history_transformed = bolus_history.groupby('patient_id').apply(pp.bolus_transform).reset_index(drop=True)
    basal_history_transformed = basal_history.groupby('patient_id').apply(pp.basal_transform).reset_index(drop=True)

    #save
    out_transformed = os.path.join(out_path, folder, 'transformed')
    if not os.path.exists(out_transformed):
        os.makedirs(out_transformed, exist_ok=True)
    save_data_as(cgm_history_transformed, 'CSV', os.path.join(out_transformed, f"{run_time}-cgm_history"))
    save_data_as(bolus_history_transformed, 'CSV', os.path.join(out_transformed, f"{run_time}-bolus_history"))
    save_data_as(basal_history_transformed, 'CSV', os.path.join(out_transformed, f"{run_time}-basal_history"))
