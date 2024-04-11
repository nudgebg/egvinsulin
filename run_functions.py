from cleaning_functions import FLAIR_cleaning,DCLP5_cleaning,DCLP3_cleaning,IOBP2_cleaning

original_data_path = '/Users/rachelbrandt/Downloads/FLAIRPublicDataSet/Data Tables/'
cleaned_data_path = '/Users/rachelbrandt/egvinsulin/'

cleaned_data,patient_data =  FLAIR_cleaning(original_data_path,cleaned_data_path)
