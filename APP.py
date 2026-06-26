import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 1. 페이지 레이아웃 설정
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

# 3. 네이버 실시간 주가 API 수집 (하락 부호 '-' 처리 정밀 보완)
def get_naver_multi_prices_safe(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    base_url = "https://polling.finance.naver.com/api/realtime"
    url = f"{base_url}?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=3)
        data = response.json()
        raw_datas = data['result']['areas'][0]['datas']
        for item in raw_datas:
            c = item['cd']
            price = float(item['nv']) if item.get('nv') is not None else 0.0
            
            # 💡 네이버 API 특성 보완: 전일대비 등락구분코드(rf) 가 4 또는 5이면 '하락/하한가'이므로 마이너스 처리
            raw_rate = float(item['cr']) if item.get('cr') is not None else 0.0
            rf_code = str(item.get('rf', ''))
            if rf_code in ['4', '5'] and raw_rate > 0:
                rate = -raw_rate
            else:
                rate = raw_rate
                
            nav = float(item['nav']) if 'nav' in item and item['nav'] is not None else None
            if price > 0:
                st.session_state.stock_cache[c] = {
                    "price": price, 
                    "rate": rate, 
                    "nav": nav
                }
    except:
        pass
    return st.session_state.stock_cache

# 4. 국내 지수 파싱
def fetch_naver_index_safe():
    headers = {'User-Agent': 'Mozilla/5.0'}
    # 코스피
    try:
        kp_url = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
        res = requests.get(kp_url, headers=headers, timeout=2)
        if res.status_code == 200:
            txt = res.text
            p_now = txt.split('id="now_value">')[1].split('<')[0]
            p_now = p_now.replace(",", "")
            p_rt = txt.split('id="change_value_and_rate">')[1].split('%')[0]
            p_rt = p_rt.split()[-1].replace("+", "")
            st.session_state.macro_cache["kospi"] = {
                "price": float(p_now), 
                "rate": float(p_rt)
            }
    except:
        pass

    # 환율
    try:
        fx_url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
        res = requests.get(fx_url, headers=headers, timeout=2)
        if res.status_code == 200:
            txt = res.text
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
            st.session_state.macro_cache["usd_krw"] = {
                "price": f_price, 
                "rate": f_rate_pct
            }
    except:
        pass

# 5. 해외 지수 야후 파이낸스 수집
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
                st.session_state.macro_cache[key] = {
                    "price": round(current_price, 2), 
                    "rate": change_rate
                }
    except:
        pass

# 초기 구동 데이터 로드
fetch_naver_index_safe()
fetch_yahoo_macro_safe()

# 6. 사이드바 메뉴 배치
with st.sidebar:
    st.header("⚙️ 레이더 설정")
    refresh_rate = st.slider(
        "새로고침 주기 (초)", 
        min_value=2, 
        max_value=10, 
        value=3
    )
    st.markdown("---")
    st.markdown("### 🎯 모니터링 타깃")
    target_name = st.selectbox(
        "감시할 종목/ETF 선택", 
        [
            "KODEX 200 (069500)",
            "삼성전자 (005930)",
            "카카오뱅크 (323410)",
            "KODEX 미국반도체MV (390390)",
            "TIGER 미국필라델피아반도체나스닥 (381180)",
            "PLUS 글로벌HBM반도체 (442580)",
            "TIGER 반도체TOP10 (396500)",
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

# 화면 덮어쓰기용 플레이스홀더
placeholder = st.empty()

# 7. 실시간 무한 루프 관제망
while True:
    fetch_naver_index_safe()
    fetch_yahoo_macro_safe()
    single_stock = get_naver_multi_prices_safe([code])
    macro = st.session_state.macro_cache
    
    local_tz = pytz.timezone('Asia/Seoul')
    current_time_str = datetime.now(local_tz).strftime("%H:%M:%S")
    
    # 중복 컴포넌트 충돌 방지 고유 난수 키 생성
    loop_key = str(int(time.time() * 1000))
    
    with placeholder.container():
        st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        
        with m_col1:
            val_kp = f"{macro['kospi']['price']:,} pt"
            st.metric(
                label="⚡ KOSPI 지수 (실시간)", 
                value=val_kp, 
                delta=f"{macro['kospi']['rate']}%"
            )
        with m_col2:
            val_fx = f"₩{macro['usd_krw']['price']:,}"
            st.metric(
                label="💵 원/달러 환율 (실시간)", 
                value=val_fx, 
                delta=f"{macro['usd_krw']['rate']}%"
            )
        with m_col3:
            val_wti = f"${macro['wti']['price']:,}"
            st.metric(
                label="🛢️ WTI 국제유가 [야후]", 
                value=val_wti, 
                delta=f"{macro['wti']['rate']}%"
            )
        with m_col4:
            val_sox = f"{macro['taco']['price']:,} pt"
            st.metric(
                label="🌮 필라델피아 반도체 [야후]", 
                value=val_sox, 
                delta=f"{macro['taco']['rate']}%"
            )

        st.markdown("---")
        st.title("📡 실시간 괴리율 & 변동성 종합 레이더")

        if code in single_stock and single_stock[code]["price"] > 0:
            price = int(single_stock[code]["price"])
            fluctuation_rate = single_stock[code]["rate"]
            nav = single_stock[code]["nav"]
            
            is_etf = nav is not None and nav > 0
            
            if is_etf:
                diff = price - nav
                disparity_rate = round((diff / nav) * 100, 2)
            else:
                disparity_rate = 0.0
            
            if not st.session_state.price_history or st.session_state.price_history[-1] != price or len(st.session_state.price_history) < 2:
                st.session_state.price_history.append(price)
                st.session_state.time_history.append(current_time_str)
            
            if len(st.session_state.price_history) > 20:
                st.session_state.price_history.pop(0)
                st.session_state.time_history.pop(0)
                
            # 메인 데이터 메트릭스 전광판
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.metric(
                    label="📊 현재 가격", 
                    value=f"₩{price:,}", 
                    delta=f"{fluctuation_rate}%"
                )
            with kpi2:
                nav_value = f"₩{int(nav):,}" if is_etf else "N/A (일반주식)"
                st.metric(label="🎯 실시간 NAV", value=nav_value)
            with kpi3:
                if is_etf:
                    status_disparity = "🚨 고평가" if disparity_rate >= 0.5 else ("🔵 저평가" if disparity_rate <= -0.5 else "✅ 정상")
                    st.metric(
                        label=f"🔍 실시간 괴리율 ({status_disparity})", 
                        value=f"{disparity_rate} %", 
                        delta=f"{disparity_rate}%", 
                        delta_color="inverse"
                    )
                else:
                    st.metric(label="🔍 실시간 괴리율", value="N/A")
            
            st.markdown(
                "<p style='text-align: right; color: gray; font-size: 12px; margin-top: -10px;'>📊 출처: Naver Finance Feed & Yahoo Finance API</p>", 
                unsafe_allow_html=True
            )
            st.markdown("---")
            
            # 차트 영역 및 게이지 분할 레이아웃
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("### 📈 실시간 주가 추이")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=st.session_state.time_history, 
                    y=st.session_state.price_history, 
                    mode='lines+markers', 
                    line=dict(color='#00ffcc', width=2.5)
                ))
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20), 
                    height=380, 
                    template="plotly_dark"
                )
                st.plotly_chart(
                    fig, 
                    use_container_width=True, 
                    key=f"chart_{loop_key}"
                )
                
            with col2:
                st.markdown("### 📊 리스크 종합 분석")
                g_col1, g_col2 = st.columns(2)
                
                with g_col1:
                    st.markdown("##### 🎯 괴리율 미터")
                    if is_etf:
                        fig_gauge1 = go.Figure(go.Indicator(
                            mode="gauge+number", 
                            value=disparity_rate, 
                            domain={'x': [0, 1], 'y': [0, 1]},
                            gauge={
                                'axis': {'range': [-2, 2]}, 
                                'bar': {'color': "white"}, 
                                'steps': [
                                    {'range': [-2, -0.5], 'color': "navy"}, 
                                    {'range': [-0.5, 0.5], 'color': "forestgreen"}, 
                                    {'range': [0.5, 2], 'color': "crimson"}
                                ]
                            }
                        ))
                        fig_gauge1.update_layout(
                            height=180, 
                            margin=dict(l=10, r=10, t=10, b=10), 
                            template="plotly_dark"
                        )
                        st.plotly_chart(
                            fig_gauge1, 
                            use_container_width=True, 
                            key=f"g1_{loop_key}"
                        )
                    else:
                        st.info("ETF 전용 지표입니다.")
                
                with g_col2:
                    st.markdown("##### 🛑 변동성 리스크")
                    fig_gauge2 = go.Figure(go.Indicator(
                        mode="gauge+number", 
                        value=fluctuation_rate, 
                        domain={'x': [0, 1], 'y': [0, 1]},
                        gauge={
                            'axis': {'range': [-5, 5]}, 
                            'bar': {'color': "white"}, 
                            'steps': [
                                {'range': [-5, -1.5], 'color': "crimson"}, 
                                {'range': [-1.5, 1.5], 'color': "forestgreen"}, 
                                {'range': [1.5, 5], 'color': "darkorange"}
                            ]
                        }
                    ))
                    fig_gauge2.update_layout(
                        height=180, 
                        margin=dict(l=10, r=10, t=10, b=10), 
                        template="plotly_dark"
                    )
                    st.plotly_chart(
                        fig_gauge2, 
                        use_container_width=True, 
                        key=f"g2_{loop_key}"
                    )
                
            st.caption(f"동기화 시간: {datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')} | 시스템 가동 중")
        else:
            st.warning("데이터 동기화 중입니다. 잠시만 기다려주세요...")
            
    time.sleep(refresh_rate)
