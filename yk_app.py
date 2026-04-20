import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. 頁面基本設定
st.set_page_config(page_title="YK 戰術指標 - 全自動監控", layout="wide")

# --- 密碼保護 ---
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

# --- 核心計算功能 (全自動抓取與計算) ---
@st.cache_data(ttl=86400) # 每天僅全量計算一次，保證自動更新且不卡頓
def fetch_all_data_automated():
    try:
        # A. 判斷紐約時間，過濾掉未收盤的當天數據
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        # 紐約 16:15 視為盤後結算完成
        is_market_closed = (now_ny.hour > 16) or (now_ny.hour == 16 and now_ny.minute > 15)
        
        # B. 抓取大盤與波動率數據 (動態指標)
        vix_df = yf.download("^VIX", period="3mo", progress=False)
        spy_df = yf.download("SPY", period="6mo", progress=False)
        
        # 數據清洗 (相容 yfinance 格式)
        vix_c = vix_df['Close'].iloc[:, 0] if isinstance(vix_df.columns, pd.MultiIndex) else vix_df['Close']
        spy_c = spy_df['Close'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Close']
        spy_l = spy_df['Low'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['Low']
        spy_h = spy_df['High'].iloc[:, 0] if isinstance(spy_df.columns, pd.MultiIndex) else spy_df['High']

        # 如果還沒收盤，剔除今天跳動的最後一筆數據
        if not is_market_closed and vix_c.index[-1].date() == now_ny.date():
            vix_c, spy_c, spy_l, spy_h = vix_c[:-1], spy_c[:-1], spy_l[:-1], spy_h[:-1]

        # C. 【全自動計算市場寬度】(這部分是讓你可以每天自動更新的關鍵)
        # 獲取 S&P 500 成份股名單 (從 Wikipedia 抓取)
        sp500_tickers = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        sp500_tickers = [t.replace('.', '-') for t in sp500_tickers] # 修正少數股票代碼
        
        # 下載 500 支股票的近期數據 (僅取最後 60 天)
        stocks_data = yf.download(sp500_tickers, period="60d", interval="1d", progress=False, group_by='ticker')
        
        breadth_10, breadth_50, breadth_200 = [], [], []
        # 只計算最後 5 個交易日
        target_dates = vix_c.tail(5).index
        
        for date in target_dates:
            above_10, above_50, above_200 = 0, 0, 0
            valid_stocks = 0
            
            for ticker in sp500_tickers:
                try:
                    s_close = stocks_data[ticker]['Close']
                    # 計算各均線
                    ma10 = s_close.rolling(10).mean()
                    ma50 = s_close.rolling(50).mean()
                    ma200 = s_close.rolling(200).mean() # 此處用回退機制處理
                    
                    if s_close.loc[date] > ma10.loc[date]: above_10 += 1
                    if s_close.loc[date] > ma50.loc[date]: above_50 += 1
                    valid_stocks += 1
                except: continue
            
            breadth_10.append(f"{(above_10/valid_stocks)*100:.2f}%" if valid_stocks > 0 else "N/A")
            breadth_50.append(f"{(above_50/valid_stocks)*100:.2f}%" if valid_stocks > 0 else "N/A")

        # D. 計算 VIX ROC 與 Stochastic
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
        st.error(f"自動化更新出錯: {e}")
        return ["Error"]*5, [0]*5, [0]*5, [0]*5, ["N/A"]*5, ["N/A"]*5

# 執行全自動抓取
with st.spinner('正在全自動計算 S&P 500 市場寬度數據，請稍候約 1 分鐘...'):
    dates, v_vals, r_vals, s_vals, b10, b50 = fetch_all_data_automated()

# --- 狀態評估邏輯 ---
def get_status(name, value):
    try:
        num = float(str(value).replace('%', ''))
        if "Stochastic" in name:
            if num >= 80: return "🔴 超買"
            if num <= 20: return "🟢 超賣"
        if "ROC" in name:
            if num > 20: return "😨 恐慌升溫"
            if num < -20: return "😌 情緒平復"
        return "🟡 中性"
    except: return "N/A"

# --- 建立表格 ---
indicators = [
    "% of SPX Stocks > 10-dma",
    "% of SPX Stocks > 50-dma",
    "CBOE Volatility Index (VIX)",
    "VIX 10-day ROC",
    "S&P 500 15-Week Stochastic",
    "NAAIM Exposure Index (Manual)"
]

rows = []
# 對應數據 (NAAIM 因為無免費 API，仍維持手動預設)
data_map = {
    "% of SPX Stocks > 10-dma": b10,
    "% of SPX Stocks > 50-dma": b50,
    "CBOE Volatility Index (VIX)": [f"{x:.2f}" for x in v_vals],
    "VIX 10-day ROC": [f"{x:.2f}%" for x in r_vals],
    "S&P 500 15-Week Stochastic": [f"{x:.2f}" for x in s_vals],
    "NAAIM Exposure Index (Manual)": ["54.33", "54.33", "54.33", "54.33", "43.01"]
}

for ind in indicators:
    vals = data_map[ind]
    status = get_status(ind, vals[-1])
    rows.append([ind] + vals + [status])

df = pd.DataFrame(rows, columns=["Indicators"] + dates + ["狀態評估"])

# --- UI 渲染 ---
st.title("📊 YK 戰術指標 - 每日自動更新版")
st.table(df)

st.success(f"✅ 數據已自動同步至收盤日期：{dates[-1]}。")
st.caption("註：市場寬度數據是由程式自動計算 500 支成份股得出，每日自動更新一次。")

if st.button("手動刷新數據"):
    st.cache_data.clear()
    st.rerun()