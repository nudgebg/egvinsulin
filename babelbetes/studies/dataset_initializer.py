
import os
from babelbetes.studies import IOBP2, Flair, PEDAP, DCLP3, DCLP5, ReplaceBG, Loop, T1DEXI, T1DEXIP
from babelbetes.src.logger import Logger
logger = Logger.get_logger(__name__)

def initialize_datasets(data_path):
    patterns = ['IOBP2', 'FLAIR', 'PEDAP', 'DCLP3', 'DCLP5', 'REPLACE-BG', 'Loop', 'T1DEXI - DATA', 'T1DEXIP - DATA']
    classes = [IOBP2, Flair, PEDAP, DCLP3, DCLP5, ReplaceBG, Loop, T1DEXI, T1DEXIP]
    class_map = dict(zip(patterns, classes))
    initialized_studies = []

    # Get the list of all folders in the data_path
    all_folders = set(os.listdir(data_path))

    for pattern in patterns:
        matches = [f for f in all_folders if pattern in f]
        if matches:
            match = matches[0]
            if len(matches) > 1:
                logger.warning(f"{pattern} matches multiple folders: {matches}. Using {match}.")
            file_path = os.path.join(data_path, match)
            study = class_map[pattern](file_path)
            initialized_studies.append(study)
            all_folders.remove(match)  # Remove matched folder from the list

    # Print warnings for unmatched folders
    logger.warning("Unmatched folders:")
    for unmatched_folder in all_folders:
        logger.warning(f"  {unmatched_folder}")

    # Print information about matched studies
    logger.info("Successfully matched studies with folders:")
    for study in initialized_studies:
        logger.info(f"  {study.study_name} : {study.study_path}")
    
    return {study.study_name: study for study in initialized_studies}

