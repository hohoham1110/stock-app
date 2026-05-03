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

# 오늘 데이터 별도 갱신
try:
    today = yf.download(ticker, period="1d", interval="1m", auto_adjust=False)
    if not today.empty:
        today.columns = today.columns.get_level_values(0)
        df_today = today.resample("D").agg({
            "Open": "first", "High": "max",
            "Low": "min", "Close": "last", "Volume": "sum"
        })
        df.columns = df.columns.get_level_values(0)
        df = pd.concat([df[:-1], df_today])
except:
    df.columns = df.columns.get_level_values(0)

if df.empty:
    st.error("데이터를 불러올 수 없습니다.")
else:
    close = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    # 현재가 정보
    current = close.iloc[-1]
    prev = close.iloc[-2]
    change = current - prev
    change_pct = (change / prev) * 100
    high = df["High"].squeeze().iloc[-1]
    low = df["Low"].squeeze().iloc[-1]

    # 현재가 표시
    st.subheader("💰 현재가 정보")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재가", f"{current:,.0f}원", f"{change:+,.0f} ({change_pct:+.2f}%)")
    c2.metric("전일 종가", f"{prev:,.0f}원")
    c3.metric("당일 고가/저가", f"{high:,.0f} / {low:,.0f}원")
    c4.metric("거래량", f"{volume.iloc[-1]:,.0f}")

    # 일별 데이터 테이블
    st.subheader("📅 일별 시세")
    table = df[["Open","High","Low","Close","Volume"]].copy()
    table.columns = ["시가","고가","저가","종가","거래량"]
    table = table.sort_index(ascending=False).reset_index()
    table.rename(columns={"index": "날짜", "Date": "날짜"}, inplace=True)
    for col in ["시가","고가","저가","종가"]:
        table[col] = table[col].apply(lambda x: f"{x:,.0f}")
    table["거래량"] = table["거래량"].apply(lambda x: f"{x:,.0f}")
    table.index = table.index.strftime("%Y-%m-%d")
    st.dataframe(table, use_container_width=True)

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
    latest_bb_low = bb_low.iloc[-1]
    latest_bb_high = bb_high.iloc[-1]

    buy_signals = 0
    sell_signals = 0
    if latest_rsi < 30: buy_signals += 1
    if latest_rsi > 70: sell_signals += 1
    if latest_macd > latest_signal: buy_signals += 1
    if latest_macd < latest_signal: sell_signals += 1
    if current < latest_bb_low: buy_signals += 1
    if current > latest_bb_high: sell_signals += 1

    st.subheader("📊 매매 신호")
    c1, c2, c3 = st.columns(3)
    c1.metric("RSI", f"{latest_rsi:.1f}", "🟢 과매도(매수)" if latest_rsi < 30 else "🔴 과매수(매도)" if latest_rsi > 70 else "⚪ 중립")
    c2.metric("MACD", f"{latest_macd:.2f}", "🟢 매수" if latest_macd > latest_signal else "🔴 매도")
    c3.metric("볼린저밴드", f"{current:,.0f}", "🟢 매수" if current < latest_bb_low else "🔴 매도" if current > latest_bb_high else "⚪ 중립")

    if buy_signals >= 2:
        st.success(f"✅ 매수 타이밍! (신호 {buy_signals}/3)")
    elif sell_signals >= 2:
        st.error(f"🔴 매도 타이밍! (신호 {sell_signals}/3)")
    else:
        st.info("⏳ 관망 구간")

    # 차트 (캔들 + 거래량 + RSI)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{selected} 캔들차트", "거래량", "RSI"))

    # 캔들
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"].squeeze(),
        high=df["High"].squeeze(), low=df["Low"].squeeze(), close=close,
        name="캔들", increasing_line_color="red", decreasing_line_color="blue"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_high, line=dict(color="orange", dash="dash", width=1), name="BB상단"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_low, line=dict(color="purple", dash="dash", width=1), name="BB하단"), row=1, col=1)

    # 거래량
    colors = ["red" if c >= o else "blue" for c, o in zip(df["Close"].squeeze(), df["Open"].squeeze())]
    fig.add_trace(go.Bar(x=df.index, y=volume, marker_color=colors, name="거래량"), row=2, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color="green", width=1), name="RSI"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="blue", row=3, col=1)

    fig.update_layout(height=800, xaxis_rangeslider_visible=False, showlegend=False)
    fig.update_yaxes(title_text="가격(원)", row=1, col=1)
    fig.update_yaxes(title_text="거래량", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)

    st.plotly_chart(fig, use_container_width=True)