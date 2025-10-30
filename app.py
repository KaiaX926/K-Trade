# app.py
import streamlit as st
import pandas as pd
import numpy as np
import logging
import datetime
import os

# ---------- Page setup ----------
st.set_page_config(page_title="Sector/Industry Dashboard", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>

/* ===== Layout (sidebar 30% / main 70%) ===== */
[data-testid="stSidebar"] { min-width: 30vw; max-width: 30vw; }
section.main > div { max-width: 70vw; }
.block-container { padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }

/* ===== Selected row color (force light blue) ===== */
:root {
  --dataframe-selected-background-color: #b3d9ff !important;
  --dataframe-selected-background-color-hover: #99ccff !important;
}

[data-testid="stDataFrame"] [role="row"][aria-selected="true"],
[data-testid="stDataFrame"] [role="row"][aria-selected="true"] > div,
[data-testid="stDataFrame"] [data-baseweb="data-table"] [role="row"][aria-selected="true"],
[data-testid="stDataFrame"] [data-baseweb="data-table"] [role="row"][aria-selected="true"] > div {
  background-color: #b3d9ff !important;
  color: black !important;
}

[data-testid="stDataFrame"] [role="row"][aria-selected="true"]:hover,
[data-testid="stDataFrame"] [role="row"][aria-selected="true"] > div:hover {
  background-color: #99ccff !important;
}

[data-testid="stDataEditor"] [role="row"][aria-selected="true"],
[data-testid="stDataEditor"] [role="row"][aria-selected="true"] > div {
  background-color: #b3d9ff !important;
  color: black !important;
}

[data-testid="stDataFrame"] [data-baseweb="data-table"] [data-selected="true"],
[data-testid="stDataEditor"] [data-baseweb="data-table"] [data-selected="true"] {
  background-color: #b3d9ff !important;
  color: black !important;
}

</style>
""", unsafe_allow_html=True)

# ---------- Get functions ----------
import utils.Market_screener as ms
import utils.Sector_screener as secs
import utils.Stock_screener as stocks
import utils.date_data_tracker as tracker

# ---------- Global setting -----------
data_path = 'data_test'
util_path = 'utils'
table_message = tracker.TestTables(path=data_path)
logging.info(table_message)

# ---------- Dates / globals ----------
today = datetime.date.today().strftime("%Y-%m-%d")
market_date, market_tbl = ms.MarketUpdate()

# TODO: make this dynamic later
# selected_date = '2025-10-27'

with st.sidebar:
    st.header("Date Filter")
    selected_date = st.date_input(
        "Pick a close date",
        value=datetime.date.today(),
        min_value=None,
        max_value=None,
        key="selected_date_picker"
    ).strftime("%Y-%m-%d")
logging.info(f'''User selected {selected_date}. Date type is {type(selected_date)}''')
date = selected_date if selected_date else market_date
logging.info(f'''Get data for {date}''')

date_alert = ''
if today > market_date:
    date_alert = f"Market info of {today} has not been updated. Please come back later"
    date = market_date

if date_alert:
    st.markdown(date_alert)
    
# Which sectors to focus on in sidebar selectbox
focus_section = [
    'Information Technology',
    'Health Care',
    'Financials',
    'Consumer Discretionary',
    'Consumer Staples',
    'Communication Services'
]
sector_mapping = pd.read_csv(f'''{data_path}/gics_to_yahoo_sector_mapping.csv''')

# ---------- Persistent state init ----------

# 1. Track the CSV of what dates we've already processed
if "df_date_data_tracker" not in st.session_state:
    tracker_path = os.path.join(data_path, "df_date_data_tracker.csv")
    st.session_state.df_date_data_tracker = pd.read_csv(tracker_path)

# 2. Build a unique key for the chosen date
date_key = f"data_for_{date}"

# Only compute / load heavy data if we haven't already for this date
if date_key not in st.session_state:
    logging.info(f'''date_key not in st.session_state''')
    # Build sector↔industry mapping (needed whether we load cached tables or calculate fresh)
    df_industry_sector = secs.SectorToIndustry(
        path=data_path,
        focus_section=focus_section
    )

    save_his = True

    # Decide whether to load historical CSVs or compute new data
    if date not in st.session_state.df_date_data_tracker.closed_date.to_list() and date == market_date:
        logging.info(f'''Run functions to get data''')
        # First time seeing this date → compute and persist
        industry_tbl = secs.IndustryPositionFact(
            date=date,
            df_industry_sector=df_industry_sector,
            path=data_path,
            save_his=save_his
        )

        industry_prioritize_full = secs.IndustryPrioritization(
            date=date,
            df_industry_sector=df_industry_sector,
            industry_tbl=industry_tbl,
            filterfunction=secs.IndustryFilter_Trend,
            path=data_path,
            save_his=save_his,
        )

        stock_tbl_full = stocks.GetTicker_MarketCapital(
            date=date,
            industry_candidate=industry_prioritize_full,
            path=data_path,
            save_his=save_his
        )

        stock_metrics_full = stocks.StockMetrics(
            date=date,
            stock_tbl=stock_tbl_full,
            path=data_path,
            save_his=save_his
        )

        # Record that we've now generated data for this date
        st.session_state.df_date_data_tracker.loc[
            len(st.session_state.df_date_data_tracker)
        ] = [date, today]

        st.session_state.df_date_data_tracker.to_csv(
            f"{data_path}/df_date_data_tracker.csv",
            index=False
        )

    else:
        # We've seen this date before → load cached CSV artifacts
        logging.info(f'''Get data from historical tables for {date}''')
        industry_prioritize_full = pd.read_csv(f"{data_path}/industry_prioritize.csv")
        stock_tbl_full = pd.read_csv(f"{data_path}/stock_tbl.csv")
        stock_metrics_full = pd.read_csv(f"{data_path}/stock_metrics.csv")
        logging.info(f'''Data is retrieved from database (csv cache). {len(stock_metrics_full)} metric records were retrived''')

    # Filter down to just this close date once
    industry_prioritize_for_date = (
        industry_prioritize_full[industry_prioritize_full.closed_date == date]
        .reset_index(drop=True)
    )
    stock_tbl_for_date = (
        stock_tbl_full[stock_tbl_full.closed_date == date]
        .reset_index(drop=True)
    )
    stock_metrics_for_date = (
        stock_metrics_full[stock_metrics_full.closed_date == date]
        .reset_index(drop=True)
    )
    logging.info(f'''Data is retrieved from database (csv cache) for {date}. {len(stock_metrics_for_date)} metric records were retrived''')
    
    # Format for display
    stock_present_for_date = stocks.StockReformat(stock_metrics_for_date)

    # Stash everything under this date_key so reruns don't recompute
    st.session_state[date_key] = {
        "industry_prioritize": industry_prioritize_for_date,
        "stock_tbl": stock_tbl_for_date,
        "stock_metrics": stock_metrics_for_date,
        "stock_present": stock_present_for_date,
        "sector_mapping": sector_mapping,
    }
    

else:
    logging.info(f'''Current date is searched before''')
# ---------- Pull cached dfs for this rerun ----------
industry_prioritize = st.session_state[date_key]["industry_prioritize"]
stock_tbl = st.session_state[date_key]["stock_tbl"]
stock_metrics = st.session_state[date_key]["stock_metrics"]
stock_present = st.session_state[date_key]["stock_present"]
sector_mapping = st.session_state[date_key]["sector_mapping"]
logging.info(f'''{len(stock_metrics)} stock records was found for {date} research''')

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Filters")

    # Track last chosen sector so we can reset multi-select rows when sector changes
    if "last_sector" not in st.session_state:
        st.session_state["last_sector"] = None

    sector = st.selectbox("Sector", options=focus_section, index=0)
    mapping = sector_mapping[sector_mapping.gics_sector == sector].yahoo_sector
    if len(mapping) > 0:
        mapped_sector = mapping.iloc[0]
    else:
        logging.info('No mapping sector name was found')
        mapped_sector = sector

    # If user changed sector since last rerun, reset industries_df_select
    if st.session_state["last_sector"] != mapped_sector:
        st.session_state.pop("industries_df_select", None)
        st.session_state["last_sector"] = mapped_sector

    # Show only industries in the chosen sector
    sector_slice = (
        industry_prioritize[industry_prioritize["sector"] == mapped_sector]
        .reset_index(drop=True)
    )

    # Visible column(s)
    df_show = sector_slice[["industry_name"]].copy()

    # Build highlight mask from "Prioritize" for styling
    # Note: make sure Prioritize exists in industry_prioritize
    mask = sector_slice["Prioritize"].astype(bool).values

    def highlight_by_mask(_df):
        styles = pd.DataFrame('', index=_df.index, columns=_df.columns)
        styles.loc[mask, :] = 'background-color: #d4f8d4; color: black;'
        return styles

    styled_df = df_show.style.apply(highlight_by_mask, axis=None)

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun",
        key="industries_df_select"
    )

# ---------- Main body ----------
if st.session_state["last_sector"]:
    title_addition = f'''for sector :blue[{st.session_state["last_sector"]}]'''
    
st.title(f'''Metric screener {title_addition}''')
st.markdown("""
**Description:**  
This dashboard filters industries and stocks based on current market data, 
momentum indicators, and capitalization thresholds.  
You can use the sidebar to narrow down sectors or explore prioritized industries.
""")
st.subheader("📅 Latest Close Date")
st.info(f"Info on the screen is for **{date}**.")
if date_alert:
    st.warning(date_alert)

# ---------- Read industry selection ----------
ind_sel_state = st.session_state.get("industries_df_select", {})
ind_sel_rows = (ind_sel_state.get("selection", {}) or {}).get("rows", [])

# VERY IMPORTANT:
# The selection rows correspond to sector_slice (what we just displayed),
# NOT the full industry_prioritize df.
if ind_sel_rows:
    selected_industries = sector_slice.loc[ind_sel_rows, "industry_name"].tolist()
else:
    selected_industries = []

# Filter stock_present for those industries
if selected_industries:
    stock_present_filtered = (
        stock_present[stock_present["industry_name"].isin(selected_industries)]
        .reset_index(drop=True)
    )
else:
    stock_present_filtered = stock_present.reset_index(drop=True)

# ---------- Results table ----------
st.subheader("Results Table (click a row to plot)")
TABLE_HEIGHT = 200
stock_table_key = "stock_present_select"

st.dataframe(
    stock_present_filtered,
    use_container_width=True,
    height=TABLE_HEIGHT,
    hide_index=True,
    selection_mode="single-row",
    on_select="rerun",
    key=stock_table_key
)

# ---------- Chart ----------
st.subheader("Chart")

# Persist last selected ticker across reruns
if "last_selected_ticker" not in st.session_state:
    st.session_state["last_selected_ticker"] = None

sel_state = st.session_state.get(stock_table_key, {})
sel_rows = (sel_state.get("selection", {}) or {}).get("rows", [])

if sel_rows:
    row_idx = sel_rows[0]
    try:
        ticker_val = str(stock_present_filtered.iloc[row_idx]["stock_ticker"]).strip()
        if ticker_val:
            st.session_state["last_selected_ticker"] = ticker_val
    except Exception as e:
        st.warning(f"Could not read selected row: {e}")

ticker_to_plot = st.session_state.get("last_selected_ticker")
if ticker_to_plot:
    fig = stocks.StockPlot(ticker_to_plot)  # must return a Matplotlib figure
    if fig is not None:
        st.pyplot(fig, use_container_width=True)


# ---------- Manual input table + Send ----------
st.subheader("Your tickers & comments")

# initialize once
if "notes_df" not in st.session_state:
    st.session_state.notes_df = pd.DataFrame(
        {"stock_ticker": [""] * 6, "comment": [""] * 6}
    )

with st.form("notes_form", clear_on_submit=False):
    edited_notes = st.data_editor(
        st.session_state.notes_df,
        use_container_width=True,
        num_rows="fixed",  # keeps it at 6 rows (change to "dynamic" if you want add/remove)
        key="notes_editor",
        column_config={
            "stock_ticker": st.column_config.TextColumn(
                "stock_ticker",
                help="e.g., AAPL, MSFT",
                max_chars=10,
                required=False,
            ),
            "comment": st.column_config.TextColumn(
                "comment",
                help="your note for this ticker",
                required=False,
            ),
        },
    )

    send_clicked = st.form_submit_button("Send")
    if send_clicked:
        # persist the latest edits
        st.session_state.notes_df = edited_notes

        # TODO: hook up your function here:
        # result = your_function(edited_notes)

        st.success("Notes captured. (Connect your function in the TODO section.)")
        # Optionally preview what you'll send:
        st.dataframe(edited_notes, use_container_width=True, hide_index=True)
