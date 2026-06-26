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
st.markdown("본 대시보드는 네이버 증권 시세를 기반으로 작동하며, 24시간 화면을 유지합니다.")

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

# 데이터 파싱 함수
def get_naver_stock_price(item_code):
    url = f"https://finance.naver.com/item/main.naver?code={item_code}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        dfs = pd.read_html(response.text)
        
        # 현재가 추출
        df_sise = dfs[2] 
        current_price = int(str(df_sise.iloc[0, 1]).replace(",", ""))
        
        # 등락률 추출
        df_rate = dfs[1]
        rate_text = str(df_rate.iloc[0, 1]).split("%")[0].strip().replace("+", "")
        rate_cleaned = "".join([c for c in rate_text if c.isdigit() or c in ['.', '-']])
        
        fluctuation_rate = float(rate_cleaned) if rate_cleaned else 0.0
        return current_price, fluctuation_rate
    except:
        try:
            url_mini = f"https://finance.naver.com/item/sise_mini.naver?code={item_code}"
            res_mini = requests.get(url_mini, headers=headers)
            df_m = pd.read_html(res_mini.text)[0]
            c_price = int(str(df_m.iloc[0, 1]).replace(",", ""))
            return c_price, 0.0
        except:
            return None, None

# 세션 상태 캐싱 초기화
if "price_history" not in st.session_state:
    st.session_state.price_history = []
if "time_history" not in st.session_state:
    st.session_state.time_history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = code

# 종목 교체 시 초기화
if st.session_state.last_code != code:
    st.session_state.price_history = []
    st.session_state.time_history = []
    st.session_state.last_code = code

placeholder = st.empty()

while True:
    with placeholder.container():
        price, fluctuation_rate = get_naver_stock_price(code)
        
        # 대한민국 시간대 고정
        local_tz = pytz.timezone('Asia/Seoul')
        current_time = datetime.now(local_tz).strftime("%H:%M:%S")
        
        if price is not None:
            st.session_state.price_history.append(price)
            st.session_state.time_history.append(current_time)
            
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            # 대시보드 상단 지표
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric(label="📊 현재 가격", value=f"₩{price:,}")
            with kpi2:
                status_msg = "🔥 과열" if fluctuation_rate >= 1.5 else ("🚨 과매도" if fluctuation_rate <= -1.5 else "✅ 정상")
                st.metric(label=f"⚡ 장중 변동률 ({status_msg})", value=f"{fluctuation_rate} %", delta=f"{fluctuation_rate}%")
                
            st.markdown("---")
            
            # 차트 및 게이지 배치
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 주가 추이")
                fig = go.Figure()
                # 괄호 닫힘 오류 수정을 위해 한 줄로 깔끔하게 정리
                fig.add_trace(go.Scatter(x=st.session_state.time_history, y=st.session_state.price_history, mode='lines+markers', line=dict(color='#00ffcc', width=2.5)))
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=300, template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown("### 🛑 리스크 변동 게이지")
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
                
            st.caption(f"KST: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} | Running...")
        else:
            st.warning("Connecting to server...")
            
    time.sleep(refresh_rate)
