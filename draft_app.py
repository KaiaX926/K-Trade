# app.py
import streamlit as st
import pandas as pd
import numpy as np

# ---------- Page setup ----------
st.set_page_config(page_title="Sector/Industry Dashboard", layout="wide")

# CSS: force ~30% sidebar and ~70% main content
st.markdown("""
<style>
/* Sidebar ~30% of viewport width */
[data-testid="stSidebar"] {
    min-width: 30vw;
    max-width: 30vw;
}
/* Main content ~70% of viewport width */
section.main > div {
    max-width: 70vw;
}
/* Make the main block stretch to use available width */
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}
/* Reduce padding inside sidebar for tighter layout */
[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ---------- Get functions ----------
import Market_screener as ms
import Sector_screener as secs
import Stock_screener as stocks


# ---------- Get data ----------
date, market_tbl = ms.MarketUpdate()
focus_section = ['Information Technology','Health Care','Financials','Consumer Discretionary','Consumer Staples','Communication Services']
df_sector, focus_yahoo_section = secs.SectorToIndustry(focus_section = focus_section)
industry_tbl = secs.IndustryPositionFact(date, df_sector)
industry_filtered = secs.IndustryFilter_Trend(date, industry_tbl)
stock_list = stocks.StockFilter_SwingScreen_MarketCapital(industry_candiadte = industry_filtered)
stock_tbl = stocks.StockFilter_SwingScreen(stock_list = stock_list)

# Big table placeholder (lots of columns -> horizontal scroll)
# def make_placeholder_table(rows=200, cols=25, seed=42):
#     rng = np.random.default_rng(seed)
#     data = rng.normal(size=(rows, cols)).round(3)
#     columns = [f"col_{i:02d}" for i in range(cols)]
#     df = pd.DataFrame(data, columns=columns)
#     df.insert(0, "ticker", [f"TCKR{i:04d}" for i in range(rows)])
#     df.insert(1, "industry", rng.choice(sum(SECTORS.values(), []), size=rows))
#     df.insert(2, "sector", rng.choice(list(SECTORS.keys()), size=rows))
#     return df

# big_df = make_placeholder_table()

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Filters")
    sectors = df_sector.reset_index()
    # Dropdown for Sector
    sector = st.selectbox("Sector", options=focus_yahoo_section, index=0)

    # Filter industries belonging to the selected sector
    industries = sectors[sectors["sector"] == sector]["name"].drop_duplicates().sort_values()
    industries_highlight = pd.DataFrame({"Industry": industries})

    # Add 'Prioritize' column — True if industry appears in industry_filtered.industry
    industries_highlight["Prioritize"] = industries_highlight["Industry"].isin(
        industry_filtered["industry"].unique()
    )
    industries_highlight = industries_highlight.sort_values(by="Prioritize", ascending=False)

    print(industries_highlight)

    # Display industries table
    # st.subheader(f"Industries in {sector}")
    # st.dataframe(
    #     pd.DataFrame({"Industry": industries, "Prioritize": True}),
    #     use_container_width=True,
    #     hide_index=True
    # )

    def highlight_row(row):
        if row["Prioritize"]:
            return ["background-color: #d4f8d4; color: black;"] * len(row)
        else:
            return [""] * len(row)
    
    styled_df = industries_highlight.style.apply(highlight_row, axis=1)
    
    # Display styled dataframe
    st.dataframe(
        styled_df.hide(axis="columns", subset=["Prioritize"]),
        use_container_width=True,
        hide_index=True
    )


# ---------- Main body ----------
st.title("Sector → Industry Explorer (Template)")

# ✅ Latest Close Date Section
st.subheader("📅 Latest Close Date")
latest_date = date #big_df["close_date"].max().strftime("%Y-%m-%d")
st.info(f"The latest close date in the dataset is **{latest_date}**.")

# --- Results table with single-row selection ---
st.subheader("Results Table (click a row to plot)")
TABLE_HEIGHT = 200
table_key = "stock_tbl_select"

st.dataframe(
    stock_tbl,
    use_container_width=True,
    height=TABLE_HEIGHT,
    hide_index=True,
    selection_mode="single-row",   # requires Streamlit >= 1.33
    on_select="rerun",             # selection triggers rerun; we'll persist it below
    key=table_key
)

# --- Chart area ---
st.subheader("Chart")
chart_placeholder = st.empty()

# Initialize state keys
if "last_selected_ticker" not in st.session_state:
    st.session_state["last_selected_ticker"] = None

# Read current selection from the table widget
sel_state = st.session_state.get(table_key, {})
sel_rows = (sel_state.get("selection", {}) or {}).get("rows", [])

# If there is a fresh selection, persist its ticker to session_state
if sel_rows:
    row_idx = sel_rows[0]
    try:
        ticker_val = str(stock_tbl.iloc[row_idx]["stock_code"]).strip()
        if ticker_val:
            st.session_state["last_selected_ticker"] = ticker_val
    except Exception as e:
        st.warning(f"Could not read selected row: {e}")

# Use the persisted ticker to plot (survives reruns)
ticker_to_plot = st.session_state.get("last_selected_ticker")

if ticker_to_plot:
    fig = stocks.StockPlot(ticker_to_plot)   # must RETURN a Matplotlib fig
    if fig is not None:
        chart_placeholder.pyplot(fig, use_container_width=True)

                
# # ---------- Notes ----------
# with st.expander("Notes"):
#     st.markdown("""
# - Replace the **SECTORS** dict and the `make_placeholder_table()` with your real data sources.
# - The sidebar width is enforced via CSS (`30vw`). The main content is constrained to `70vw`.
# - The top table uses `st.dataframe(height=...)` to allow vertical scrolling; many columns enable horizontal scrolling.
# - The chart is just a placeholder cumulative series; swap in your own plotting logic (Altair/Matplotlib/Plotly) if desired.
# """)
