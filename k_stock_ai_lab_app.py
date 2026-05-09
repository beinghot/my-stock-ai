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
        auth_body = {"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret}
        auth_res = requests.post(auth_url, data=json.dumps(auth_body))
        token = auth_res.json().get('access_token')
        
        if not token: return None

        # 2. 일봉 데이터 조회
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotation/inquire-daily-itemchartprice"
        headers = {"content-type":"application/json", "authorization":f"Bearer {token}", "appkey":app_key, "appsecret":app_secret, "tr_id":"FHKST03010100"}
        params = {"fid_cond_mrkt_div_code":"J", "fid_input_iscd":symbol, "fid_input_date_1":(datetime.now() - timedelta(days=100)).strftime("%Y%m%d"), "fid_input_date_2":datetime.now().strftime("%Y%m%d"), "fid_period_div_code":"D", "fid_org_adj_prc":"1"}
        
        res = requests.get(url, headers=headers, params=params)
        res_json = res.json()
        
        if 'output2' in res_json:
            df = pd.DataFrame(res_json['output2'])
            df = df[['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']]
            df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
            for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date').reset_index(drop=True)
        return None
    except:
        return None

# --- 데모 데이터 생성 함수 ---
def get_demo_data():
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n)
    prices = 70000 + np.random.randn(n).cumsum() * 1000
    return pd.DataFrame({
        'Date': dates, 'Close': prices, 'Open': prices*0.99, 
        'High': prices*1.01, 'Low': prices*0.98, 'Volume': np.random.randint(100000, 1000000, n)
    })

# --- 사이드바 및 메인 로직 ---
st.sidebar.title("🔐 API 설정")
app_key = st.sidebar.text_input("KIS App Key", type="password")
app_secret = st.sidebar.text_input("KIS App Secret", type="password")
symbol = st.sidebar.text_input("종목코드 (6자리)", value="005930")

st.title("📊 나만의 주식 AI Lab")

# 데이터 로드 (키가 있으면 실시간, 없으면 데모)
if app_key and app_secret:
    df = get_kis_data(symbol, app_key, app_secret)
    mode = "실시간 연동중"
    if df is None:
        st.error("API 연결 실패. 키를 확인하거나 잠시 후 다시 시도하세요.")
        df = get_demo_data()
        mode = "데모(API 오류)"
else:
    df = get_demo_data()
    mode = "데모 모드"
    st.info("사이드바에 API 키를 입력하면 실시간 주가가 연결됩니다.")

# 화면 출력
if df is not None:
    curr_p = df['Close'].iloc[-1]
    # 간단한 AI 예측 (이동평균 기반)
    pred_p = curr_p + (df['Close'].iloc[-1] - df['Close'].iloc[-5]) * 0.1
    
    col1, col2 = st.columns(2)
    col1.metric(f"현재가 ({mode})", f"{int(curr_p):,}원")
    col2.metric("AI 내일 예상가", f"{int(pred_p):,}원", f"{int(pred_p - curr_p):+,}원")
    
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
