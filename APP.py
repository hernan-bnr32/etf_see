import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="글로벌 매크로 & ETF 실시간 종합 관제 레이더", layout="wide", initial_sidebar_state="expanded")

# 💡 세션 상태를 활용해 데이터 피드 캐싱 (네트워크 단절 대비 백업용)
if "macro_cache" not in st.session_state:
    st.session_state.macro_cache = {
        "kospi": {"price": 2700.0, "rate": 0.0},
        "usd_krw": {"price": 1380.0, "rate": 0.0},
        "wti": {"price": 80.0, "rate": 0.0},
        "taco": {"price": 5000.0, "rate": 0.0}
    }
if "stock_cache" not in st.session_state:
    st.session_state.stock_cache = {}

# 💡 안전한 네이버 실시간 API 수집 함수
def get_naver_multi_prices_safe(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=3)
        data = response.json()
        for item in data['result']['areas'][0]['datas']:
            c = item['cd']
            price = float(item['nv']) if item.get('nv') is not None else 0.0
            rate = float(item['cr']) if item.get('cr') is not None else 0.0
            nav = float(item['nav']) if 'nav' in item and item['nav'] is not None else None
            
            # 정상 데이터인 경우 캐시 업데이트
            if price > 0:
                st.session_state.stock_cache[c] = {"price": price, "rate": rate, "nav": nav}
    except Exception as e:
        pass # 실패 시 기존 캐시 데이터 사용
    
    return st.session_state.stock_cache

# 💡 안전한 거시경제 지표 수집 함수
def get_macro_indicators_safe():
    url = "https://polling.finance.naver.com/api/realtime?query=SERVICE_MARKETINDEX:FX_USDKRW,SERVICE_MARKETINDEX:OIL_GSL,SERVICE_MARKETINDEX:SPI@KOSPI"
    url_global = "https://polling.finance.naver.com/api/realtime?query=SERVICE_WORLDINDEX:NAS@SOX,SERVICE_MARKETINDEX:OIL_CL"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=3)
        data = res.json()
        for item in data['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv']) if item.get('nv') is not None else 0.0
            cr = float(item['cr']) if item.get('cr') is not None else 0.0
            
            if nv > 0:
                if cd == "FX_USDKRW": st.session_state.macro_cache["usd_krw"] = {"price": nv, "rate": cr}
                elif cd == "OIL_GSL": st.session_state.macro_cache["wti"] = {"price": nv, "rate": cr}
                elif cd == "SPI@KOSPI": st.session_state.macro_cache["kospi"] = {"price": nv, "rate": cr}
                
        res_g = requests.get(url_global, headers=headers, timeout=3)
        data_g = res_g.json()
        for item in data_g['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv']) if item.get('nv') is not None else 0.0
            cr = float(item['cr']) if item.get('cr') is not None else 0.0
            
            if nv > 0:
                if cd == "NAS@SOX": st.session_state.macro_cache["taco"] = {"price": nv, "rate": cr}
                elif cd == "OIL_CL": st.session_state.macro_cache["wti"] = {"price": nv, "rate": cr}
    except Exception as e:
        pass # 에러 발생 시 0.0으로 밀지 않고 기존 캐시값 방어
        
    return st.session_state.macro_cache

# --- 데이터 로드 ---
macro = get_macro_indicators_safe()

# --- 대시보드 상단 글로벌 매크로 판넬 ---
st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(label="📉 KOSPI 코스피 지수", value=f"{macro['kospi']['price']:,} pt", delta=f"{macro['kospi']['rate']}%")
with m_col2:
    st.metric(label="💵 원/달러 환율", value=f"₩{macro['usd_krw']['price']:,}", delta=f"{macro['usd_krw']['rate']}%")
with m_col3:
    st.metric(label="🛢️ WTI 국제유가 (선물)", value=f"${macro['wti']['price']:,}", delta=f"{macro['wti']['rate']}%")
with m_col4:
    st.metric(label="🌮 TACO (Phila 반도체 지수)", value=f"{macro['taco']['price']:,} pt", delta=f"{macro['taco']['rate']}%")

