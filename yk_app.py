import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

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
        val_str = str(value).replace('%', '').replace(',', '')
        num = float(val_str)
        if "Stochastic" in name:
            if num >= 80: return "🔴 超買 (高檔警戒)"
            if num <= 20: return "🟢 超賣 (底部機會)"
        if "ROC" in name:
            if num > 20: return "😨 恐慌飆升"
            if num < -20: return "😌 情緒回穩"
        if "dma" in name:
            if num >= 80: return "🔥 極度熱絡"
            if num <= 20: return "❄️ 市場冰點"
        return "🟡 中性"
    except:
        return "N/A"

# --- 獲取 5 天收盤數據 ---
@st.cache_data(ttl=3600)
def fetch_closing_data():
    try:
        # 抓取足夠歷史資料以計算指標
        vix_df = yf.download("^VIX", period="3mo", progress=False)
        spy_df = yf.download("SPY", period="6mo", progress=False)
        
        # 處理 yfinance 可能產生的 MultiIndex 或 Series
        def clean_series(df, col):
            if isinstance(df.columns, pd.MultiIndex):
                return df[col].iloc[:, 0]
            return df[col]

        vix_c = clean_series(vix_df, 'Close')
        spy_c = clean_series(spy_df, 'Close')
        spy_l = clean_series(spy_df, 'Low')
        spy_h = clean_series(spy_df, 'High')

        # 計算 VIX 10-day ROC
        vix_roc = (vix_c / vix_c.shift(10) - 1) * 100
        
        # 計算 15-Week Stochastic (約 75 交易日)
        low_75 = spy_l.rolling(window=75).min()
        high_75 = spy_h.rolling(window=75).max()
        stoch = ((spy_c - low_75) / (high_75 - low_75)) * 100
        
        # 取得最後 5 個交易日
        dates = [d.strftime("%a. %d-%b") for d in vix_c.tail(5).index]
        vix_vals = vix_c.tail(5).tolist()
        roc_vals = vix_roc.tail(5).tolist()
        stoch_vals = stoch.tail(5).tolist()
        
        return dates, vix_vals, roc_vals, stoch_vals
    except Exception as e:
        st.error(f"數據抓取錯誤: {e}")
        return ["N/A"]*5, [0.0]*5, [0.0]*5, [0.0]*5

dates_header, v_list, r_list, s_list = fetch_closing_data()

# --- 靜態數據 (此處根據您的截圖手動預設，您可自行修改最後一格) ---
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

# 構建表格行
rows = []
for ind in indicators:
    if ind in static_data:
        vals = static_data[ind]
    elif "VIX 10-day ROC" in ind:
        vals = [f"{x:.2f}%" for x in r_list]
    elif "Stochastic" in ind:
        vals = [f"{x:.2f}" for x in s_list]
    else:
        vals = [f"{x:.2f}" for x in v_list]
    
    # 狀態評估只針對最後一天的數值
    status = get_status(ind, vals[-1])
    rows.append([ind] + vals + [status])

# 建立 DataFrame
columns = ["S&P 500 Index (SPX) Tactical Indicators"] + dates_header + ["狀態評估"]
df = pd.DataFrame(rows, columns=columns)

# --- UI 渲染 ---
st.title("📊 YK 美股戰術指標監控")
st.markdown("參考來源：Dwyer Strategy")

# 使用 st.table 確保格式跟網頁版一致，不會有捲軸
st.table(df)

st.caption(f"💡 數據已更新至收盤。最近更新日期：{dates_header[-1]}。數據源：Yahoo Finance / NAAIM")

if st.button("登出"):
    st.session_state["password_correct"] = False
    st.rerun()
