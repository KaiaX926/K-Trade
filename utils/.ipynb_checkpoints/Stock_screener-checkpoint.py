import yfinance as yf
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from yfinance import EquityQuery
import logging
# Configure basic logging to console (default)
logging.basicConfig(level=logging.INFO) 



# how many days does each uptrend window last
def TrendWindow(df, col, window_size):

    # i = window_size
    uptrend, his = [], []
    length, i = 0, 0
    while i < len(df):
        # print(his)
        if i < window_size:
            his.append(df[col].iloc[i])
        else:
            avg = sum(his)/window_size
            his.pop(0)
            current = df[col].iloc[i]
            if  current > avg:
                length += 1
            else:
                if length != 0:
                    uptrend.append(length)
                    length = 0

            his.append(current)
        i += 1
    uptrend.sort()
    return uptrend


def customized_bin():

    # Follow fiobonacci pattern
    
    fib = [1,1]
    end = 1000
    fib_binname = []
    i = 2
    while i < 13:
        nxt = fib[i-1] + fib[i-2]
        fib.append(nxt)
        i += 1
        # print(fib)
        binname = f'''bin{fib[i-2]}_{fib[i-1]}'''
        # print(binname)
        fib_binname.append(binname)
    fib_binname.append(f'''bin{fib[-1]}_{end}''')
    fib.append(end)
    # fib[0] = 0
    fib.pop(0)
    return fib, fib_binname


def price_above_dma(data, window_size=50):
    """
    Checks if the most recent closing price is above its moving average (DMA).
    
    Parameters:
        data (pd.DataFrame): Historical price data with a 'Close' column.
        window_size (int): Moving average period (default 50).
    
    Returns:
        bool: True if latest price > DMA, else False.
    """

    # --- 1. Validate input ---
    if "Close" not in data.columns:
        raise ValueError("Input DataFrame must contain a 'Close' column.")

    if len(data) < window_size:
        raise ValueError(f"Not enough data to compute {window_size}-day moving average.")

    # --- 2. Compute DMA ---
    data = data.copy()
    data[f"{window_size}_DMA"] = data["Close"].rolling(window=window_size).mean()

    # --- 3. Check last price vs. DMA ---
    latest_close = data["Close"].iloc[-1]
    latest_dma = data[f"{window_size}_DMA"].iloc[-1]

    return bool(latest_close > latest_dma)


def dma_crossover_test(data, window_size_short=50, window_size_long=200):
    """
    Tests if the short-term DMA (e.g., 50-DMA) is above the long-term DMA (e.g., 200-DMA).
    Returns True if bullish crossover (Golden Cross), else False.
    
    Parameters:
        data (pd.DataFrame): Historical price data with a 'Close' column.
        window_size_short (int): Short-term moving average window (default 50).
        window_size_long (int): Long-term moving average window (default 200).
    
    Returns:
        bool: True if latest short DMA > latest long DMA, else False.
    """

    # --- 1. Validate input ---
    if "Close" not in data.columns:
        raise ValueError("Input DataFrame must contain a 'Close' column.")
    
    if len(data) < window_size_long:
        raise ValueError(f"Not enough data to compute {window_size_long}-day moving average.")

    # --- 2. Compute both moving averages ---
    data = data.copy()
    data[f"{window_size_short}_DMA"] = data["Close"].rolling(window=window_size_short).mean()
    data[f"{window_size_long}_DMA"] = data["Close"].rolling(window=window_size_long).mean()

    # --- 3. Compare latest values ---
    short_dma = data[f"{window_size_short}_DMA"].iloc[-1]
    long_dma = data[f"{window_size_long}_DMA"].iloc[-1]

    return bool(short_dma > long_dma)

