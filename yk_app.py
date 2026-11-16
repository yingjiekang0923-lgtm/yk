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


# ==========================================================
# 新增部分：只在原表格下方增加五项分析
# ==========================================================

def analysis_number(value):
    """将原表格数值转成数字；无效数据返回 None。"""
    try:
        number = float(str(value).replace("%", "").strip())
        if pd.isna(number) or abs(number) == float("inf"):
            return None
        return number
    except (TypeError, ValueError):
        return None


def analysis_format(value, suffix=""):
    if value is None:
        return "不可用"
    return f"{value:.2f}{suffix}"


@st.cache_data(ttl=900, show_spinner=False)
def fetch_analysis_prices(symbol):
    """仅供新增分析使用，不改变原表格的数据获取。"""
    prices = yf.Ticker(symbol).history(
        period="1y",
        interval="1d",
        auto_adjust=True,
        actions=False,
    )

    required = ["Close", "High", "Low", "Volume"]

    if prices.empty:
        raise ValueError(f"{symbol} 未返回行情，请检查代码。")

    if not all(column in prices.columns for column in required):
        raise ValueError(f"{symbol} 行情字段不完整。")

    prices = prices[required].copy()

    # 使用交易日期索引，便于个股与 SPY 对齐。
    prices.index = pd.DatetimeIndex(
        [timestamp.date() for timestamp in prices.index]
    )
    prices = prices.sort_index()
    prices = prices.loc[~prices.index.duplicated(keep="last")]

    now_ny = datetime.now(pytz.timezone("America/New_York"))

    # 面向美股：保守排除纽约时间 16:15 前的当天日线。
    if (now_ny.hour, now_ny.minute) < (16, 15):
        prices = prices.loc[
            prices.index < pd.Timestamp(now_ny.date())
        ]

    prices = prices.dropna(subset=["Close", "High", "Low"])

    if len(prices) < 60:
        raise ValueError(
            f"{symbol} 可用历史不足 60 个交易日，暂无法完整分析。"
        )

    return prices


st.divider()
st.header("🧭 市场与个股分析")
st.caption("市场环境 → 个股表现 → 判断依据 → 触发条件 → 风险")

# ----------------------------------------------------------
# 1. 市场环境：直接读取上方原表格
# ----------------------------------------------------------
st.subheader("1. 市场环境")

market_b10 = analysis_number(b10[-1])
market_b50 = analysis_number(b50[-1])
market_vix = analysis_number(v_vals[-1])
market_roc = analysis_number(r_vals[-1])
market_stoch = analysis_number(s_vals[-1])

market_valid = (
    market_b10 is not None
    and market_b50 is not None
    and market_vix is not None
    and market_vix > 0
    and market_roc is not None
)

if market_valid:
    # 固定规则分类，不是经过回测的交易信号。
    if (
        market_b10 >= 60
        and market_b50 >= 60
        and market_roc <= 0
    ):
        market_label = "偏积极"
        market_comment = (
            "多数成分股位于短中期均线上方，"
            "同时 VIX 未较 10 个交易日前上升，"
            "市场背景相对有利，但不能直接推导个股会上涨。"
        )
    elif (
        market_b10 < 40
        and market_b50 < 40
    ) or market_roc > 20:
        market_label = "偏谨慎"
        market_comment = (
            "市场宽度偏弱，或波动率快速上升。"
            "个股的上涨与突破需要更谨慎地验证。"
        )
    else:
        market_label = "混合 / 震荡"
        market_comment = (
            "市场宽度与波动率信号未形成一致方向，"
            "应优先观察个股自身趋势及相对强弱。"
        )

    st.info(f"市场环境：{market_label}。{market_comment}")
else:
    market_label = "无法确认"
    st.warning(
        "上方市场数据不完整或可能为失败后的占位值，"
        "暂不生成市场环境结论。个股分析仍可使用。"
    )

