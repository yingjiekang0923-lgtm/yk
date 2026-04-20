import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
import requests
import io

# 1. Page Configuration
st.set_page_config(page_title="YK Tactical Indicators", layout="wide")

# --- Password Protection ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 YK Tactical Indicators - Private Access")
        password = st.text_input("Enter password to view data", type="password")
        if st.button("Login"):
            if password == "yk":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    return True

if not check_password():
    st.stop()

# --- Core Calculation (Fully Automated) ---
@st.cache_data(ttl=86400) # Updates once every 24 hours
def fetch_all_data_automated():
    try:
        # Check NY time to ensure we are using closed data
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        is_market_closed = (now_ny.hour > 16) or (now_ny.hour == 16 and now_ny.minute > 15)
        
        vix_df = yf.download("^VIX", period="3mo", progress=False)
        spy_df = yf.download("SPY", period="6mo", progress=False)
        
        vix_c = vix_df['Close'].iloc[:, 0] if isinstance(vix_df.columns, pd.MultiIndex) else vix_df['Close']
        spy_c = spy_df['Close'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Close']
        spy_l = spy_df['Low'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Low']
        spy_h = spy_df['High'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['High']

        if not is_market_closed and vix_c.index[-1].date() == now_ny.date():
            vix_c, spy_c, spy_l, spy_h = vix_c[:-1], spy_c[:-1], spy_l[:-1], spy_h[:-1]

        # 🚀 解決 Pandas 誤認檔名的問題：使用 io.StringIO
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        html_data = requests.get(url, headers=headers).text
        
        # 這裡強制把 HTML 文字轉成資料流
        sp500_tickers = pd.read_html(io.StringIO(html_data))[0]['Symbol'].tolist()
        sp500_tickers = [t.replace('.', '-') for t in sp500_tickers]
        
        stocks_data = yf.download(sp500_tickers, period="60d", interval="1d", progress=False, group_by='ticker')
        
        breadth_10, breadth_50 = [], []
        target_dates = vix_c.tail(5).index
        
        for date in target_dates:
            above_10, above_50 = 0, 0
            valid_stocks = 0
            
            for ticker in sp500_tickers:
                try:
                    s_close = stocks_data[ticker]['Close']
                    ma10 = s_close.rolling(10).mean()
                    ma50 = s_close.rolling(50).mean()
                    
                    if s_close.loc[date] > ma10.loc[date]: above_10 += 1
                    if s_close.loc[date] > ma50.loc[date]: above_50 += 1
                    valid_stocks += 1
                except: continue
            
            breadth_10.append(f"{(above_10/valid_stocks)*100:.2f}%" if valid_stocks > 0 else "N/A")
            breadth_50.append(f"{(above_50/valid_stocks)*100:.2f}%" if valid_stocks > 0 else "N/A")

        vix_roc = (vix_c / vix_c.shift(10) - 1) * 100
        low_75 = spy_l.rolling(window=75).min()
        high_75 = spy_h.rolling(window=75).max()
        stoch = ((spy_c - low_75) / (high_75 - low_75)) * 100
        
        dates_header = [d.strftime("%a. %d-%b") for d in vix_c.tail(5).index]
        v_list = vix_c.tail(5).tolist()
        r_list = vix_roc.tail(5).tolist()
        s_list = stoch.tail(5).tolist()
        
        return dates_header, v_list, r_list, s_list, breadth_10, breadth_50
    except Exception as e:
        st.error(f"🚨 Data Fetch Error: {str(e)}")
        return ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"], [0]*5, [0]*5, [0]*5, ["N/A"]*5, ["N/A"]*5

with st.spinner('Calculating S&P 500 Market Breadth automatically, please wait (~1 min)...'):
    dates, v_vals, r_vals, s_vals, b10, b50 = fetch_all_data_automated()

# --- Status Assessment Logic ---
def get_status(name, value):
    try:
        num = float(str(value).replace('%', ''))
        if "Stochastic" in name:
            if num >= 80: return "🔴 Overbought"
            if num <= 20: return "🟢 Oversold"
        if "ROC" in name:
            if num > 20: return "😨 Volatility Surging"
            if num < -20: return "😌 Sentiment Calming"
        if "dma" in name:
            if num >= 80: return "🔥 Extreme Optimism"
            if num <= 20: return "❄️ Extreme Pessimism"
        return "🟡 Neutral"
    except: return "N/A"

# --- Build Table ---
indicators = [
    "% of SPX Stocks > 10-dma",
    "% of SPX Stocks > 50-dma",
    "CBOE Volatility Index (VIX)",
    "VIX 10-day ROC",
    "S&P 500 15-Week Stochastic",
    "NAAIM Exposure Index (Manual)"
]

rows = []
data_map = {
    "% of SPX Stocks > 10-dma": b10,
    "% of SPX Stocks > 50-dma": b50,
    "CBOE Volatility Index (VIX)": [f"{x:.2f}" for x in v_vals],
    "VIX 10-day ROC": [f"{x:.2f}%" for x in r_vals],
    "S&P 500 15-Week Stochastic": [f"{x:.2f}" for x in s_vals],
    "NAAIM Exposure Index (Manual)": ["54.33%", "54.33%", "54.33%", "54.33%", "43.01%"]
}

for ind in indicators:
    vals = data_map[ind]
    status = get_status(ind, vals[-1])
    rows.append([ind] + vals + [status])

df = pd.DataFrame(rows, columns=["S&P 500 Index (SPX) Tactical Indicators"] + dates + ["Status Assessment"])

# --- UI Rendering ---
st.title("📊 YK Tactical Indicators - Daily Auto Update")
st.table(df)

st.success(f"✅ Data successfully synced to closing date: {dates[-1]}.")
st.caption("Note: Market breadth data (% > 10/50 dma) is automatically calculated from S&P 500 constituents and updated daily.")

if st.button("Log Out"):
    st.session_state["password_correct"] = False
    st.rerun()