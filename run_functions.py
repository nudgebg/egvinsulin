import os
from studies.iobp2 import IOBP2StudyData
import src.postprocessing as pp
from save_data_as import save_data_as
import logging


logging.basicConfig(
    level=logging.INFO, 
    format='%(levelname)s - %(message)s', 
    handlers=[
        #logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)

current_dir = os.getcwd()
in_path = os.path.join(current_dir, 'data/test')
out_path = os.path.join(current_dir, 'data/cleaned')
logging.info(f"Input path: {in_path}")
logging.info(f"Output path: {out_path}")

#define how folders are identified and processed
patterns = {'IOBP2 RCT Public Dataset': IOBP2StudyData}
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

    #processing
    cgm_data = cgm_history.groupby('patient_id').apply(pp.cgm_transform).reset_index(drop=True)
    bolus_data = bolus_history.groupby('patient_id').apply(pp.bolus_transform).reset_index(drop=True)

    #save
    save_data_as(cgm_data, 'CSV', os.path.join(out_path, folder))
    save_data_as(bolus_data, 'CSV', os.path.join(out_path, folder))
