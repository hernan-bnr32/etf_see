import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(
    page_title="글로벌 매크로 & ETF 실시간 종합 관제 레이더", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 💡 세션 상태 캐싱 (네트워크 단절 대비 백업용)
if "macro_cache" not in st.session_state:
    st.session_state.macro_cache = {
        "kospi": {"price": 2700.0, "rate": 0.0},
        "usd_krw": {"price": 1380.0, "rate": 0.0},
        "wti": {"price": 80.0, "rate": 0.0},
        "taco": {"price": 5000.0, "rate": 0.0}
    }
if "stock_cache" not in st.session_state:
    st.session_state.stock_cache = {}

# 💡 네이버 실시간 개별 종목 API 수집 함수
def get_naver_multi_prices_safe(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=3)
        data = response.json()
        for item in data['result']['areas'][0]['datas']:
            c = item['cd']
            price = float(item['nv']) if item.get('nv') is not None else 0.0
            rate = float(item['cr']) if item.get('cr') is not None else 0.0
            nav = float(item['nav']) if 'nav' in item and item['nav'] is not None else None
            if price > 0:
                st.session_state.stock_cache[c] = {"price": price, "rate": rate, "nav": nav}
    except:
        pass
    return st.session_state.stock_cache

# 💡 국내 지수는 실시간 크롤링 / 해외 지수는 야후 파이낸스 결합 (에러 방지형 줄바꿈 제거)
def get_hybrid_macro_indicators():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. 국내 지수 (코스피, 환율) 실시간 크롤링
    try:
        kospi_url = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
        res_kp = requests.get(kospi_url, headers=headers, timeout=2)
        if res_kp.status_code == 200:
            p_now = res_kp.text.split('id="now_value">')[1].split('<')[0].replace(",", "")
            p_rate = res_kp.text.split('id="change_value_and_rate">')[1].split('%')[0].split()[-1].replace("+", "")
            st.session_state.macro_cache["kospi"] = {"price": float(p_now), "rate": float(p_rate)}
            
        fx_url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
        res_fx = requests.get(fx_url, headers=headers, timeout=2)
        if res_fx.status_code == 200:
            f_now = res_fx.text.split('class="value">')[1].split('<')[0].replace(",", "")
            f_rate = res_fx.text.split('class="change">')[1].split('<')[0].strip().replace(",", "").replace("원", "")
            f_price = float(f_now)
            f_change = float(f_rate)
            f_prev = f_price - f_change if "-" not in res_fx.text else f_price + f_change
            f_rate_pct = round((f_change / f_prev) * 100, 2)
            if "🔴" in res_fx.text or "상승" in res_fx.text:
                f_rate_pct = +f_rate_pct
            else:
                f_rate_pct = -f_rate_pct
            st.session_state.macro_cache["usd_krw"] = {"price": f_price, "rate": f_rate_pct}
    except:
        pass
        
    # 2. 해외 지수 (WTI 유가, 필라델피아 반도체) 야후 파이낸스 엔진 활용
    try:
        tickers = {"wti": "CL=F", "taco": "^SOX"}
        for key, ticker_symbol in tickers.items():
            ticker = yf.Ticker(ticker_symbol)
            todays_data = ticker.history(period='1d')
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
                prev_price = todays_data['Open'].iloc[-1] if 'Open' in todays_data else current_price
                change_rate = round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price != 0 else 0.0
                st.session_state.macro_cache[key] = {"price": round(current_price, 2), "rate": change_rate}
    except:
        pass
        
    return st.session_state.macro_cache

# --- 데이터 초기 로드 ---
macro = get_hybrid_macro_indicators()

# --- 대시보드 상단 글로벌 매크로 판넬 ---
st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(label="⚡ KOSPI 코스피 지수 (실시간)", value=f"{macro['kospi']['price']:,} pt", delta=f"{macro['kospi']['rate']}%")
with m_col2:
    st.metric(label="💵 원/달러 환율 (실시간)", value=f"₩{macro['usd_krw']['price']:,}", delta=f"{macro['usd_krw']['rate']}%")
with m_col3:
    st.metric(label="🛢️ WTI 국제유가 (26년 8월물 선물) [15분지연]", value=f"${macro['wti']['price']:,}", delta=f"{macro['wti']['rate']}%")
with m_col4:
    st.metric(label="🌮 TACO (Phila 반도체 지수) [15분지연]", value=f"{macro['taco']['price']:,} pt", delta=f"{macro['taco']['rate']}%")

st.markdown("---")

# --- 하단 개별 종목 실시간 레이더 ---
st.title("📡 선택 종목 실시간 괴리율 & 변동성 종합 레이더")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider("새로고침 주기 (초)", min_value=2, max_value=10, value=3)
    st.markdown("---")
    st.markdown("### 🎯 모니터링 타깃")
    target_name = st.selectbox(
        "감시할 종목/ETF 선택", 
        [
            "KODEX 200 (069500)",
            "삼성전자 (005930)",
            "TIGER 반도체TOP10 (396500)",
            "PLUS 글로벌HBM반도체 (442580)",
            "KODEX 미국반도체 (390390)",
            "IBK K-AI반도체코어테크 (0005G0)"
        ]
    )

code = target_name.split("(")[-1].replace(")", "").strip()

if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = code

if st.session_state.last_code != code:
    st.session_state.price_history = []
    st.session_state.time_history = []
    st.session_state.last_code = code

placeholder = st.empty()

while True:
    with placeholder.container():
        single_stock = get_naver_multi_prices_safe([code])
        macro = get_hybrid_macro_indicators()
        
        local_tz = pytz.timezone('Asia/Seoul')
        current_time_str = datetime.now(local_tz).strftime("%H:%M:%S")
        ts_key = str(int(time.time() * 1000))
        
        if code in single_stock and single_stock[code]["price"] >
