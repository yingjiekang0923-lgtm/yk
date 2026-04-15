import streamlit as st
import yfinance as yf
import pandas as pd

# 設定頁面
st.set_page_config(page_title="YK Strategy", layout="wide")

st.title("📊 YK 美股戰術指標監控")
st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

@st.cache_data(ttl=3600)
def get_data():
    # 1. 下載 SPY (S&P 500 ETF) 計算 15週隨機指標
    spy = yf.download("SPY", period="2y", interval="1wk")
    # 處理可能的多重索引格式
    spy_close = spy['Close'].squeeze()
    spy_low = spy['Low'].squeeze()
    spy_high = spy['High'].squeeze()
    
    low_15 = spy_low.rolling(window=15).min()
    high_15 = spy_high.rolling(window=15).max()
    stoch = ((spy_close - low_15) / (high_15 - low_15) * 100)
    stoch_final = float(stoch.iloc[-1])
    
    # 2. 下載 VIX 並計算 10日變化率
    vix_df = yf.download("^VIX", period="30d")
    vix = vix_df['Close'].squeeze() # 強制轉為單一序列
    
    vix_latest = float(vix.iloc[-1])
    vix_10d_ago = float(vix.iloc[-11]) # 取10個交易日前
    vix_roc = ((vix_latest / vix_10d_ago) - 1) * 100
    
    return vix_roc, stoch_final, vix_latest

try:
    vix_roc, stoch_val, vix_now = get_data()

    # 建立展示表格
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
            "29.08%", # 寬度指標建議參考專業數據源手工更新或接入付費 API
            "19.02%", 
            "40.25%",
            f"{vix_now:.2f}",
            f"{vix_roc:.2f}%", 
            f"{stoch_val:.2f}", 
            "43.01%"
        ]
    }

    df = pd.DataFrame(data)
    
    # 使用表格顯示
    st.table(df)
    
    # 顯示更新時間
    st.write("---")
    st.caption("數據更新成功！來源: YFinance. 指標 1, 2, 3, 7 為基準參考值。")

except Exception as e:
    st.error(f"數據抓取發生錯誤: {e}")
    st.write("請檢查網路連接或稍後再試。")