def macd_bullish_test(data, EMA_short=12, EMA_long=26, EMA_signal=9, lookback_days=3):
    """
    Checks whether a stock recently passed the MACD bullish crossover test.
    
    Parameters:
        data (pd.DataFrame, optional): Historical price data with a 'Close' column.
                                       If None, data will be downloaded automatically.
        EMA_short (int): Short-term EMA period (default 12)
        EMA_long (int): Long-term EMA period (default 26)
        EMA_signal (int): Signal EMA period (default 9)
        lookback_days (int): Days to check for recent crossover (default 3)
    
    Returns:
        bool: True if recent bullish MACD crossover detected, else False
    """

    # --- 1. Load data if not provided ---
    if data is None:
        raise ValueError("Input data does not exist")


    # Ensure required column exists
    if "Close" not in data.columns:
        raise ValueError("Input data must contain a 'Close' column.")

    # --- 2. Compute EMAs ---
    data["EMA_short"] = data["Close"].ewm(span=EMA_short, adjust=False).mean()
    data["EMA_long"] = data["Close"].ewm(span=EMA_long, adjust=False).mean()

    # --- 3. Compute MACD and Signal Line ---
    data["MACD"] = data["EMA_short"] - data["EMA_long"]
    data["Signal"] = data["MACD"].ewm(span=EMA_signal, adjust=False).mean()

    # --- 4. Check for recent bullish crossover ---
    data["Crossover"] = (data["MACD"] > data["Signal"]) & (data["MACD"].shift(1) <= data["Signal"].shift(1))

    recent_crossover = data.tail(lookback_days)["Crossover"].any()

    # --- 5. Confirm MACD > 0 (optional filter for momentum strength) ---
    if recent_crossover and data["MACD"].iloc[-1] > 0:
        return True
    else:
        return False

        

def volume_surge_test(data, window_size=20, multiplier=1.5):
    """
    Tests if the latest daily trading volume is greater than (multiplier × N-day average volume).

    Parameters:
        data (pd.DataFrame): Historical price data with a 'Volume' column.
        window_size (int): Number of days for average volume (default 20).
        multiplier (float): Threshold multiplier (default 1.5 → 50% above average).

    Returns:
        bool: True if latest volume > multiplier × average volume, else False.
    """

    # --- 1. Validate input ---
    if "Volume" not in data.columns:
        raise ValueError("Input DataFrame must contain a 'Volume' column.")
    if len(data) < window_size:
        raise ValueError(f"Not enough data to compute {window_size}-day average volume.")

    # --- 2. Compute rolling average volume ---
    data = data.copy()
    data[f"{window_size}_day_avg_volume"] = data["Volume"].rolling(window=window_size).mean()

    # --- 3. Compare latest volume to average ---
    latest_vol = data["Volume"].iloc[-1]
    avg_vol = data[f"{window_size}_day_avg_volume"].iloc[-1]

    return bool(latest_vol > multiplier * avg_vol)


def index_trend_test(data, symbol="^GSPC", window_size=20, ma_window=55, slope_threshold=0):
    """
    Tests whether a market index (e.g., S&P 500) is in an up or flat trend.
    Returns True if trend is up or flat, else False (downtrend).

    Parameters:
        data (pd.DataFrame, optional): Historical price data with a 'Close' column.
                                       If None, data will be fetched automatically for the symbol.
        symbol (str): Index ticker (default '^GSPC' = S&P 500).
        window_size (int): Lookback period to calculate trend slope (default 20 days).
        ma_window (int): Moving average window to confirm trend alignment (default 50 days).
        slope_threshold (float): Minimum acceptable slope (default 0 → flat or uptrend passes).

    Returns:
        bool: True if trend is up or flat, else False.
    """

    # --- 1. Fetch data if not provided ---
    index_data = yf.download(symbol, period="3y", interval="1d", progress=False, auto_adjust = False)

    if "Close" not in data.columns:
        raise ValueError("Input DataFrame must contain a 'Close' column.")
        
    if "Close" not in index_data.columns:
        raise ValueError("Index DataFrame must contain a 'Close' column.")
        
    if len(data) < max(window_size, ma_window):
        raise ValueError("Not enough data to compute trend metrics.")

    # --- 2. Compute slope of recent trend ---
    y = index_data["Close"].tail(window_size)
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]  # slope of linear regression line

    # --- 3. Compute moving average alignment ---
    index_data[f"{ma_window}_DMA"] = index_data["Close"].rolling(window=ma_window).mean()
    price_above_ma = index_data["Close"].iloc[-1] >= index_data[f"{ma_window}_DMA"].iloc[-1]

    # --- 4. Determine trend status ---
    trend_up_or_flat = (slope >= slope_threshold) and price_above_ma

    return bool(trend_up_or_flat)


