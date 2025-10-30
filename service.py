import pandas as pd
import numpy as np
import datetime

# Get today's date
today = datetime.date.today().strftime("%Y-%m-%d")

# Test if files exist
from date_data_tracker import TestWriteDate
getnewdata = 