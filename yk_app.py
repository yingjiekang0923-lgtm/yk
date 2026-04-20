import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. 頁面基本設定
st.set_page_config(page_title="YK 美股戰術指標監控", layout="wide")

# --- 密碼保護功能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔐 YK 戰術指標 - 私人訪問")
        password = st.text_input("請輸入密碼以查看數據", type="password")
        if st.button("登入"):
            if password == "yk":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("密碼錯誤")
        return False
    return True

if not check_password():
    st.stop()

# --- 狀態評估邏輯 ---
def get_status(name, value):
    try:
        val_str = str(value).replace('%', '')
        num = float(val_str)
        if "Stochastic" in name:
            if num >= 80: return "🔴 超買 (高檔)"
            if num <= 20: return "🟢 超賣 (機會)"
            return "🟡 中性"
        if "ROC" in name:
            if num > 20: return "😨 恐慌升溫"
            if num < -20: return "😌 情緒回穩"
            return "🟡 平穩"
        if "dma" in name:
            if num >= 80: return "🔥 極度熱絡"
            if num <= 20: return "❄️ 市場冰點"
            return "🟡 正常"
        return "🟡 觀察"
    except:
        return "N/A"

# --- 獲取 5 天收盤數據 ---
@st.cache_data(ttl=3600) # 每小時檢查一次
def fetch_closing_data():
    # 抓取充足的歷史數據以計算 15週隨機指標 (約 75 個交易日)
    vix_df = yf.download("^VIX", period="3mo")
    spy_df = yf.download("SPY", period="6mo")
    
    # 確保數據是收盤後的 (取最後 5 筆已結算數據)
    vix_close = vix_df['Close'].tail(5)
    
    # 計算 VIX 10-day ROC
    vix_all_close = vix_df['Close']
    vix_roc = (vix_all_close / vix_all_close.shift(10) - 1) * 100
    vix_roc_5 = vix_roc.tail(5)
    
    # 計算 15-Week Stochastic (用 75 交易日代表 15 週)
    spy_low = spy_df['Low'].rolling(window=75).min()
    spy_high = spy_df['High'].rolling(window=75).max()
    stoch = ((spy_df['Close'] - spy_low) / (spy_high - spy_low)) * 100
    stoch_5 = stoch.tail(5)
    
    # 獲取日期作為列頭
    dates = [d.strftime("%a. %d-%b") for d in vix_close.index]
    
    return dates, vix_close.values, vix_roc_5.values, stoch_5.values

dates, vix_vals, roc_vals, stoch_vals = fetch_closing_data()

# --- 靜態數據 (需手動在程式碼更新最新值) ---
# 為了配合 5 天顯示，這裡保留前 4 天的歷史，並把最新數據放最後
static_data = {
    "% of SPX Stocks > 10-dma": ["12.33%", "16.10%", "8.75%", "13.32%", "29.08%"],
    "% of SPX Stocks > 50-dma": ["18.89%", "21.07%", "14.12%", "15.71%", "19.02%"],
    "% of SPX Stocks > 200-dma": ["39.10%", "38.50%", "39.00%", "39.80%", "40.25%"],
    "NAAIM Exposure Index": ["54.33%", "54.33%", "54.33%", "54.33%", "43.01%"]
}

indicators = [
    "% of SPX Stocks > 10-dma",
    "% of SPX Stocks > 50-dma",
    "% of SPX Stocks > 200-dma",
    "CBOE Volatility Index (VIX)",
    "VIX 10-day ROC",
    "S&P 500 15-Week Stochastic",
    "NAAIM Exposure Index"
]

# 組合表格
table_rows = []
for ind in indicators:
    if ind in static_data:
        row_vals = static_data[ind]
    elif "VIX 10-day ROC" in ind:
        row_vals = [f"{v:.2f}%" for v in roc_vals]
    elif "Stochastic" in ind:
        row_vals = [f"{v:.2f}" for v in stoch_vals]
    else:
        row_vals = [f"{v:.2f}" for v in vix_vals]
    
    status = get_status(ind, row_vals[-1])
    table_rows.append([ind] + row_vals + [status])

# 欄位定義
columns = ["S&P 500 Index (SPX) Tactical Indicators"] + dates + ["狀態評估"]
df = pd.DataFrame(table_rows, columns=columns)

# --- UI 渲染 ---
st.title("📊 YK 戰術指標 - 每日收盤監控")
st.table(df) # 使用 st.table 讓外觀更接近靜態報告

st.info(f"💡 目前顯示的是截至 {dates[-1]} 的收盤數據。數據每小時自動校準一次。")

if st.button("登出"):
    st.session_state["password_correct"] = False
    st.rerun()