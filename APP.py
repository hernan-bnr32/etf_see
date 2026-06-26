import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
from datetime import datetime
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="글로벌 매크로 & ETF 실시간 레이더", layout="wide", initial_sidebar_state="expanded")

# 💡 네이버 실시간 API 수집 함수 (여러 종목 동시 조회 지원)
def get_naver_multi_prices(codes_list):
    query_str = ",".join([f"SERVICE_ITEM:{c}" for c in codes_list])
    url = f"https://polling.finance.naver.com/api/realtime?query={query_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    results = {}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        for item in data['result']['areas'][0]['datas']:
            c = item['cd'] # 종목코드
            price = float(item['nv']) # 현재가
            rate = float(item['cr']) # 등락률
            results[c] = {"price": price, "rate": rate}
        return results
    except:
        return {}

# 💡 인베스팅/네이버 시장지표(유가, 환율, 해외지수) 수집 함수
def get_macro_indicators():
    # 네이버 금융 시장지표 등의 실시간 피드 우회 주소
    url = "https://polling.finance.naver.com/api/realtime?query=SERVICE_MARKETINDEX:FX_USDKRW,SERVICE_MARKETINDEX:OIL_GSL,SERVICE_MARKETINDEX:SPI@KOSPI"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    macro_data = {
        "usd_krw": {"price": 0.0, "rate": 0.0},
        "wti": {"price": 0.0, "rate": 0.0},
        "kospi": {"price": 0.0, "rate": 0.0},
        "taco": {"price": 0.0, "rate": 0.0}
    }
    
    try:
        # 1. 코스피 / 환율 / 오일 기본 수집
        res = requests.get(url, headers=headers)
        data = res.json()
        for item in data['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv'])
            cr = float(item['cr']) if 'cr' in item and item['cr'] is not None else 0.0
            
            if cd == "FX_USDKRW":
                macro_data["usd_krw"] = {"price": nv, "rate": cr}
            elif cd == "OIL_GSL": # 네이버 제공 무연고시 기준 유가 또는 WTI 대체 피드
                macro_data["wti"] = {"price": nv, "rate": cr}
            elif cd == "SPI@KOSPI":
                macro_data["kospi"] = {"price": nv, "rate": cr}
                
        # 2. TACO(SOX 필라델피아 반도체 지수 등) 및 WTI 보완을 위한 해외 외환/원자재 보완 API
        # 미국 시장 지표용 (SOX 혹은 유가 파싱 실패 대비용 API 피드)
        url_global = "https://polling.finance.naver.com/api/realtime?query=SERVICE_WORLDINDEX:NAS@SOX,SERVICE_MARKETINDEX:OIL_CL"
        res_g = requests.get(url_global, headers=headers)
        data_g = res_g.json()
        for item in data_g['result']['areas'][0]['datas']:
            cd = item['cd']
            nv = float(item['nv'])
            cr = float(item['cr']) if 'cr' in item and item['cr'] is not None else 0.0
            
            if cd == "NAS@SOX": # 반도체 중심 타깃이므로 TACO 지수 대용으로 가장 중요한 '필라델피아 반도체지수(SOX)' 매칭
                macro_data["taco"] = {"price": nv, "rate": cr}
            elif cd == "OIL_CL": # 실제 WTI 선물 크루드 오일 가격
                macro_data["wti"] = {"price": nv, "rate": cr}
                
        return macro_data
    except:
        return macro_data

# --- 대시보드 상단 글로벌 매크로 전광판 배치 ---
st.markdown("### 🌐 글로벌 거시경제 및 시황 판넬")
macro = get_macro_indicators()

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.metric(
        label="📉 KOSPI 코스피 지수", 
        value=f"{macro['kospi']['price']:,} pt", 
        delta=f"{macro['kospi']['rate']}%"
    )
with m_col2:
    st.metric(
        label="💵 원/달러 환율", 
        value=f"₩{macro['usd_krw']['price']:,}", 
        delta=f"{macro['krw']['rate']}%"
