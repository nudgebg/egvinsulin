from cleaning_functions import FLAIR_cleaning, DCLP5_cleaning, DCLP3_cleaning, IOBP2_cleaning
import os, sys

# Add higher directory to Python path
current_dir = os.getcwd()
print(current_dir)
<<<<<<< HEAD
original_data_path = os.path.join(current_dir, 'data/raw')
=======
original_data_path = os.path.join(current_dir, 'data/test')
>>>>>>> develop
cleaned_data_path = os.path.join(current_dir, 'data/cleaned')
print(original_data_path, cleaned_data_path)


data_set_folder_names = ['FLAIRPublicDataSet',
                         'DCLP3 Public Dataset - Release 3 - 2022-08-04',
                         'DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53',
                         'IOBP2 RCT Public Dataset']
handlers = [FLAIR_cleaning, DCLP3_cleaning, DCLP5_cleaning, IOBP2_cleaning]

for folder, handler in zip(data_set_folder_names, handlers):
    rawPath = os.path.join(original_data_path, folder)
    outPath = os.path.join(cleaned_data_path, folder)
    handler(rawPath, outPath, True)