st.write(
    f"- 10 日均线上方比例：{analysis_format(market_b10, '%')}\n"
    f"- 50 日均线上方比例：{analysis_format(market_b50, '%')}\n"
    f"- VIX：{analysis_format(market_vix)}\n"
    f"- VIX 10 日变化：{analysis_format(market_roc, '%')}\n"
    f"- 上方表格随机指标：{analysis_format(market_stoch)}"
)

if market_valid and market_stoch is not None:
    if market_stoch >= 80:
        st.caption(
            "随机指标处于高位：可能反映强趋势，也可能伴随回撤风险，"
            "不单独作为卖出条件。"
        )
    elif market_stoch <= 20:
        st.caption(
            "随机指标处于低位：可能反映弱趋势，"
            "不单独作为抄底条件。"
        )

st.caption(
    f"市场分析使用上方表格最后一列：{dates[-1]}。"
    "原市场宽度算法保持不变，未在新增模块中重新验证样本覆盖率；"
    "原表格中的固定 NAAIM 数值不参与新增判断。"
)

# ----------------------------------------------------------
# 输入股票代码
# ----------------------------------------------------------
with st.form("five_part_analysis_form"):
    stock_symbol = st.text_input(
        "输入要分析的美股代码",
        value="AAPL",
        placeholder="例如 AAPL、NVDA、TSLA",
    ).strip().upper()

    generate_analysis = st.form_submit_button("生成个股分析")

if generate_analysis:
    if stock_symbol:
        st.session_state["five_part_stock_symbol"] = stock_symbol
    else:
        st.warning("请先输入股票代码。")

selected_symbol = st.session_state.get("five_part_stock_symbol")

if not selected_symbol:
    st.subheader("2. 个股表现")
    st.info("输入股票代码并点击“生成个股分析”，即可显示后续分析。")

    st.subheader("3. 判断依据")
    st.caption("将结合价格均线、相对 SPY 表现及成交量生成。")

    st.subheader("4. 触发条件")
    st.caption("将显示具体的突破参考价和转弱参考价。")

    st.subheader("5. 风险")
    st.caption("将显示波动风险、市场背景及数据限制。")

