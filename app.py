import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

st.set_page_config(page_title="주식 분석기", layout="wide")
st.title("📈 주식 차트 분석기")

# 종목 추천 리스트
STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "LG에너지솔루션": "373220.KS",
    "애플": "AAPL",
    "테슬라": "TSLA",
    "엔비디아": "NVDA",
}

col1, col2 = st.columns(2)
with col1:
    selected = st.selectbox("종목 선택", list(STOCKS.keys()))
with col2:
    period = st.selectbox("기간", ["3mo", "6mo", "1y", "2y"], index=2)

ticker = STOCKS[selected]
df = yf.download(ticker, period=period)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
else:
    close = df["Close"].squeeze()

    # 지표 계산
    rsi = RSIIndicator(close).rsi()
    macd_obj = MACD(close)
    macd = macd_obj.macd()
    macd_signal = macd_obj.macd_signal()
    bb = BollingerBands(close)
    bb_high = bb.bollinger_hband()
    bb_low = bb.bollinger_lband()

    # 매수/매도 신호
    latest_rsi = rsi.iloc[-1]
    latest_macd = macd.iloc[-1]
    latest_signal = macd_signal.iloc[-1]
    latest_close = close.iloc[-1]
    latest_bb_low = bb_low.iloc[-1]
    latest_bb_high = bb_high.iloc[-1]

    buy_signals = 0
    sell_signals = 0
    if latest_rsi < 30: buy_signals += 1
    if latest_rsi > 70: sell_signals += 1
    if latest_macd > latest_signal: buy_signals += 1
    if latest_macd < latest_signal: sell_signals += 1
    if latest_close < latest_bb_low: buy_signals += 1
    if latest_close > latest_bb_high: sell_signals += 1

    # 신호 표시
    st.subheader("📊 매매 신호")
    c1, c2, c3 = st.columns(3)
    c1.metric("RSI", f"{latest_rsi:.1f}", "과매도(매수)" if latest_rsi < 30 else "과매수(매도)" if latest_rsi > 70 else "중립")
    c2.metric("MACD", f"{latest_macd:.2f}", "매수" if latest_macd > latest_signal else "매도")
    c3.metric("볼린저밴드", f"{latest_close:.0f}", "매수" if latest_close < latest_bb_low else "매도" if latest_close > latest_bb_high else "중립")

    if buy_signals >= 2:
        st.success(f"✅ 매수 타이밍 (신호 {buy_signals}/3)")
    elif sell_signals >= 2:
        st.error(f"🔴 매도 타이밍 (신호 {sell_signals}/3)")
    else:
        st.info("⏳ 관망 구간")

    # 차트
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"].squeeze(), high=df["High"].squeeze(), low=df["Low"].squeeze(), close=close, name="캔들"))
    fig.add_trace(go.Scatter(x=df.index, y=bb_high, line=dict(color="red", dash="dash"), name="BB상단"))
    fig.add_trace(go.Scatter(x=df.index, y=bb_low, line=dict(color="blue", dash="dash"), name="BB하단"))
    fig.update_layout(title=f"{selected} 차트", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)