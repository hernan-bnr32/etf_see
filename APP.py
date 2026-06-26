import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="글로벌 매크로 레이더", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. 세션 상태 캐시 초기화
if "macro_cache" not in st.session_state:
    st.session_state.macro_cache = {
        "kospi": {"price": 2700.0, "rate": 0.0},
        "usd_krw": {"price": 1350.0, "rate": 0.0},
        "wti": {"price": 80.0, "rate": 0.0},
        "taco": {"price": 5000.0, "rate": 0.0}
    }
if "stock_cache" not in st.session_state:
    st.session_state.stock_cache = {}

# 3. 네이버 실시간 개별 종목 API 수집 함수
def get_naver_multi_prices_safe(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
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

# 4. 국내 지수 실시간 크롤링 (문자열 파싱 쪼개기 안전 조치)
def fetch_naver_index_safe():
    headers = {'User-Agent': 'Mozilla/5.0'}
    # 코스피 파싱
    try:
        url_kp = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
        res_kp = requests.get(url_kp, headers=headers, timeout=2)
        if res_kp.status_code == 200:
            txt = res_kp.text
            p_now = txt.split('id="now_value">')[1].split('<')[0]
            p_now = p_now.replace(",", "")
            p_rt = txt.split('id="change_value_and_rate">')[1].split('%')[0]
            p_rt = p_rt.split()[-1].replace("+", "")
            st.session_state.macro_cache["kospi"] = {"price": float(p_now), "rate": float(p_rt)}
    except:
        pass

    # 환율 파싱
    try:
        url_fx = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
        res_fx = requests.get(url_fx, headers=headers, timeout=2)
        if res_fx.status_code == 200:
            txt = res_fx.text
            f_now = txt.split('class="value">')[1].split('<')[0]
            f_now = f_now.replace(",", "")
            f_rt = txt.split('class="change">')[1].split('<')[0]
            f_rt = f_rt.strip().replace(",", "").replace("원", "")
            f_price = float(f_now)
            f_change = float(f_rt)
            f_prev = f_price - f_change if "-" not in txt else f_price + f_change
            f_rate_pct = round((f_change / f_prev) * 100, 2)
            if "🔴" in txt or "상승" in txt:
                f_rate_pct = +f_rate_pct
            else:
                f_rate_pct = -f_rate_pct
            st.session_state.macro_cache["usd_krw"] = {"price": f_price, "rate": f_rate_pct}
    except:
        pass

# 5. 해외 매크로 지수 수집 함수 (야후 파이낸스)
def fetch_yahoo_macro_safe():
    try:
        tickers = {"wti": "CL=F", "taco": "^SOX"}
        for key, symbol in tickers.items():
            ticker = yf.Ticker(symbol)
            todays_data = ticker.history(period='1d')
            if not todays_data.empty:
                current_price = todays_data['Close'].iloc[-1]
                prev_price = todays_data['Open'].iloc[-1] if 'Open' in todays_data else current_price
                change_rate = round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price != 0 else 0.0
                st.session_state.macro_cache[key] = {"price": round(current_price, 2), "rate": change_rate}
    except:
        pass

# 초기 1회 실행
fetch_naver_index_safe()
fetch_yahoo_macro_safe()

# 6. 사이드바 구성 (설정 정보가 루프 내에서 끊기지 않도록 분리)
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

# 메인 디스플레이 박스 선언
placeholder = st.empty()

# 7. 실시간 메인 관제 루프 실행
while True:
    fetch_naver_index_safe()
    fetch_yahoo_macro_safe()
    single_stock = get_naver_multi_prices_safe([code])
    macro = st.session_state.macro_cache
    
    local_tz = pytz.timezone('Asia/Seoul')
    current_time_str = datetime.now(local_tz).strftime("%H:%M:%S")
    
    # 중복 엘리먼트 ID 에러 방지용 가변 토큰 키 생성
    loop_key = str(int(time.time() * 1000))
    
    with placeholder.container():
        st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            st.metric(label="⚡ KOSPI 지수 (실시간)", value=f"{macro['kospi']['price']:,} pt", delta=f"{macro['kospi']['rate']}%")
        with m_col2:
            st.metric(label="💵 원/달러 환율 (실시간)", value=f"₩{macro['usd_krw']['price']:,}", delta=f"{macro['usd_krw']['rate']}%")
        with m_col3:
            st.metric(label="🛢️ WTI 국제유가 [15분지연]", value=f"${macro['wti']['price']:,}", delta=f"{macro['wti']['rate']}%")
        with m_col4:
            st.metric(label="🌮 필라델피아 반도체 [15분지연]", value=f"{macro['taco']['price']:,} pt", delta=f"{macro['taco']['rate']}%")

        st.markdown("---")
        st.title("📡 선택 종목 실시간 괴리율 & 변동성 종합 레이더")

        if code in single_stock and single_stock[code]["price"] > 0:
            price = int(single_stock[code]["price"])
            fluctuation_rate = single_stock[code]["rate"]
            nav = single_stock[code]["nav"]
            
            is_etf = nav is not None and nav > 0
            disparity_rate = round(((price - nav)
