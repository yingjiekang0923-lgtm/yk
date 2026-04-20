import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 頁面基本設定 (必須是第一個 Streamlit 指令)
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

# --- 狀態評估邏輯 (基於最新一天的數據) ---
def get_status(name, value):
    try:
        val_str = str(value).replace('%', '')
        num = float(val_str)
        
        if "Stochastic" in name:
            if num >= 80: return "🔴 超買 (高檔警戒)"
            if num <= 20: return "🟢 超賣 (底部機會)"
            return "🟡 中性"
            
        if "ROC" in name:
            if num > 20: return "😨 恐慌飆升"
            if num < -20: return "😌 情緒回穩"
            return "🟡 平穩"
            
        if "dma" in name:
            if num >= 80: return "🔥 極度熱絡"
            if num <= 20: return "❄️ 市場冰點"
            return "🟡 正常"
            
        if "NAAIM" in name:
            if num >= 80: return "🐂 極度樂觀"
            if num <= 20: return "🐻 極度悲觀"
            return "🟡 正常配置"
            
        return "🟡 觀察中"
    except Exception:
        return "N/A"

# --- 獲取過去 5 天的動態數據 ---
@st.cache_data(ttl=86400) # 每天自動更新一次
def fetch_5day_dynamic_data():
    try:
        # 抓取較長週期的數據以確保計算無誤 (ROC需前10天，Stochastic需前75個交易日/約15週)
        vix_df = yf.download("^VIX", period="2mo")
        spy_df = yf.download("SPY", period="6mo")
        
        # 兼容 yfinance 新版 MultiIndex 格式
        vix_close = vix_df['Close']['^VIX'] if isinstance(vix_df.columns, pd.MultiIndex) else vix_df['Close']
        spy_close = spy_df['Close']['SPY'] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Close']
        spy_low = spy_df['Low']['SPY'] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Low']
        spy_high = spy_df['High']['SPY'] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['High']
        
        # 計算 VIX 10-day ROC
        vix_roc = (vix_close / vix_close.shift(10) - 1) * 100
        
        # 計算 SPY 15-Week Stochastic (使用 75 個交易日作為 15 週的近似值)
        low_75 = spy_low.rolling(window=75).min()
        high_75 = spy_high.rolling(window=75).max()
        stoch_15w = ((spy_close - low_75) / (high_75 - low_75)) * 100
        
        # 提取最後 5 個交易日的數據
        last_5_dates = vix_close.index[-5:]
        
        # 格式化日期作為表格列頭 (例如 "Fri. 22-Sep")
        formatted_dates = [d.strftime("%a. %d-%b") for d in last_5_dates]
        
        # 提取這 5 天的具體數值
        vix_vals = vix_close.iloc[-5:].values
        roc_vals = vix_roc.iloc[-5:].values
        stoch_vals = stoch_15w.iloc[-5:].values
        
        return formatted_dates, vix_vals, roc_vals, stoch_vals
    
    except Exception as e:
        # 錯誤處理回退
        return ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"], [0]*5, [0]*5, [0]*5

# 執行抓取
dates, vix_vals, roc_vals, stoch_vals = fetch_5day_dynamic_data()

# --- 建立表格數據 ---
# 靜態指標 (市場寬度與 NAAIM 需手動更新，此處提供 5 天的陣列佔位符，您可以根據實際情況修改)
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

# 構建每一列的數據
row_data = []
for indicator in indicators:
    if indicator in static_data:
        # 使用手動更新的靜態數據
        vals = static_data[indicator]
        latest_val = vals[-1]
    else:
        # 使用動態計算的數據
        if "VIX 10-day ROC" in indicator:
            vals = [f"{v:.2f}%" for v in roc_vals]
        elif "Stochastic" in indicator:
            vals = [f"{v:.2f}" for v in stoch_vals]
        else:
            vals = [f"{v:.2f}" for v in vix_vals]
        latest_val = vals[-1]
        
    # 計算狀態評估 (只看最後一天)
    status = get_status(indicator, latest_val)
    
    # 組合該指標的完整行數據
    row = [indicator] + vals + [status]
    row_data.append(row)

# 設定 DataFrame 列頭 (指標名稱 + 5天日期 + 狀態評估)
columns = ["S&P 500 Index (SPX) Tactical Indicators"] + dates + ["最新狀態評估"]
df = pd.DataFrame(row_data, columns=columns)

# --- UI 渲染 ---
st.title("📊 YK 美股戰術指標監控 (5日動態對比)")
st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

# 顯示表格 (自適應寬度並隱藏左側索引)
st.dataframe(df, hide_index=True, use_container_width=True)

st.markdown("---")
st.markdown("數據已自動更新。來源: Yahoo Finance (VIX 與 Stochastic 動態計算)。指標 1, 2, 3, 7 需手動維護過去 5 天陣列。")

# 登出按鈕
if st.button("登出"):
    st.session_state["password_correct"] = False
    st.rerun()