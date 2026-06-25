import os
import sys

# 1. 필요한 모든 패키지가 있는지 검사하고, 하나라도 없으면 즉시 강제 설치 후 시스템을 리로드합니다.
required_modules = ["yfinance", "pandas", "plotly", "streamlit"]
missing_modules = []

for module in required_modules:
    try:
        if module == "plotly":
            import plotly
        elif module == "yfinance":
            import yfinance
        elif module == "pandas":
            import pandas
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    # 누락된 부품들을 시장(pip)에서 한꺼번에 다운로드하여 설치합니다.
    os.system(f"pip install {' '.join(missing_modules)}")
    # 설치 완료 후 파이썬 프로그램이 새 부품을 완벽히 인식하도록 강제 새로고침(재실행)합니다.
    os.execv(sys.executable, ['python'] + sys.argv)

# 2. 이제 안전하게 라이브러리들을 불러옵니다.
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# 3. 페이지 기본 설정 및 다크모드 풍 스타일링
st.set_page_config(page_title="실시간 ETF 괴리율 레이더", layout="wide", initial_sidebar_state="expanded")

st.title("📡 실시간 ETF 괴리율 & 웩더독 모니터링 시스템")
st.markdown("본 대시보드는 자동 새로고침되며, ETF 가격과 실제 자산가치 간의 괴리를 실시간 추적합니다.")

# 4. 사이드바 - 새로고침 주기 및 감시 종목 설정
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider("새로고침 주기 (초)", min_value=2, max_value=10, value=2)
    
    st.markdown("---")
    st.markdown("### 🎯 모니터링 타깃")
    target_etf = st.selectbox("감시할 ETF 선택", ["KORU (MSCI Korea 3X)", "EWY (MSCI Korea South)"])
    
    st.info("💡 괴리율이 -0.5% 이하로 떨어지면 기계적 투매(웩더독) 신호로 판정합니다.")

# Ticker 매핑
ticker_map = {
    "KORU (MSCI Korea 3X)": {"etf": "KORU", "nav_proxy": "^KS11"},
    "EWY (MSCI Korea South)": {"etf": "EWY", "nav_proxy": "^KS11"}
}

etf_ticker = ticker_map[target_etf]["etf"]
nav_ticker = ticker_map[target_etf]["nav_proxy"]

# 5. 데이터 실시간 스트리밍 시뮬레이션 및 로직
placeholder = st.empty()

while True:
    with placeholder.container():
        try:
            # 실시간 데이터 가져오기
            etf_data = yf.Ticker(etf_ticker).history(period="1d", interval="1m").iloc[-1]
            nav_data = yf.Ticker(nav_ticker).history(period="1d", interval="1m").iloc[-1]
            
            etf_price = round(etf_data["Close"], 2)
            base_nav = round(nav_data["Close"], 2)
            
            # 괴리율 연산 시뮬레이션
            ratio = etf_price / (base_nav / 50)
            disparity = round((ratio - 1) * 100, 2)
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 6. 상단 핵심 KPI 전광판 배치
            kpi1, kpi2, kpi3 = st.columns(3)
            
            with kpi1:
                st.metric(label=f"📊 {etf_ticker} 시장 가격", value=f"${etf_price}")
            with kpi2:
                st.metric(label="💎 실시간 추정 가치 (iNAV Proxy)", value=f"{base_nav} pt")
            with kpi3:
                if disparity <= -0.5:
                    status_msg = "🚨 LP 방어벽 붕괴 (헐값 투매!)"
                    delta_color = "inverse"
                elif disparity >= 0.5:
                    status_msg = "🔥 플러스 오버슈팅 (추격 금지)"
                    delta_color = "normal"
                else:
                    status_msg = "✅ 기계 정상 작동 중"
                    delta_color = "off"
                    
                st.metric(label=f"⚡ 현재 괴리율 ({status_msg})", value=f"{disparity} %", delta=f"{disparity}%", delta_color=delta_color)

            st.markdown("---")
            
            # 7. 차트 시각화
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### 📈 장중 실시간 트랙킹 추이")
                hist_etf = yf.Ticker(etf_ticker).history(period="1d", interval="1m").tail(15)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist_etf.index, y=hist_etf['Close'], name=etf_ticker, line=dict(color='#1f77b4', width=2)))
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown("### 🛑 실시간 리스크 게이지")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = disparity,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [-3, 3]},
                        'bar': {'color': "white"},
                        'steps': [
                            {'range': [-3, -0.5], 'color': "crimson"},
                            {'range': [-0.5, 0.5], 'color': "forestgreen"},
                            {'range': [0.5, 3], 'color': "darkorange"}
                        ],
                    }
                ))
                fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20), template="plotly_dark")
                st.plotly_chart(fig_gauge, use_container_width=True)
                
            st.caption(f"최종 업데이트 동기화 시간: {current_time} | 레이더 가동 중...")
            
        except Exception as e:
            st.warning("데이터 연결 재시도 중... 대기 중입니다.")
            
    time.sleep(refresh_rate)