st.markdown("---")

# --- 하단 개별 종목 실시간 레이더 ---
st.title("📡 선택 종목 실시간 괴리율 & 변동성 종합 레이더")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider("새로고침 주기 (초)", min_value=2, max_value=10, value=3) # 기본값 3초로 안정화
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
        local_tz = pytz.timezone('Asia/Seoul')
        current_time_str = datetime.now(local_tz).strftime("%H:%M:%S")
        ts_key = str(int(time.time() * 1000))  # 고유 엘리먼트 키 생성용
        
        if code in single_stock and single_stock[code]["price"] > 0:
            price = int(single_stock[code]["price"])
            fluctuation_rate = single_stock[code]["rate"]
            nav = single_stock[code]["nav"]
            
            is_etf = nav is not None and nav > 0
            disparity_rate = round(((price - nav) / nav) * 100, 2) if is_etf else 0.0
            
            # 차트용 데이터 누적
            if not st.session_state.price_history or st.session_state.price_history[-1] != price or len(st.session_state.price_history) < 2:
                st.session_state.price_history.append(price)
                st.session_state.time_history.append(current_time_str)
            
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            # 메인 종합 전광판
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.metric(label="📊 현재 가격", value=f"₩{price:,}", delta=f"{fluctuation_rate}%")
            with kpi2:
                nav_value = f"₩{int(nav):,}" if is_etf else "N/A (일반주식)"
                st.metric(label="🎯 실시간 NAV (순자산가치)", value=nav_value)
            with kpi3:
                if is_etf:
                    status_disparity = "🚨 고평가" if disparity_rate >= 0.5 else ("🔵 저평가" if disparity_rate <= -0.5 else "✅ 정상")
                    st.metric(label=f"🔍 실시간 괴리율 ({status_disparity})", value=f"{disparity_rate} %", delta=f"{disparity_rate}%", delta_color="inverse")
                else:
                    st.metric(label="🔍 실시간 괴리율", value="N/A")
                
            st.markdown("---")
            
            # 레이아웃 배치
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 주가 추이 (정밀 누적)")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=st.session_state.time_history, y=st.session_state.price_history, mode='lines+markers', line=dict(color='#00ffcc', width=2.5)))
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=380, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{ts_key}")
                
            with col2:
                st.markdown("### 📊 리스크 종합 분석 패널")
                g_col1, g_col2 = st.columns(2)
                
                with g_col1:
                    st.markdown("##### 🎯 실시간 괴리율 미터")
                    if is_etf:
                        fig_gauge1 = go.Figure(go.Indicator(
                            mode = "gauge+number",
                            value = disparity_rate,
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            gauge = {
                                'axis': {'range': [-2, 2]},
                                'bar': {'color': "white"},
                                'steps': [
                                    {'range': [-2, -0.5], 'color': "navy"},
                                    {'range': [-0.5, 0.5], 'color': "forestgreen"},
                                    {'range': [0.5, 2], 'color': "crimson"}
                                ],
                            }
                        ))
                        fig_gauge1.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark")
                        st.plotly_chart(fig_gauge1, use_container_width=True, key=f"g_disp_{ts_key}")
                    else:
                        st.info("ETF 전용 지표\n(일반 주식은 NAV가 없습니다)")
                
                with g_col2:
                    st.markdown("##### 🛑 변동성 리스크 게이지")
                    fig_gauge2 = go.Figure(go.Indicator(
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
                    fig_gauge2.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark")
                    st.plotly_chart(fig_gauge2, use_container_width=True, key=f"g_fluc_{ts_key}")
                
            st.caption(f"동기화 시간: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} | 데이터 백업 프로토콜 가동 중")
        else:
            st.warning("증권사 응답 대기 중 또는 장마감(휴일) 상태입니다. 잠시 후 자동으로 데이터를 복구합니다.")
            time.sleep(5) # API가 막혔을 때는 재시도 간격을 늘려 IP 차단 해제 유도
            
    time.sleep(refresh_rate)
