import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="K-Stock AI Lab", layout="wide")

# --- UI 스타일 ---
st.markdown("""
    <style>
    .main { background-color: #0f1117; color: #ffffff; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- 한국투자증권(KIS) 실시간 데이터 가져오기 함수 ---
def get_kis_data(symbol, app_key, app_secret):
    try:
        # 토큰 발급
        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        body = {"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret}
        res = requests.post(url, data=json.dumps(body))
        token = res.json().get('access_token')
        
        # 일봉 데이터 조회
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotation/inquire-daily-itemchartprice"
        headers = {"content-type":"application/json", "authorization":f"Bearer {token}", 
                   "appkey":app_key, "appsecret":app_secret, "tr_id":"FHKST03010100"}
        params = {"fid_cond_mrkt_div_code":"J", "fid_input_iscd":symbol, "fid_input_date_1":"20240101", "fid_input_date_2":datetime.now().strftime("%Y%m%d"), "fid_period_div_code":"D", "fid_org_adj_prc":"1"}
        
        res = requests.get(url, headers=headers, params=params)
        data = res.json().get('output2', [])
        df = pd.DataFrame(data)
        if not df.empty:
            df = df[['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']]
            df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
            for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date')
    except:
        return None

# --- 가짜 데이터 (API 연결 실패 시) ---
def get_demo_data():
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n)
    prices = 70000 + np.random.randn(n).cumsum() * 1000
    return pd.DataFrame({'Date': dates, 'Close': prices, 'Open': prices*0.99, 'High': prices*1.01, 'Low': prices*0.98, 'Volume': np.random.randint(100, 1000, n)})

# --- 사이드바 설정 (여기에 키를 넣으세요) ---
st.sidebar.title("🔐 API 설정")
app_key = st.sidebar.text_input("KIS App Key", type="password")
app_secret = st.sidebar.text_input("KIS App Secret", type="password")
symbol = st.sidebar.text_input("종목코드", value="005930")

# --- 데이터 로드 및 AI 예측 ---
if app_key and app_secret:
    df = get_kis_data(symbol, app_key, app_secret)
    mode = "실시간"
else:
    df = get_demo_data()
    mode = "데모"

if df is not None:
    # AI 예측 (랜덤포레스트)
    df['MA'] = df['Close'].rolling(5).mean()
    train = df.dropna()
    model = RandomForestRegressor().fit(train[['Open','High','Low','Volume','MA']], train['Close'])
    pred = model.predict(df.tail(1)[['Open','High','Low','Volume','MA']])[0]
    
    # 메인 화면
    st.title(f"📊 {symbol} 주가 예측 ({mode})")
    c1, c2 = st.columns(2)
    c1.metric("현재가", f"{int(df['Close'].iloc[-1]):,}원")
    c2.metric("AI 내일 예상가", f"{int(pred):,}원")
    
    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("API 연결 실패. 키를 확인해 주세요.")
