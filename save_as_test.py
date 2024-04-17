from save_data_as import save_data_as
import pandas as pd

data = [[0,1],
        [2,3],
        [4,5]]

test_data = pd.DataFrame(data,columns=['Col1','Col2'])

print(test_data)

save_data_as(test_data,'CSV','test_data')
save_data_as(test_data,'MAT','test_data')