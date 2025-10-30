import yfinance as yf
import pandas as pd
import datetime
import logging
# Configure basic logging to console (default)
logging.basicConfig(level=logging.INFO) 


# Get market index value for the latest closed date
def MarketUpdate(save_his = False):

    market_tbl = pd.DataFrame(columns = ['closed_date', 'index', 'metric', 'val'])
    Market_US_summary = yf.Market('US').summary
    Market_US_status = yf.Market('US').status
    # market_tbl_new = pd.DataFrame(columns = market_tbl.columns.to_list()) #['nextopen_date','index','metric', 'val']
    # date = datetime.datetime.today().date().strftime("%Y-%m-%d")
    date = Market_US_status['open'][:10] #'2025-10-07' #Market_US_status['open'][:10]
    if date != datetime.date.today().strftime('%Y-%m-%d'):
        logging.info('New market summary is not updated. Please reload the package or come back later.')
    else:
        if date in market_tbl.closed_date.to_list(): # to be updated
            market_tbl = market_tbl[market_tbl.closed_date != date]
            print(f'''Data on {date} is refreshed''')
        for idx in Market_US_summary:
            for key, val in Market_US_summary[idx].items():
                if type(val) == float:
                    market_tbl.loc[len(market_tbl)] = [date, idx, key, val]
        print(f'''Market index is retrived for {date}''')
        
        if save_his:
            market_tbl_his = pd.read_csv(f'''{path}/market_tbl.csv''')
            market_tbl_his = pd.concat([market_tbl_his, market_tbl])
            market_tbl.to_csv(f'''{path}/market_tbl.csv''', index = False)
            print(f'''{date} Updates are saved in historical table''')
    return date, market_tbl