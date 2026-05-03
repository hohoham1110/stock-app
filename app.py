import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

st.set_page_config(page_title="주식 분석기", layout="wide")
st.title("📈 주식 차트 분석기")

STOCKS_KR = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차": "005380.KS",
    "KB금융": "105560.KS",
    "셀트리온": "068270.KS",
}

STOCKS_US = {
    "애플": "AAPL",
    "테슬라": "TSLA",
    "엔비디아": "NVDA",
    "알파벳A": "GOOGL",
    "아마존": "AMZN",
    "메타": "META",
    "마이크로소프트": "MSFT",
    "샌디스크": "SNDK",
}

market = st.radio("시장 선택", ["🇰🇷 국내", "🇺🇸 해외"], horizontal=True)
STOCKS = STOCKS_KR if market == "🇰🇷 국내" else STOCKS_US

col1, col2 = st.columns(2)
with col1:
    selected = st.selectbox("종목 선택", list(STOCKS.keys()))
with col2:
    period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)

ticker = STOCKS[selected]
df = yf.download(ticker, period=period, auto_adjust=False)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
else:
    # 컬럼 평탄화
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]
    volume = df["Volume"]

    current = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    change = current - prev
    change_pct = (change / prev) * 100
    high = float(df["High"].iloc[-1])
    low = float(df["Low"].iloc[-1])

# 일별 시세 + 매매신호 나란히
    st.subheader("📅 일별 시세 & 📊 매매 신호")
    left, right = st.columns([1, 1])

    with left:
        table = df[["Close","Volume"]].copy()
        table = table.iloc[::-1]
        table.index = [str(i)[:10] for i in table.index]
        table.columns = ["종가","거래량"]

        prev_closes = list(df["Close"].iloc[::-1])
        changes = []
        for i, val in enumerate(prev_closes):
            if i == len(prev_closes)-1:
                changes.append("-")
            else:
                diff = float(prev_closes[i]) - float(prev_closes[i+1])
                pct = diff / float(prev_closes[i+1]) * 100
                changes.append(f"{pct:+.2f}%")

        table["등락률"] = changes
        table["종가"] = table["종가"].apply(lambda x: f"{float(x):,.0f}")
        table["거래량"] = table["거래량"].apply(lambda x: f"{float(x):,.0f}")
        table = table[["종가","등락률","거래량"]]

        def color_change(val):
            if val == "-": return ""
            if val.startswith("+"): return "color: red"
            if val.startswith("-"): return "color: blue"
            return ""

        styled = table.style.applymap(color_change, subset=["등락률"])
        st.dataframe(styled, use_container_width=True)

    with right:
        st.markdown("### 매매 신호")
        rsi_label = "🟢 과매도(매수)" if latest_rsi < 30 else "🔴 과매수(매도)" if latest_rsi > 70 else "⚪ 중립"
        macd_label = "🟢 매수" if latest_macd > latest_signal else "🔴 매도"
        bb_label = "🟢 매수" if current < latest_bb_low else "🔴 매도" if current > latest_bb_high else "⚪ 중립"

        st.metric("RSI", f"{latest_rsi:.1f}", rsi_label)
        st.metric("MACD", f"{latest_macd:.2f}", macd_label)
        st.metric("볼린저밴드", f"{current:,.0f}", bb_label)

        if buy_signals >= 2:
            st.success(f"✅ 매수 타이밍! (신호 {buy_signals}/3)")
        elif sell_signals >= 2:
            st.error(f"🔴 매도 타이밍! (신호 {sell_signals}/3)")
        else:
            st.info("⏳ 관망 구간")
    c1.metric("RSI", f"{latest_rsi:.1f}", "🟢 과매도(매수)" if latest_rsi < 30 else "🔴 과매수(매도)" if latest_rsi > 70 else "⚪ 중립")
    c2.metric("MACD", f"{latest_macd:.2f}", "🟢 매수" if latest_macd > latest_signal else "🔴 매도")
    c3.metric("볼린저밴드", f"{current:,.0f}", "🟢 매수" if current < latest_bb_low else "🔴 매도" if current > latest_bb_high else "⚪ 중립")

    if buy_signals >= 2:
        st.success(f"✅ 매수 타이밍! (신호 {buy_signals}/3)")
    elif sell_signals >= 2:
        st.error(f"🔴 매도 타이밍! (신호 {sell_signals}/3)")
    else:
        st.info("⏳ 관망 구간")

    # 차트
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{selected} 캔들차트", "거래량", "RSI"))

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=close,
        name="캔들", increasing_line_color="red", decreasing_line_color="blue"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_high, line=dict(color="orange", dash="dash", width=1), name="BB상단"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_low, line=dict(color="purple", dash="dash", width=1), name="BB하단"), row=1, col=1)

    colors = ["red" if float(c) >= float(o) else "blue" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=volume, marker_color=colors, name="거래량"), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="green", width=1), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=3, col=1)

    fig.update_layout(height=800, xaxis_rangeslider_visible=False, showlegend=False)
    fig.update_yaxes(title_text="가격", row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)