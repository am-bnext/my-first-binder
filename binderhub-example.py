import io
import re
import glob
import datetime
from functools import partial

import numpy as np
import pandas as pd

blanklabel = "B:16"
normlabel = "B:14"
date = "20240916"
datafile = "data/M_20240916-204829 b.next Envision FLUOR deGFP Timecourse.csv"
label_order = [f"B:{2*i+2}" for i in range(8)]

def read_platemap_str(platemap_str: str) -> pd.DataFrame:
    platemap = pd.read_table(io.StringIO(platemap_str), index_col=0)
    platemap.index.name = "Row"
    platemap = platemap.reset_index().melt(id_vars=["Row"], var_name="Column", value_name="Construct")
    
    platemap["Column"] = platemap["Column"].astype(int)
    platemap["Well"] = platemap.apply(lambda well: f"{well['Row']}:{well['Column']}", axis=1)
    platemap = platemap.rename(columns={"Construct": "Label"})
    platemap = platemap.dropna()
    return platemap

def read_platemap_excel(platemap_path: str) -> pd.DataFrame:
    """
    Use like this:

    
    > platemap_path = "path/to/platemap.xlsx"
    > platemap = read_platemap_excel(platemap_path)
    > platemap.head()
    """
    platemap = pd.read_excel(platemap_path)
    platemap.fillna(value=0, inplace=True)
    platemap['Row'] = platemap['Well'].apply(lambda s: s.split(":")[0])
    platemap['Column'] = platemap['Well'].apply(lambda s: s.split(":")[1]).astype(int)

    return platemap

# LOAD YOUR PLATEMAP HERE
platemap = read_platemap_excel(
    f"data/{date}-platemap.xlsx"
)
platemap.head()

def read_envision(
    datafile: str, 
    platemap: pd.DataFrame,
    blanklabel: str = False
) -> pd.DataFrame:
    # load data
    data = pd.read_csv(datafile)
    # massage Row, Column, and Well information
    data["Row"] = data["Well ID"].apply(lambda s: s[0])
    data["Column"] = data["Well ID"].apply(lambda s: str(int(s[1:])))
    data["Well"] = data.apply(lambda well: f"{well['Row']}:{well['Column']}", axis=1)
    # merge on Well
    data = data.merge(
        platemap.drop(["Row", "Column"], axis=1), 
        left_on="Well", right_on="Well", how="inner"
    )
    
    data["Data"] = data["Result Channel 1"]
    data["Ex"] = data["Exc WL[nm]"]
    data["Em"] = data["Ems WL Channel 1[nm]"]
    data["Wavelength"] = data["Ex"] + "," + data["Em"]

    data['Time'] = pd.to_timedelta(data['Time [hhh:mm:ss.sss]']).astype('timedelta64[s]')
    data['Seconds'] = data['Time'].map(lambda x: x.total_seconds())

    # apply blanking, if blanklabel given
    if blanklabel:
        num_conditions = len(set(data["Well"]))
        
        # make a new DataFrame with just the blanks; use "Repeat" as time variable
        background_column = data[data["Well"] == blanklabel]
        background_data = background_column["Data"]
        background_repeat = background_column["Repeat"]
        background = pd.DataFrame({
            "Background": background_data,
            "Repeat": background_repeat
        })
        
        # merge blanks dataframe with data; subtract
        data = pd.merge(data, background, on="Repeat")
        data["BackgroundSubtracted"] = data["Data"] - data["Background"]
        
    return data

data = read_envision(
    datafile=datafile,
    platemap=platemap,
    blanklabel=blanklabel
)
data.head()
