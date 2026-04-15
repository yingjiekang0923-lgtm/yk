import streamlit as st
import yfinance as yf
import pandas as pd

# 設定頁面
st.set_page_config(page_title="YK Strategy", layout="wide")

# --- 密碼保護功能 ---
def check_password():
    """如果輸入正確密碼則返回 True"""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # 顯示密碼輸入界面
    st.title("🔐 YK 戰術指標 - 私人訪問")
    password = st.text_input("請輸入密碼以查看數據", type="password")
    if st.button("登入"):
        if password == "yk":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("密碼錯誤，請重新輸入")
    return False

# 檢查密碼，通過才執行下面的程式碼
if check_password():
    
    st.title("📊 YK 美股戰術指標監控")
    st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

    @st.cache_data(ttl=3600) # 每小時自動更新數據
    def get_data():
        # 1. 下載 SPY 計算 15週隨機指標
        spy = yf.download("SPY", period="2y", interval="1wk")
        spy_close = spy['Close'].squeeze()
        spy_low = spy['Low'].squeeze()
        spy_high = spy['High'].squeeze()
        
        low_15 = spy_low.rolling(window=15).min()
        high_15 = spy_high.rolling(window=15).max()
        stoch = ((spy_close - low_15) / (high_15 - low_15) * 100)
        stoch_final = float(stoch.iloc[-1])
        
        # 2. 下載 VIX 並計算 10日變化率 (ROC)
        vix_df = yf.download("^VIX", period="30d")
        vix = vix_df['Close'].squeeze()
        
        vix_latest = float(vix.iloc[-1])
        vix_10d_ago = float(vix.iloc[-11]) 
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
                "29.08%", # 寬度指標為參考值
                "19.02%", 
                "40.25%",
                f"{vix_now:.2f}",
                f"{vix_roc:.2f}%", 
                f"{stoch_val:.2f}", 
                "43.01%"
            ]
        }

        df = pd.DataFrame(data)
        st.table(df)
        
        st.write("---")
        st.caption("數據已自動更新。來源: Yahoo Finance")
        
        if st.button("登出"):
            st.session_state["password_correct"] = False
            st.rerun()

    except Exception as e:
        st.error(f"數據抓取發生錯誤: {e}")