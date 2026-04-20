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

# 如果密碼未通過，停止執行後續程式碼
if not check_password():
    st.stop()

# --- 狀態評估邏輯 ---
def get_status(name, value):
    try:
        # 將字串中的 % 符號去掉並轉換為浮點數
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
            if num >= 80: return "🐂 經理人極度樂觀"
            if num <= 20: return "🐻 經理人極度悲觀"
            return "🟡 正常配置"
            
        return "🟡 觀察中"
    except Exception:
        return "N/A"

# --- 獲取即時數據 (設定每天更新一次) ---
@st.cache_data(ttl=86400) # ttl=86400秒 (24小時)，確保每天自動更新
def fetch_dynamic_data():
    try:
        # 抓取 VIX 數據 (過去 1 個月，以確保有足夠的 10 天前數據)
        vix_data = yf.download("^VIX", period="1mo")
        # 抓取 SPY 數據 (過去 1 年，以計算 15 週隨機指標)
        spy_data = yf.download("SPY", period="1y", interval="1wk")
        
        # 處理最新 VIX 與 10天前的 VIX (ROC 計算)
        vix_latest = float(vix_data['Close'].iloc[-1].item() if isinstance(vix_data['Close'].iloc[-1], pd.Series) else vix_data['Close'].iloc[-1])
        vix_10d_ago = float(vix_data['Close'].iloc[-11].item() if isinstance(vix_data['Close'].iloc[-11], pd.Series) else vix_data['Close'].iloc[-11])
        vix_roc = ((vix_latest / vix_10d_ago) - 1) * 100
        
        # 計算 15-Week Stochastic
        low_15 = spy_data['Low'].rolling(window=15).min()
        high_15 = spy_data['High'].rolling(window=15).max()
        
        latest_close = float(spy_data['Close'].iloc[-1].item() if isinstance(spy_data['Close'].iloc[-1], pd.Series) else spy_data['Close'].iloc[-1])
        latest_low_15 = float(low_15.iloc[-1].item() if isinstance(low_15.iloc[-1], pd.Series) else low_15.iloc[-1])
        latest_high_15 = float(high_15.iloc[-1].item() if isinstance(high_15.iloc[-1], pd.Series) else high_15.iloc[-1])
        
        stoch_15w = ((latest_close - latest_low_15) / (latest_high_15 - latest_low_15)) * 100
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        return current_date, vix_latest, vix_roc, stoch_15w
    except Exception as e:
        # 若抓取失敗的回退機制
        return datetime.now().strftime("%Y-%m-%d"), 0.0, 0.0, 0.0

# 執行獲取動態數據
date_str, vix_now, vix_roc_val, stoch_val = fetch_dynamic_data()

# --- 建立表格數據 ---
# 這些是需要手動更新的靜態指標 (市場寬度與 NAAIM 通常無免費 API)
static_values = {
    "% of SPX Stocks > 10-dma": "29.08%",
    "% of SPX Stocks > 50-dma": "19.02%",
    "% of SPX Stocks > 200-dma": "40.25%",
    "NAAIM Exposure Index": "43.01%"
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

values = [
    static_values["% of SPX Stocks > 10-dma"],
    static_values["% of SPX Stocks > 50-dma"],
    static_values["% of SPX Stocks > 200-dma"],
    f"{vix_now:.2f}",
    f"{vix_roc_val:.2f}%",
    f"{stoch_val:.2f}",
    static_values["NAAIM Exposure Index"]
]

# 組合成 DataFrame，完美對齊你截圖中的名稱
df = pd.DataFrame({
    "S&P 500 Index (SPX) Tactical Indicators": indicators,
    "Date (日期)": [date_str] * len(indicators),
    "Latest Level": values,
    "Status Assessment (狀態評估)": [get_status(indicators[i], values[i]) for i in range(len(indicators))]
})

# --- UI 渲染 ---
st.title("📊 YK 美股戰術指標監控")
st.markdown("參考來源：Dwyer Strategy | 網址命名：**YK**")

# 顯示表格 (使用 st.dataframe 可以自動適應寬度並隱藏左側索引)
st.dataframe(df, hide_index=True, use_container_width=True)

st.markdown("---")
st.markdown("數據已自動更新。來源: Yahoo Finance (VIX 與 Stochastic 動態計算)。指標 1, 2, 3, 7 為基準參考值。")

# 登出按鈕
if st.button("登出"):
    st.session_state["password_correct"] = False
    st.rerun()