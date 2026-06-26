import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="글로벌 매크로 & ETF 실시간 종합 관제 레이더", layout="wide", initial_sidebar_state="expanded")

# 💡 네이버 실시간 API 수집 함수 (NAV 데이터 추출 포함)
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
            nav = float(item['nav']) if 'nav' in item and item['nav'] is not None else None
            results[c] = {"price": price, "rate": rate, "nav": nav}
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
code = target_name.split("(")
