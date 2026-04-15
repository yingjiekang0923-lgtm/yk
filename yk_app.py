import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="YK Strategy", layout="wide")

st.title("📊 YK 美股戰術指標監控")
st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

@st.cache_data(ttl=3600)
def get_data():
    # 1. 下載 SPY 計算 15週隨機指標
    spy = yf.download("SPY", period="1y", interval="1wk")
    low_15 = spy['Low'].rolling(window=15).min()
    high_15 = spy['High'].rolling(window=15).max()
    # 計算最新的一筆隨機指標數值
    stoch = ((spy['Close'] - low_15) / (high_15 - low_15) * 100)
    stoch_final = float(stoch.iloc[-1].iloc[0]) if isinstance(stoch.iloc[-1], pd.Series) else float(stoch.iloc[-1])
    
    # 2. 下載 VIX 並計算 10日變化率
    vix = yf.download("^VIX", period="20d")['Close']
    vix_latest = float(vix.iloc[-1])
    vix_10d_ago = float(vix.iloc[-10])
    vix_roc = ((vix_latest / vix_10d_ago) - 1) * 100
    
    return vix_roc, stoch_final, vix_latest

vix_roc, stoch_val, vix_now = get_data()

# 建立表格 (依照你要求的 6 個項目)
data = {
    "S&P 500 Index (SPX) Tactical Indicators": [
        "% of SPX Stocks > 10-dma", 
        "% of SPX Stocks > 50-dma", 
        "% of SPX Stocks > 200-dma", 
        "CBOE Volatility Index (VIX)",
        "VIX 10-day ROC", 
        "S&P 500 15-Week Stochastic", 
        "NAAIM Exposure Index"
    ],
    "Latest Level": [
        "29.08%", # 此處目前為模擬值，如需全自動計算需加入500支股票掃描邏輯
        "19.02%", 
        "40.25%",
        f"{vix_now:.2f}",
        f"{vix_roc:.2f}", 
        f"{stoch_val:.2f}", 
        "43.01%"
    ]
}

df = pd.DataFrame(data)
st.table(df)

st.write("---")
st.caption("數據來源: YFinance / YK Strategy Engine")