def remove_non_trading_days(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove weekends, holidays, and non-trading rows from yfinance data.
    
    Logic:
      - Drop rows with all NaNs in OHLC
      - Drop rows with 0 volume (if column exists)
      - Drop duplicate calendar rows (if weekends appear)
      - Return DataFrame indexed only by actual market trading days.
    
    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame returned by yfinance.download()

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame containing only trading sessions.
    """

    if df.empty:
        return df

    df_clean = df.copy()

    # Drop rows with all NaN prices
    ohlc_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df_clean.columns]
    df_clean = df_clean.dropna(subset=ohlc_cols, how="all")

    # Drop rows with 0 volume (if Volume column exists)
    if "Volume" in df_clean.columns:
        df_clean = df_clean[df_clean["Volume"] != 0]

    # Ensure index is datetime and sorted
    if not isinstance(df_clean.index, pd.DatetimeIndex):
        df_clean.index = pd.to_datetime(df_clean.index, errors="coerce")
    df_clean = df_clean.sort_index().dropna(subset=ohlc_cols, how="all")

    # Drop duplicates (can occur if weekend filler exists)
    df_clean = df_clean[~df_clean.index.duplicated(keep="first")]

    return df_clean



def flatten_yf_data(df: pd.DataFrame, keep_first: bool = True, ticker: str = None) -> pd.DataFrame:
    """
    Flatten yfinance multi-index DataFrame (Price, Ticker) into single-level columns.
    If multi-indexed, keeps only the first ticker or a specified one.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame returned by yfinance.download() which may have MultiIndex columns.
    keep_first : bool, default True
        If True, keep only the first ticker in the MultiIndex.
    ticker : str, optional
        Specify a ticker symbol to extract instead of the first one.

    Returns
    -------
    pd.DataFrame
        Single-index DataFrame (columns = 'Open', 'High', 'Low', 'Close', 'Volume', ...).
    """

    if df.empty:
        return df

    # --- Check if columns are multi-indexed ---
    if isinstance(df.columns, pd.MultiIndex):
        # Level names often look like ['Price', 'Ticker'] or [None, None]
        price_level, ticker_level = df.columns.names

        # Get available tickers (level 1)
        tickers_available = df.columns.get_level_values(1).unique().tolist()

        # Choose which ticker to keep
        if ticker is not None and ticker in tickers_available:
            target_ticker = ticker
        elif keep_first:
            target_ticker = tickers_available[0]
        else:
            raise ValueError(
                f"Multiple tickers found: {tickers_available}. Please specify one using `ticker=`."
            )

        # --- Filter only columns for the chosen ticker ---
        df = df.xs(target_ticker, axis=1, level=1)

        # Drop the remaining top-level (now single-level columns)
        df.columns.name = None
        df = df.copy()

    else:
        # Not multi-indexed — nothing to flatten
        df = df.copy()

    return df


def GetTicker_MarketCapital(
        # industry filter params
    date: str,
    industry_candidate: pd.DataFrame,
    path: str, 
    indsutry_filter_func = None,
    lower_mp = 10000000000,
    higher_mp = 50000000000,
    save_his = False
    ):
    '''
    Get qualified stock ticker under specific industries
    criteria : market capital
    '''

    stock_tbl = pd.DataFrame(columns = ['closed_date', 'industry_name', 'stock_ticker', 'stock_name', "epsTrailingTwelveMonths","epsCurrentYear","epsForward","priceEpsCurrentYear"])
    fields = ["symbol","longName","epsTrailingTwelveMonths","epsCurrentYear","epsForward","priceEpsCurrentYear"]
    rename_mapping = {'symbol' : 'stock_ticker', 'longName' : 'stock_name'}
    
    for i in range(len(industry_candidate)):
        industry_name = industry_candidate['industry_name'].iloc[i]
        offset = 0
        logging.info(f'''appending stock info of {industry_name}''')
        rows = []

        try:
            q = EquityQuery('and', [
                    EquityQuery('EQ', ['region', 'us']),
                    EquityQuery('EQ', ['industry', industry_name]),
                    EquityQuery('GTE', ['intradaymarketcap', lower_mp]),
                    EquityQuery('LT', ['intradaymarketcap', higher_mp]),
                    EquityQuery('IS-IN', ['exchange', 'NMS', 'NYQ'])
                    ])

            while True:
                r = yf.screen(q, size=250, offset=offset, sortField='intradaymarketcap', sortAsc=False)
                quotes = r.get('quotes', [])
                if not quotes:
                    break
                for q in quotes:
                    row = {f: q.get(f, None) for f in fields}
                    # print(row)
                    if row:
                        rows.append(row)
                if len(quotes) < 250:
                    break
                offset += 250
            logging.info(f'''{len(rows)} tickers saved.''')
            if rows:
                df_quotes = pd.DataFrame(rows)
                df_quotes = df_quotes.rename(columns=rename_mapping)
                df_quotes['closed_date'] = date
                df_quotes['industry_name'] = industry_name    
                stock_tbl = pd.concat([stock_tbl, df_quotes], ignore_index = True)
 
        except:
            logging.info(f'''WARNING : {industry_name} is not a validate name in the pool''')
    if save_his:
        stock_tbl_his = pd.read_csv(f'''{path}/stock_tbl.csv''')
        
        if list(stock_tbl_his.columns) != list(stock_tbl.columns):
            raise Exception ('stock_tbl format does not match with expectation')
            
        if date in stock_tbl_his.closed_date.to_list(): #not in section_tbl.nextopen_date.to_list(): # to be updated
            stock_tbl_his = stock_tbl_his[stock_tbl_his.closed_date != date]
            logging.info(f'''stock_tbl_his Data on {date} is refreshed''')
            
        stock_tbl_his = pd.concat([stock_tbl_his, stock_tbl])
        stock_tbl_his.to_csv(f'''{path}/stock_tbl.csv''', index = False)
    return stock_tbl


# --- Assumes the following helper functions are already defined in your codebase ---
# macd_bullish_test(stock_code, data=None, EMA_short=12, EMA_long=26, EMA_signal=9, lookback_days=3) -> bool
# price_above_dma(data, window_size=50) -> bool
# dma_crossover_test(data, window_size_short=50, window_size_long=200) -> bool
# volume_surge_test(data, window_size=20, multiplier=1.5) -> bool
# index_trend_test(data=None, symbol="^GSPC", window_size=20, ma_window=50, slope_threshold=0.0) -> bool
# -------------------------------------------------------------------------------

def StockMetrics(
    date: str,
    stock_tbl: pd.DataFrame, # = stock_list,
    # *,
    # Stock filter params
    # yfinance fetch params
    path, 
    period: str = "3y",
    interval: str = "1d",
    # MACD params
    ema_short: int = 13, #12,
    ema_long: int = 21, #26,
    ema_signal: int = 8, #9,
    macd_lookback_days: int = 3,
    # Price > DMA params
    dma_window: int = 8, #50,
    # 50/200 trend params
    dma_short: int = 3, #50,
    dma_long: int = 21, #200,
    # Volume surge params
    volume_window: int = 3,
    volume_multiplier: float = 1.3, #1.5,
    # Index trend params
    index_symbol: str = "^GSPC",
    index_window: int = 20,
    index_ma_window: int = 50,
    index_slope_threshold: float = 0.0,
    save_his = False,
) -> pd.DataFrame:
    """
    Iterate an industry->(code, [tickers]) pool, fetch data, run tests, and return a boolean results table.

    Parameters
    ----------
    industry_stocks : dict
        Shape: {industry_name: [industry_code, [tickers]]}
    period, interval : str
        yfinance download parameters for each stock (default 6mo, 1d).
    ema_short, ema_long, ema_signal, macd_lookback_days : int
        MACD settings and lookback window for recent crossover detection.
    dma_window : int
        Window for Price > DMA test (default 50).
    dma_short, dma_long : int
        Windows for short/long DMA crossover test (default 50/200).
    volume_window, volume_multiplier : int, float
        Rolling window and multiplier for volume surge test (default 20, 1.5x).
    index_symbol, index_window, index_ma_window, index_slope_threshold : ...
        Settings for the market trend filter (S&P 500 up/flat by default).

    Returns
    -------
    pd.DataFrame
        Columns: industry_name, industry_code, stock_code,
                 macd_bullish, price_above_{dma_window}dma,
                 dma_{dma_short}_gt_{dma_long}, volume_surge,
                 market_trend_up_or_flat, all_pass
    """

    rows = []

    for i in range(len(stock_tbl)):
        stock_ticker = stock_tbl['stock_ticker'].iloc[i]
        stock_name = stock_tbl['stock_name'].iloc[i]
        industry_name = stock_tbl['industry_name'].iloc[i]

        df = flatten_yf_data(yf.download(stock_ticker, period=period, interval=interval, progress=False, auto_adjust=False))
        df = remove_non_trading_days(df)

        # Guard: ensure data has Close & Volume and enough rows
        has_close = "Close" in df.columns #and len(df) > max(dma_long, 30)
        has_volume = "Volume" in df.columns #and len(df) >= volume_window
        # display(df)
        if not has_close or not has_volume:
            raise Exception(f'''{stock_ticker} : Downloaded data frame strucutre of does not match expectation, Close = {has_close}, Volume = {has_volume}''')

        if len(df) > max(dma_long, 30) and len(df) >= volume_window:
            # Initialize defaults (False if test can’t be computed safely)
            macd_bullish = False
            price_above = False
            dma_cross = False
            vol_surge = False
            index_trend_above = False

            # --- Run tests with safety wrappers ---
            macd_bullish = macd_bullish_test(df, EMA_short=ema_short, EMA_long=ema_long, EMA_signal=ema_signal, lookback_days=macd_lookback_days)
            price_above = price_above_dma(df, window_size=dma_window)
            dma_cross = dma_crossover_test(df, window_size_short=dma_short, window_size_long=dma_long)
            vol_surge = volume_surge_test(df, window_size=volume_window, multiplier=volume_multiplier)
            
            metrics_dict = {
                "macd_bullish": bool(macd_bullish),
                f"price_above_{dma_window}dma": bool(price_above),
                f"dma_{dma_short}_gt_{dma_long}": bool(dma_cross),
                "volume_surge": bool(vol_surge),
            }
            
            # convert to long-form rows
            for metric_name, metric_value in metrics_dict.items():
                rows.append({
                    'closed_date' : date,
                    "industry_name": industry_name,
                    "stock_ticker": stock_ticker,
                    'stock_name': stock_name,
                    "metric": metric_name,
                    "metric_test": metric_value,
                })
            logging.info(f'''{stock_ticker}: stock metrics are calculated''')
        else:
            logging.info(f'''{stock_ticker}: Not enought data point''')
    stock_metrics = pd.DataFrame(rows)
    if save_his:
        stock_metrics_his = pd.read_csv(f'''{path}/stock_metrics.csv''')
        
        if list(stock_metrics.columns) != list(stock_metrics_his.columns):
            raise Exception ('stock_metrics table format does not match exceptation')
            
        if date in stock_metrics_his.closed_date.to_list(): #not in section_tbl.nextopen_date.to_list(): # to be updated
            stock_metrics_his = stock_metrics_his[stock_metrics_his.closed_date != date]
            logging.info(f'''stock_metrics_his Data on {date} is refreshed''')
            
        stock_metrics_his = pd.concat([stock_metrics_his, stock_metrics])
        stock_metrics_his.to_csv(f'''{path}/stock_metrics.csv''', index = False)
    
    return stock_metrics


def StockReformat(
    stock_metrics: pd.DataFrame, 
    ):
    print(stock_metrics.columns, stock_metrics)
    df_wide = stock_metrics.pivot(index= ['closed_date', 'industry_name', 'stock_ticker', 'stock_name'], columns='metric', values='metric_test').reset_index()
    df_wide['pass_count'] = df_wide.iloc[:,4:].sum(axis = 1)
    df_wide = df_wide.sort_values(by = 'pass_count', ascending = False).reset_index()
    # df_wide = df_wide[['closed_date', 'industry_name', 'stock_ticker', 'stock_name']]
    
    column_to_move = 'pass_count'
    new_position_index = 4
    col_data = df_wide.pop(column_to_move)
    # Insert the column at the desired new position
    df_wide.insert(new_position_index, column_to_move, col_data)
    return df_wide
    


def StockPlot(ticker: str):
    df_stock = flatten_yf_data(yf.download(ticker, period='3y', interval='1d', progress=False, auto_adjust=False)).reset_index()
    
    # Sample data
    x = df_stock.Date  # 100 points between 0 and 10
    y1 = df_stock.Close
    y2 = df_stock.Volume
    # # Create the line plot
    # plt.figure(figsize=(30, 6)) 
    # plt.plot(x, y)
    
    
    # Create plot with dual axes
    fig, ax1 = plt.subplots(figsize=(40, 10))
    
    # Plot close price
    ax1.plot(x, y1, color='tab:blue', label='Close Price', linewidth=1.5)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Close Price (USD)', color='tab:blue', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    # Create second y-axis for Volume
    ax2 = ax1.twinx()
    ax2.plot(x, y2, color='tab:orange', label='Volume', linewidth=1.0, alpha=0.6)
    ax2.set_ylabel('Volume', color='tab:orange', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    # Titles and layout
    plt.title('APH — Close Price and Volume (3Y Daily)', fontsize=16)
    fig.tight_layout()
    
    # Combine legends from both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')
    
    # plt.show()
    return fig
