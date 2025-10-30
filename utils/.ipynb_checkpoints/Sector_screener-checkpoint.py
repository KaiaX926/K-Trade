import yfinance as yf
import pandas as pd
import datetime
from yfinance import EquityQuery
import logging
# Configure basic logging to console (default)
logging.basicConfig(level=logging.INFO) 

# get industry info from sectors
def SectorToIndustry(path, focus_section = ['Information Technology','Health Care','Financials','Consumer Discretionary',
                                      'Consumer Staples','Communication Services']
                    ):
    '''
    Get all sector names (gics standard) and their symbols (yahoo standard)
    input : pre-defined 6 sectors under gics standard
    output : industry table of the focus_section. columns: [industry_key, industry_name, industry_ticker, market_weight, sector] 
    - industry_key, industry_name, industry_ticker in yahoo standard
    - sector in yahoo standard
    
    Should not be saved
    '''

    sector_mapping = pd.read_csv(f'''{path}/gics_to_yahoo_sector_mapping.csv''').set_index('gics_sector')
    df_industry_sector = pd.DataFrame()
    focus_gics_section = sector_mapping.loc[focus_section]
    if len(focus_gics_section) != len(focus_section):
        raise Exception('One or more section cannot be found in the validated section list. Please review and update')
    else:
        focus_yahoo_section = focus_gics_section.yahoo_sector.to_list()
        for i in range(len(focus_yahoo_section)):
            sector_y = focus_yahoo_section[i]
            df_ = yf.Sector(sector_y).industries
            df_['sector'] = sector_y
            df_industry_sector = pd.concat([df_industry_sector, df_])
            # print(df_sector)
        df_industry_sector = df_industry_sector.reset_index()
        if 'key' not in df_industry_sector.columns or 'name' not in df_industry_sector.columns or 'symbol' not in df_industry_sector.columns:
            raise Exception('Please check the yahoo download table format')
        column_mapping = {
                            'key': 'industry_key',
                            'name': 'industry_name',
                            'symbol': 'industry_ticker',
                        }
        df_industry_sector.rename(columns=column_mapping, inplace=True)

        return df_industry_sector #, focus_yahoo_section




# get industry basic metric position facts
def IndustryPositionFact(date, df_industry_sector, save_his = False):
    '''
    Get focused Industry positions for the date
    input : industry basic info 'sector', 'industry_key', 'industry_name', 'industry_ticker'
    output : industry table with industry basic info and metrics position of the date
    '''
    industry_tbl = pd.DataFrame(columns = ['closed_date', 'sector', 'industry_key', 'industry_name', 'industry_ticker', 'metric', 'val'])

    for i in range(len(df_industry_sector.industry_ticker)):
        industry_key = df_industry_sector.industry_key.iloc[i]
        industry_name = df_industry_sector.industry_name.iloc[i]
        industry_ticker = df_industry_sector.industry_ticker.iloc[i]
        sector = df_industry_sector.sector.iloc[i]
        # print(industry)
        df_ = yf.Ticker(industry_ticker).info
        for key, val in df_.items():
            if type(val) == float:
                industry_tbl.loc[len(industry_tbl)] = [date, sector, industry_key, industry_name, industry_ticker, key, val]
    logging.info(f'''Industry postion is retrieved for {date}''')

    if save_his:
        industry_tbl_his = pd.read_csv('industry_tbl.csv')
        if date in industry_tbl_his.closed_date.to_list(): #not in section_tbl.nextopen_date.to_list(): # to be updated
            industry_tbl_his = industry_tbl_his[industry_tbl_his.closed_date != date]
            logging.info(f'''Data on {date} is refreshed''')
        industry_tbl_his = pd.concat([industry_tbl_his, industry_tbl])
        industry_tbl_his.to_csv('industry_tbl.csv', index = False)
        logging.info(f'''Industry metrics on {date} is saved in industry_tbl''')
    
    return industry_tbl



# Priorotization method 
def IndustryFilter_Trend(date, industry_tbl):
    '''
    Logic : previousClose > 50DayAverage * (1+abs(50DayAverageChangePercent)) & previousClose > 200DayAverage * (1+abs(200DayAverageChangePercent))
    '''
    df = industry_tbl[industry_tbl.closed_date == date]
    analysis_industry_tbl_new = df.pivot(index=['closed_date', 'industry_key', 'industry_ticker'], 
                                                columns='metric', values='val').reset_index()
    industry_list_50days = analysis_industry_tbl_new[analysis_industry_tbl_new.previousClose > 
                          analysis_industry_tbl_new.fiftyDayAverage * (1+abs(analysis_industry_tbl_new.fiftyDayAverageChangePercent))]
    industry_list_200days = analysis_industry_tbl_new[analysis_industry_tbl_new.previousClose > 
                              analysis_industry_tbl_new.twoHundredDayAverage * (1+abs(analysis_industry_tbl_new.twoHundredDayAverageChangePercent))]
    
    industry_list_set = set(industry_list_50days.industry_key) & set(industry_list_200days.industry_key)

        
    return industry_list_set



# generate an industry repo with industry info and a prioritize tag
def IndustryPrioritization(date, df_industry_sector, industry_tbl, filterfunction = IndustryFilter_Trend, save_his = False):
    '''
    generate an industry repo with industry info and a prioritize tag and save the result as sector_fact table
    '''
    industry_prioritize = df_industry_sector[['industry_key', 'industry_name', 'industry_ticker', 'sector']]
    industry_prioritize['closed_date'] = date
    industry_prioritize['Prioritize'] = False
    industry_list_set = filterfunction(date = date, industry_tbl = industry_tbl)
    industry_prioritize.loc[industry_prioritize['industry_key'].isin(industry_list_set),'Prioritize'] = True
    industry_prioritize = industry_prioritize.sort_values(by = 'Prioritize', ascending = False)
    
    if save_his:
        industry_prioritize_his = pd.read_csv('industry_prioritize.csv')
    
        if industry_prioritize.columns != industry_prioritize_his.columns:
            raise Exception('industry_prioritize table format does not match expactation')
        else:
            industry_prioritize_his = pd.concat([industry_prioritize_his, industry_prioritize])
            industry_prioritize_his.to_csv('industry_prioritize.csv', index = False)
            print(f'''industry_prioritize on {date} is saved in histroical table''')
    return industry_prioritize



