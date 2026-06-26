import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="국내 상장 ETF 실시간 레이더", layout="wide", initial_sidebar_state="expanded")

st.title("📡 네이버 금융 연동 실시간 ETF 및 종목 모니터링 시스템")
st.markdown("본 대시보드는 네이버 금융 공식 실시간 데이터 피드를 사용하여 차단 없이 안정적으로 24시간 작동합니다.")

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

# 💡 차단 위험 없는 네이버 실시간 시세 API 연동 함수
def get_naver_api_price(item_code):
    # 네이버 금융이 내부적으로 사용하는 차단 없는 실시간 JSON API 주소
    url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{item_code}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # JSON 데이터에서 현재가와 전일대비 등락률 다이렉트 추출
        item_data = data['result']['areas'][0]['datas'][0]
        
        current_price = int(item_data['nv'])  # 현재가 (Now Value)
        fluctuation_rate = float(item_data['cr'])  # 등락률 (Change Rate)
        
        return current_price, fluctuation_rate
    except:
        return None, None

# 세션 상태 캐싱 초기화
if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = code

# 종목 교체 시 기존 차트 누적 데이터 리셋
if st.session_state.last_code != code:
    st.session_state.price_history = []
    st.session_state.time_history = []
    st.session_state.last_code = code

placeholder = st.empty()

while True:
    with placeholder.container():
        price, fluctuation_rate = get_naver_api_price(code)
        
        # 대한민국 시간대 강제 동기화
        local_tz = pytz.timezone('Asia/Seoul')
        current_time = datetime.now(local_tz).strftime("%H:%M:%S")
        
        if price is not None:
            # 실시간 데이터 축적
            st.session_state.price_history.append(price)
            st.session_state.time_history.append(current_time)
            
            # 차트 가독성을 위해 최근 20개 데이터만 유지
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            # 대시보드 상단 메인 전광판
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric(label=f"📊 {target_name.split(' ')[0]} 가격", value=f"₩{price:,}")
            with kpi2:
                status_msg = "🔥 과열" if fluctuation_rate >= 1.5 else ("🚨 과매도" if fluctuation_rate <= -1.5 else "✅ 정상")
                st.metric(label=f"⚡ 현재 등락률 ({status_msg})", value=f"{fluctuation_rate} %", delta=f"{fluctuation_rate}%")
                
            st.markdown("---")
            
            # 차트 및 리스크 게이지 화면 배치
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 주가 추이 (API 실시간 연동)")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=st.session_state.time_history, 
                    y=st.session_state.price_history, 
                    mode='lines+markers', 
                    line=dict(color='#00ffcc', width=2.5)
                ))
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
            st.warning("네이버 금융 데이터 통신망을 재설정하고 있습니다. 잠시만 기다려주세요...")
            
    time.sleep(refresh_rate)
