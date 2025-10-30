import yfinance as yf
import pandas as pd
import datetime
from yfinance import EquityQuery
import logging
import os
# Configure basic logging to console (default)
logging.basicConfig(level=logging.INFO) 

def TestWriteDate(date, path):
    df_date_data_tracker = pd.read_csv(f'''{path}/df_date_data_tracker.csv''')
    if date in df_date_data_tracker.closed_date.to_list():
        return False
    else:
        return True

def TestTables(path, tablenames = {}):
    new_tables = []
    if len(tablenames) == 0:
    
    # df_industry_sector_col = ['industry_key', 'industry_name', 'industry_ticker', 'marßket weight', 'sector']
        tablenames = {
            'df_date_data_tracker':['closed_date', 'run_date'],
            'industry_tbl':['closed_date', 'sector', 'industry_key', 'industry_name', 'industry_ticker', 'metric', 'val'],
            'industry_prioritize':['industry_key', 'industry_name', 'industry_ticker', 'sector', 'closed_date', 'Prioritize'],
            'stock_tbl':['closed_date', 'industry_name', 'stock_ticker', 'stock_name','epsTrailingTwelveMonths', 'epsCurrentYear',
                         'epsForward','priceEpsCurrentYear'],
            'stock_metrics':['closed_date', 'industry_name', 'stock_ticker', 'stock_name', 'metric', 'metric_test']
        }
    
    for table, col in tablenames.items():
        file_path = os.path.join(path, table + '.csv')
        exist = os.path.exists(file_path)
        if not exist:
            df_ = pd.DataFrame(columns = col)
            df_.to_csv(f'''{path}/{table}.csv''', index = False)
            new_tables.append(table)
    if len(new_tables) > 0:
        return f'''{new_tables} are created'''
    else:
        return f'''All tables exist'''
        
    