import os, sys, time, random
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from matplotlib import pyplot as plt
import dask.dataframe as dd
import warnings

warnings.filterwarnings("ignore")

current_dir = os.getcwd(); 
original_data_path = os.path.join(current_dir, 'data/raw')

path = os.path.join(original_data_path, 'Loop study public dataset 2023-01-31', 'Data Tables', 'LOOPDeviceCGM*.txt')
t = time.time()
df_cgm = dd.read_csv(path, sep="|",
                 usecols=['PtID', 'UTCDtTm', 'CGMVal', 'Units'],
                 dtype={'DeviceDtTm': 'object',
                       'DexInternalDtTm': 'object'},
                parse_dates=[1])
elapsed = time.time() - t
print(f"Loading all 6 Loop CGM data files with Dask while parsing dates takes {elapsed:.2f}s")
print()

t = time.time()
df_cgm_id = df_cgm.set_index(df_cgm.PtID, sorted=False)
df_cgm_id = df_cgm_id.repartition(npartitions=851)
elapsed = time.time() - t
print(f"Repartitioning data into individual IDs takes {elapsed:.2f}s")
print()

print(df_cgm_id.partitions[300].head(15))
print()

#applying function to all partitions
def test_function(df_cgm_id):
    #drop duplicate date times 
    df_cgm2 = df_cgm_id.drop_duplicates(subset = 'UTCDtTm')
    df_cgm2['UTCDtTm'] = df_cgm2['UTCDtTm'].dt.round("5min")
    df_cgm2['CGMVal'] = df_cgm2['CGMVal'] * 18
    df_cgm2['Units'] = 'mg/dL'
    df_cgm2 = df_cgm2.sort_values(by='UTCDtTm').reset_index(drop=True)
    return df_cgm2

t = time.time()
df_cgm2 = df_cgm_id.map_partitions(test_function)
elapsed = time.time() - t
print(f"Applying a function to 851 partitions takes {elapsed:.2f}s")
print()
print(df_cgm2.partitions[300].head(15))
