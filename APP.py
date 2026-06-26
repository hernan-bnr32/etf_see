import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="국내 상장 ETF 실시간 레이더", layout="wide", initial_sidebar_state="expanded")

st.title("📡 네이버 금융 연동 실시간 ETF 및 종목 모니터링 시스템")
st.markdown("본 대시보드는 네이버 증권 실시간 시세를 파싱하여 2초마다 자동 갱신됩니다.")

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

# 종목 코드 추출 (괄호 안의 6자리 숫자)
code = target_name.split("(")[-1].replace(")", "").strip()

# 💡 네이버 증권 실시간 데이터 스크래핑 함수
def get_naver_stock_price(item_code):
    url = f"https://finance.naver.com/item/sise_mini.naver?code={item_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        dfs = pd.read_html(response.text)
        df = dfs[0] # 첫 번째 테이블 선택
        
        # 네이버 미니시세 테이블 파싱
        current_price = int(df.iloc[0, 1].replace(",", ""))
        change_text = df.iloc[1, 1].split()
        
        # 등락률 추출
        direction = change_text[0]
        change_val = change_text[1].replace(",", "")
        rate = float(change_text[2].replace("%", "").replace("+", ""))
        
        if "하락" in direction or "-" in direction:
            rate = -rate
            
        return current_price, rate
    except:
        return None, None

placeholder = st.empty()

# 임시 차트 데이터 축적용 리스트
if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = code

# 종목 변경 시 차트 초기화
if st.session_state.last_code != code:
    st.session_state.price_history = []
    st.session_state.time_history = []
    st.session_state.last_code = code

while True:
    with placeholder.container():
        price, fluctuation_rate = get_naver_stock_price(code)
        current_time = datetime.now().strftime("%H:%M:%S")
        
        if price is not None:
            # 데이터 축적
            st.session_state.price_history.append(price)
            st.session_state.time_history.append(current_time)
            
            # 최근 20개 데이터만 유지
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            # 전광판 배치
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric(label=f"📊 {target_name.split(' ')[0]} 현재가", value=f"₩{price:,}")
            with kpi2:
                status_msg = "🔥 과열" if fluctuation_rate >= 1.5 else ("🚨 과매도" if fluctuation_rate <= -1.5 else "✅ 정상")
                st.metric(label=f"⚡ 장중 등락률 ({status_msg})", value=f"{fluctuation_rate} %", delta=f"{fluctuation_rate}%")
                
            st.markdown("---")
            
            # 차트 그리기
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 스크래핑 가격 추이 (장중 캐싱)")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=st.session_state.time_history, y=st.session_state.price_history, mode='lines+markers', line=dict(color='#00ffcc', width=2)))
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown("### 🛑 등락 폭 게이지")
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
                
            st.caption(f"네이버 금융 동기화 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 시스템 가동 중")
        else:
            st.warning("네이버 금융 연결을 재시도 중이거나 장마감(휴일) 상태입니다.")
            
    time.sleep(refresh_rate)
