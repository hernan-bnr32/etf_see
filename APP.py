import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="글로벌 매크로 & ETF 실시간 레이더", layout="wide", initial_sidebar_state="expanded")

# 💡 네이버 실시간 API 수집 함수
def get_naver_multi_prices(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    results = {}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        for item in data['result']['areas'][0]['datas']:
            c = item['cd']
            price = float(item['nv'])
            rate = float(item['cr'])
            results[c] = {"price": price, "rate": rate}
        return results
    except:
        return {}

# 💡 거시경제 지표 수집 함수
def get_macro_indicators():
    url = "https://polling.finance.naver.com/api/realtime?query=SERVICE_MARKETINDEX:FX_USDKRW,SERVICE_MARKETINDEX:OIL_GSL,SERVICE_MARKETINDEX:SPI@KOSPI"
    url_global = "https://polling.finance.naver.com/api/realtime?query=SERVICE_WORLDINDEX:NAS@SOX,SERVICE_MARKETINDEX:OIL_CL"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    macro_data = {
        "usd_krw": {"price": 0.0, "rate": 0.0},
        "wti": {"price": 0.0, "rate": 0.0},
        "kospi": {"price": 0.0, "rate": 0.0},
        "taco": {"price": 0.0, "rate": 0.0}
    }
    
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        for item in data['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv'])
            cr = float(item['cr']) if 'cr' in item and item['cr'] is not None else 0.0
            
            if cd == "FX_USDKRW":
                macro_data["usd_krw"] = {"price": nv, "rate": cr}
            elif cd == "OIL_GSL":
                macro_data["wti"] = {"price": nv, "rate": cr}
            elif cd == "SPI@KOSPI":
                macro_data["kospi"] = {"price": nv, "rate": cr}
                
        res_g = requests.get(url_global, headers=headers)
        data_g = res_g.json()
        for item in data_g['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv'])
            cr = float(item['cr']) if 'cr' in item and item['cr'] is not None else 0.0
            
            if cd == "NAS@SOX":
                macro_data["taco"] = {"price": nv, "rate": cr}
            elif cd == "OIL_CL":
                macro_data["wti"] = {"price": nv, "rate": cr}
                
        return macro_data
    except:
        return macro_data

# --- 대시보드 상단 글로벌 매크로 판넬 ---
st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
macro = get_macro_indicators()

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(label="📉 KOSPI 코스피 지수", value=f"{macro['kospi']['price']:,} pt", delta=f"{macro['kospi']['rate']}%")

# 💡 피드백 주신 원/달러 환율 메트릭 수정 (딕셔너리 키 및 괄호 완벽 매칭)
with m_col2:
    st.metric(label="💵 원/달러 환율", value=f"₩{macro['usd_krw']['price']:,}", delta=f"{macro['usd_krw']['rate']}%")

with m_col3:
    st.metric(label="🛢️ WTI 국제유가 (선물)", value=f"${macro['wti']['price']:,}", delta=f"{macro['wti']['rate']}%")

with m_col4:
    st.metric(label="🌮 TACO (Phila 반도체 지수)", value=f"{macro['taco']['price']:,} pt", delta=f"{macro['taco']['rate']}%")

st.markdown("---")

# --- 하단 개별 종목 실시간 레이더 ---
st.title("📡 선택 종목 실시간 집중 감시 레이더")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider("새로고침 주기 (초)", min_value=2, max_value=10, value=2)
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

# 종목 코드 추출
code = target_name.split("(")[-1].replace(")", "").strip()

# 세션 상태 캐싱 초기화
if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = code

# 종목 교체 시 리셋
if st.session_state.last_code != code:
    st.session_state.price_history = []
    st.session_state.time_history = []
    st.session_state.last_code = code

placeholder = st.empty()

while True:
    with placeholder.container():
        single_stock = get_naver_multi_prices([code])
        local_tz = pytz.timezone('Asia/Seoul')
        current_time = datetime.now(local_tz).strftime("%H:%M:%S")
        
        if code in single_stock:
            price = int(single_stock[code]["price"])
            fluctuation_rate = single_stock[code]["rate"]
            
            st.session_state.price_history.append(price)
            st.session_state.time_history.append(current_time)
            
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric(label="📊 현재 가격", value=f"₩{price:,}")
            with kpi2:
                status_msg = "🔥 과열" if fluctuation_rate >= 1.5 else ("🚨 과매도" if fluctuation_rate <= -1.5 else "✅ 정상")
                st.metric(label=f"⚡ 현재 등락률 ({status_msg})", value=f"{fluctuation_rate} %", delta=f"{fluctuation_rate}%")
                
            st.markdown("---")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 주가 추이 (2초 단위 누적)")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=st.session_state.time_history, y=st.session_state.price_history, mode='lines+markers', line=dict(color='#00ffcc', width=2.5)))
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown("### 🛑 변동성 리스크 게이지")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = fluctuation_rate,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [-5, 5]},
                        'bar': {'color': "white"},
                        'steps': [
                            {'range': [-5, -1.5], 'color': "crimson"},
                            {'range': [-1.5, 1.5], 'color': "forestgreen"},
                            {'range': [1.5, 5], 'color': "darkorange"}
                        ],
                    }
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), template="plotly_dark")
                st.plotly_chart(fig_gauge, use_container_width=True)
                
            st.caption(f"KST 실시간 동기화 완료: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} | 인프라 정상")
        else:
            st.warning("데이터 피드 동기화 중입니다...")
            
    time.sleep(refresh_rate)
