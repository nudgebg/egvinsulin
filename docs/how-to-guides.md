--8<-- "README.md"

This part of the project documentation focuses on a
**problem-oriented** approach. You'll tackle common
tasks that you might have, with the help of the code
provided in this project.

## How To extract cgm and insulin data?

```
    egvinsulin/
    ├── data/
    │   └── raw/
    │       └── FLAIRPublicDataSet
    │       └── DCLP3 Public Dataset - Release 3 - 2022-08-04
    │       └── DCLP5_Dataset_2022-01-20-5e0f3b16-c890-4ace-9e3b-531f3687cf53
    │       └── IOBP2 RCT Public Dataset
    │   └── cleaned/
    └── run_functions.py
```

1. Download the code from this GitHub repository. 
2. Install all dependencies (we recommend using a python virtual environment) using ```pip install -r requirements.txt```
3. Download the Flair, DCLP3, DCLP5 and IOBP2 from [JAEB.org](https://public.jaeb.org/datasets/diabetes). Extract the archive into the __/data/raw__ sub-folder. 
4. Run run_functions.py
5. The cleaned data will be output into __/data/cleaned__.

For more information on run_functions, check out the [Reference](reference.md).