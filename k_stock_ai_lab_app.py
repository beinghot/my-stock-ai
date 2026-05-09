import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="K-Stock AI Lab", layout="wide")

# --- UI 스타일 ---
st.markdown("""
    <style>
    .main { background-color: #0f1117; color: #ffffff; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    h1 { color: #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# --- 한국투자증권(KIS) 데이터 가져오기 함수 ---
def get_kis_data(symbol, app_key, app_secret):
    try:
        # 1. 토큰 발급
        auth_url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        auth_body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }
        auth_res = requests.post(auth_url, data=json.dumps(auth_body))
        auth_json = auth_res.json()
        token = auth_json.get('access_token')
        
        if not token:
            st.error(f"토큰 발급 실패: {auth_json.get('error_description', '키를 확인해주세요.')}")
            return None

        # 2. 일봉 데이터 조회 (최근 100일)
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotation/inquire-daily-itemchartprice"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
            "tr_id": "FHKST03010100"
        }
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": symbol,
            "fid_input_date_1": (datetime.now() - timedelta(days=150)).strftime("%Y%m%d"),
            "fid_input_date_2": datetime.now().strftime("%Y%m%d"),
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "1"
        }
        
        res = requests.get(url, headers=headers, params=params)
        res_json = res.json()
        
        if 'output2' in res_json and res_json['output2']:
            df = pd.DataFrame(res_json['output2'])
            df = df[['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']]
            df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
            # 숫자형 변환 및 날짜 정렬
            for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date').reset_index(drop=True)
        else:
            st.error(f"데이터 로드 실패: {res_json.get('msg1', '응답 데이터 없음')}")
            return None
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        return None

# --- 가짜 데이터 (API 미연결 시) ---
def get_demo_data():
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n)
    prices = 70000 + np.random.randn(n).cumsum() * 1000
    return pd.DataFrame({
        'Date': dates, 'Close': prices, 'Open': prices*0.99, 
        'High': prices*1.01, 'Low': prices*0.98, 'Volume': np.random.randint(100000, 1000000, n)
    })

# --- 사이드바 ---
st.sidebar.title("🔐 API 설정")
st.sidebar.info("한국투자증권 API 키를 입력하면 실시간 주가가 연동됩니다.")
app_key = st.sidebar.text_input("KIS App Key", type="password", help="발급받은 App Key를 입력하세요")
app_secret = st.sidebar.text_input("KIS App Secret", type="password", help="발급받은 App Secret을 입력하세요")
symbol = st.sidebar.text_input("종목코드 (6자리)", value="005930")

# --- 메인 로직 ---
st.title("📊 나만의 주식 AI Lab")

if app_key and app_secret:
    df = get_kis_data(symbol, app_key, app_secret)
    mode = "실시간 API 연결됨"
else:
    df = get_demo_
