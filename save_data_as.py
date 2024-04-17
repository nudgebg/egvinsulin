def save_data_as(data,file_format,export_filename):
    #data is a dataframe of cleaned data that needs to be saved
    #fileformat is the format of the saved data: 
    #   For a .mat file specify 'MAT'
    #   For a .csv file specify 'CSV'
    #export_filename is the name the file should be saved as excluding the file type
    import pandas as pd
    
    if file_format == 'CSV':
        data.to_csv(export_filename + '.csv', index=False)
    
    if file_format == 'MAT':
        from scipy.io import savemat
        
        data_dict = data.to_dict(orient='dict')
        savemat(export_filename + '.mat', data_dict)
    
    return 