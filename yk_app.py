import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="YK Strategy", layout="wide")

st.title("📊 YK 美股戰術指標監控")
st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

@st.cache_data(ttl=3600)
def get_data():
    # 下載 SPY 作為大盤代表
    spy = yf.download("SPY", period="1y", interval="1wk")
    low_15 = spy['Low'].rolling(window=15).min()
    high_15 = spy['High'].rolling(window=15).max()
    stoch = ((spy['Close'] - low_15) / (high_15 - low_15) * 100).iloc[-1]
    
    # 下載 VIX
    vix = yf.download("^VIX", period="20d")['Close']
    vix_roc = ((vix.iloc[-1] / vix.iloc[-10]) - 1) * 100
    
    return vix_roc, stoch

vix_roc, stoch_val = get_data()

# 建立表格
data = {
    "指標項目": ["% SPX Stocks > 10-dma", "% SPX Stocks > 50-dma", "% SPX Stocks > 200-dma", "VIX 10-day ROC", "SPX 15-Week Stochastic", "NAAIM Exposure Index"],
    "最新數值": ["29.08%", "19.02%", "40.25%", f"{vix_roc:.2f}", f"{stoch_val.values[0]:.2f}", "43.01%"]
}
df = pd.DataFrame(data)
st.table(df)