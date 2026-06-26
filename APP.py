import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time
import re
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="실시간 ETF 괴리율 레이더", layout="wide", initial_sidebar_state="expanded")

st.title("📡 실시간 ETF 괴리율 & 웩더독 모니터링 시스템")
st.markdown("본 대시보드는 자동 새로고침되며, 국내외 ETF 및 주요 종목의 실시간 추이를 추적합니다.")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider("새로고침 주기 (초)", min_value=2, max_value=10, value=2)
    
    st.markdown("---")
    st.markdown("### 🎯 모니터링 타깃")
    
    target_etf = st.selectbox(
        "감시할 종목/ETF 선택", 
        [
            "KODEX 200 (069500)",
            "삼성전자 (005930)",
            "TIGER 반도체TOP10 (396500)",
            "PLUS 글로벌HBM반도체 (442580)",
            "KODEX 미국반도체 (390390)",
            "IBK K-AI반도체코어테크 (0005G0)",
            "KORU (MSCI Korea 3X)", 
            "EWY (MSCI Korea South)"
        ]
    )
    
    st.info("💡 괴리율(또는 지수 대비 등락) 격차가 벌어지면 기계적 프로그램 매매(웩더독) 신호로 판정합니다.")

# 💡 안전한 Ticker 매핑 데이터
ticker_map = {
    "KODEX 200 (069500)": {"etf": "069500.KS", "nav_proxy": "^KS11"},
    "삼성전자 (005930)": {"etf": "005930.KS", "nav_proxy": "^KS11"},
    "TIGER 반도체TOP10 (396500)": {"etf": "396500.KS", "nav_proxy": "^KRXSEM"},
    "PLUS 글로벌HBM반도체 (442580)": {"etf": "442580.KS", "nav_proxy": "^KRXSEM"},
    "KODEX 미국반도체 (390390)": {"etf": "390390.KS", "nav_proxy": "^SOX"},
    "IBK K-AI반도체코어테크 (0005G0)": {"etf": "0005G0.KS", "nav_proxy": "^KRXSEM"},
    "KORU (MSCI Korea 3X)": {"etf": "KORU", "nav_proxy": "^KS11"},
    "EWY (MSCI Korea South)": {"etf": "EWY", "nav_proxy": "^KS11"}
}

# 정규식을 이용해 앞뒤 공백이나 특수문자($ 등)를 완벽하게 제거하고 순수 코드만 추출
etf_ticker = ticker_map[target_etf]["etf"].strip().replace("$", "")
nav_ticker = ticker_map[target_etf]["nav_proxy"].strip().replace("$", "")

placeholder = st.empty()

while True:
    with placeholder.container():
        try:
            # 실시간 데이터 가져오기
            etf_data = yf.Ticker(etf_ticker).history(period="1d", interval="1m").iloc[-1]
            nav_data = yf.Ticker(nav_ticker).history(period="1d", interval="1m").iloc[-1]
            
            etf_price = round(etf_data["Close"], 2)
            base_nav = round(nav_data["Close"], 2)
            
            # 종목별 환산 스케일링 세부 조정 알고리즘
            if "069500" in etf_ticker:
                ratio = (etf_price * 10) / base_nav
            elif "005930" in etf_ticker:
                ratio = (etf_price / 25) / (base_nav / 50)
            elif "KORU" in etf_ticker or "EWY" in etf_ticker:
                ratio = etf_price / (base_nav / 50)
            else:
                ratio = (etf_price / 4) / (base_nav / 50) if base_nav > 0 else 1.0
                
            disparity = round((ratio - 1) * 100, 2)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 전광판 배치
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                # 미국 주식은 $, 한국 주식/ETF는 원화(₩) 표시 구분
                unit = "$" if not any(x in etf_ticker for x in [".KS", ".KQ"]) else "₩"
                st.metric(label=f"📊 {target_etf.split(' ')[0]} 현재 가격", value=f"{unit}{etf_price:,}")
            with kpi2:
                st.metric(label=f"💎 추적 벤치마크 지수 ({nav_ticker})", value=f"{base_nav:,} pt")
            with kpi3:
                if disparity <= -0.5:
                    status_msg = "🚨 프로그램 매도 폭탄 / 과매도"
                    delta_color = "inverse"
                elif disparity >= 0.5:
                    status_msg = "🔥 과열 / 추격 매수 위험"
                    delta_color = "normal"
                else:
                    status_msg = "✅ 정상 궤도 내 움직임"
                    delta_color = "off"
                st.metric(label=f"⚡ 실시간 기준치 대비 격차", value=f"{disparity} %", delta=f"{disparity}%", delta_color=delta_color)

            st.markdown("---")
            
            # 차트 시각화
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 장중 실시간 1분봉 추이")
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
            st.warning("데이터 연결을 재시도 중이거나 장마감(휴일) 상태입니다.")
            
    time.sleep(refresh_rate)