else:
    try:
        with st.spinner(f"正在分析 {selected_symbol}……"):
            stock_prices = fetch_analysis_prices(selected_symbol)

        close_series = stock_prices["Close"]
        latest = stock_prices.iloc[-1]
        previous = stock_prices.iloc[-2]

        last_close = float(latest["Close"])
        daily_return = (
            last_close / float(previous["Close"]) - 1
        ) * 100

        sma20_series = close_series.rolling(20).mean()
        sma50_series = close_series.rolling(50).mean()

        sma20 = float(sma20_series.iloc[-1])
        sma50 = float(sma50_series.iloc[-1])

        sma50_rising = (
            sma50_series.iloc[-1] > sma50_series.iloc[-6]
        )

        if last_close > sma50 and sma50_rising:
            stock_trend = "中期偏强"
        elif last_close < sma50 and not sma50_rising:
            stock_trend = "中期偏弱"
        else:
            stock_trend = "震荡 / 趋势信号不一致"

        stock_return20 = (
            last_close / float(close_series.iloc[-21]) - 1
        ) * 100

        # 前 20 日区间，不包括最新一日。
        prior20 = stock_prices.iloc[-21:-1]
        support_price = float(prior20["Low"].min())
        resistance_price = float(prior20["High"].max())

        prior_volume = prior20["Volume"].mean()
        relative_volume = None

        if pd.notna(prior_volume) and prior_volume > 0:
            relative_volume = analysis_number(
                float(latest["Volume"]) / float(prior_volume)
            )

        if relative_volume is None:
            volume_comment = "成交量不可用"
        elif relative_volume >= 1.5:
            if daily_return > 0:
                volume_comment = "上涨日放量"
            elif daily_return < 0:
                volume_comment = "下跌日放量"
            else:
                volume_comment = "平收日放量"
        elif relative_volume < 0.8:
            volume_comment = "成交量低于近期常态"
        else:
            volume_comment = "成交量接近近期常态"

        # 此处采用简单平均真实波幅，不是 Wilder ATR。
        previous_close = close_series.shift(1)
        true_range = pd.concat(
            [
                stock_prices["High"] - stock_prices["Low"],
                (stock_prices["High"] - previous_close).abs(),
                (stock_prices["Low"] - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        average_range14 = float(
            true_range.rolling(14).mean().iloc[-1]
        )
        range_percent = average_range14 / last_close * 100

        stock_date = stock_prices.index[-1].date().isoformat()

        # 相对 SPY 分析失败时，不影响其他个股分析。
        excess_return = None
        relative_date = None
        relative_comment = "SPY 比较数据不可用，暂不判断相对强弱。"

        try:
            spy_prices = fetch_analysis_prices("SPY")

            aligned = pd.concat(
                [
                    close_series.rename("Stock"),
                    spy_prices["Close"].rename("SPY"),
                ],
                axis=1,
                join="inner",
            ).dropna()

            if len(aligned) >= 21:
                aligned_stock_return = (
                    aligned["Stock"].iloc[-1]
                    / aligned["Stock"].iloc[-21]
                    - 1
                ) * 100

                aligned_spy_return = (
                    aligned["SPY"].iloc[-1]
                    / aligned["SPY"].iloc[-21]
                    - 1
                ) * 100

                excess_return = (
                    aligned_stock_return - aligned_spy_return
                )
                relative_date = (
                    aligned.index[-1].date().isoformat()
                )

                if excess_return > 0:
                    relative_comment = (
                        f"近 20 个共同交易日跑赢 SPY "
                        f"{excess_return:.2f} 个百分点。"
                    )
                elif excess_return < 0:
                    relative_comment = (
                        f"近 20 个共同交易日跑输 SPY "
                        f"{abs(excess_return):.2f} 个百分点。"
                    )
                else:
                    relative_comment = (
                        "近 20 个共同交易日与 SPY 表现持平。"
                    )

        except Exception:
            pass

        # --------------------------------------------------
        # 2. 个股表现
        # --------------------------------------------------
        st.subheader("2. 个股表现")

        st.write(
            f"**{selected_symbol}：{stock_trend}**"
            f" ｜最新可用日线：{stock_date}"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "收盘价（复权）",
            f"{last_close:.2f}",
            f"{daily_return:+.2f}%",
        )
        col2.metric(
            "近 20 个交易日收益",
            f"{stock_return20:+.2f}%",
        )
        col3.metric(
            "相对成交量",
            (
                f"{relative_volume:.2f} 倍"
                if relative_volume is not None
                else "不可用"
            ),
        )

        st.write(
            f"{relative_comment} 最新量价特征：{volume_comment}。"
        )

        if relative_date:
            st.caption(f"相对 SPY 比较截至：{relative_date}")

        # --------------------------------------------------
        # 3. 判断依据
        # --------------------------------------------------
        st.subheader("3. 判断依据")

        analysis_evidence = pd.DataFrame(
            [
                {
                    "依据": "20 日均线",
                    "当前情况": f"{sma20:.2f}",
                    "解释": (
                        "价格高于短期均线"
                        if last_close > sma20
                        else "价格不高于短期均线"
                    ),
                },
                {
                    "依据": "50 日均线",
                    "当前情况": f"{sma50:.2f}",
                    "解释": (
                        f"价格{'高于' if last_close > sma50 else '不高于'}均线；"
                        f"均线较 5 个交易日前{'上升' if sma50_rising else '未上升'}"
                    ),
                },
                {
                    "依据": "相对 SPY",
                    "当前情况": (
                        f"{excess_return:+.2f} 个百分点"
                        if excess_return is not None
                        else "不可用"
                    ),
                    "解释": "近 20 个共同交易日的收益差",
                },
                {
                    "依据": "成交量",
                    "当前情况": (
                        f"{relative_volume:.2f} 倍"
                        if relative_volume is not None
                        else "不可用"
                    ),
                    "解释": volume_comment,
                },
                {
                    "依据": "市场背景",
                    "当前情况": market_label,
                    "解释": "仅作背景，不替代个股信号",
                },
            ]
        )

        st.dataframe(
            analysis_evidence,
            hide_index=True,
            use_container_width=True,
        )

        if (
            stock_trend == "中期偏强"
            and excess_return is not None
            and excess_return > 0
        ):
            st.write(
                "**综合判断：**趋势与相对强弱方向一致，"
                "个股表现偏强；仍需通过后续价格行为确认。"
            )
        elif (
            stock_trend == "中期偏弱"
            and excess_return is not None
            and excess_return < 0
        ):
            st.write(
                "**综合判断：**趋势与相对强弱均偏弱，"
                "暂未出现明确改善证据。"
            )
        else:
            st.write(
                "**综合判断：**现有证据尚未形成一致方向，"
                "优先等待触发条件，而不是只凭单一指标下结论。"
            )

        # --------------------------------------------------
        # 4. 触发条件
        # --------------------------------------------------
        st.subheader("4. 触发条件")

        breakout_now = (
            last_close > resistance_price
            and relative_volume is not None
            and relative_volume >= 1.5
        )

        st.write(
            f"- **向上观察条件：**日线收盘高于此前 20 日"
            f"高点 **{resistance_price:.2f}**，"
            "且成交量达到此前 20 日平均量的 **1.5 倍或以上**。"
        )

        if breakout_now:
            st.success(
                "最新日线已满足上述价格和成交量观察条件。"
                "这不是买入指令；仍需观察后续能否守住突破区域。"
            )
        else:
            st.caption(
                "最新日线尚未同时满足上述价格和成交量条件。"
            )

        st.write(
            f"- **短期转弱观察：**收盘跌到 20 日均线"
            f" **{sma20:.2f}** 下方。"
        )

        st.write(
            f"- **区间转弱条件：**收盘跌破此前 20 日"
            f"低点 **{support_price:.2f}**。"
        )

        if last_close < support_price:
            st.warning("最新收盘已跌破上述区间低点。")

        st.caption(
            "这些是固定规则的观察条件，未经回测验证。"
            "20 日区间及均线会随新行情更新，不是永久固定价位。"
        )

        # --------------------------------------------------
        # 5. 风险
        # --------------------------------------------------
        st.subheader("5. 风险")

        st.write(
            f"- **波动风险：**最近 14 日平均真实波幅约为"
            f" **{average_range14:.2f}**，"
            f"占股价约 **{range_percent:.2f}%**。"
            "仅描述近期波动，不预测方向。"
        )

        if market_label == "偏谨慎":
            st.write(
                "- **市场背景风险：**当前市场环境偏谨慎，"
                "即使个股暂时强势，也可能受到整体市场回撤影响。"
            )
        elif market_label == "无法确认":
            st.write(
                "- **市场背景风险：**市场数据不完整，"
                "不能确认整体环境是否支持个股走势。"
            )
        else:
            st.write(
                "- **市场背景风险：**市场指标与个股可能出现背离，"
                "整体环境较好也不能保证个股上涨。"
            )

        st.write(
            "- **事件风险：**本模块未核实财报日期、"
            "重大公告、基本面或估值，分析前需另行检查。\n"
            "- **突破风险：**区间突破可能失败；"
            "放量不能直接解释为资金净流入。\n"
            "- **数据风险：**Yahoo Finance 行情可能延迟或缺失；"
            "个股分析与上方市场表格缓存时间不同，日期可能不一致。\n"
            "- **口径限制：**个股采用复权日线；"
            "收盘过滤主要面向美股，不是完整交易所日历。"
        )

        st.caption(
            "分析由固定规则自动生成，不调用外部 AI。"
            "仅供研究参考，不构成投资建议。"
        )

    except Exception as e:
        st.error(f"个股分析暂时无法生成：{str(e)}")


# --- 原有退出登录功能保持不变 ---
if st.button("Log Out"):
    st.session_state["password_correct"] = False
    st.rerun()
