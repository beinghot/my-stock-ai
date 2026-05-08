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

# --- AlphaSquare 스타일 UI 적용 ---
st.markdown("""
    <style>
    .main { background-color: #0f1117; color: #ffffff; }
    .stTextInput>div>div>input { background-color: #1a1c24; color: white; border: 1px solid #30363d; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #3b82f6; color: white; border: none; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    h1, h2, h3 { color: #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# --- 한국투자증권(KIS) API 관련 함수 ---
def get_kis_token(app_key, app_secret):
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    payload = {"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret}
    try:
        res = requests.post(url, data=json.dumps(payload))
        if res.status_code == 200:
            return res.json().get('access_token')
    except:
        pass
    return None

def fetch_kis_data(symbol, token, app_key, app_secret):
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": "FHKST03010100"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol,
        "FID_INPUT_DATE_1": (datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
        "FID_INPUT_DATE_2": datetime.now().strftime('%Y%m%d'),
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0000000001"
    }
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            data = res.json().get('output2', [])
            df = pd.DataFrame(data)
            if not df.empty:
                df = df[['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']]
                df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
                df['Date'] = pd.to_datetime(df['Date'])
                for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                    df[col] = pd.to_numeric(df[col])
                return df.sort_values('Date')
    except:
        pass
    return None

def generate_demo_data(symbol):
    dates = pd.date_range(end=datetime.now(), periods=100)
    base_price = 70000 if symbol == "005930" else 150000
    prices = base_price + np.cumsum(np.random.randn(100) * 1000)
    df = pd.DataFrame({
        'Date': dates, 'Close': prices, 'Open': prices * 0.99,
        'High': prices * 1.01, 'Low': prices * 0.98,
        'Volume': np.random.randint(100000, 1000000, 100)
    })
    return df

# --- AI 주가 예측 로직 ---
def predict_price(df):
    df = df.copy()
    df['S_10'] = df['Close'].rolling(window=10).mean()
    df['S_30'] = df['Close'].rolling(window=30).mean()
    df = df.dropna()
    
    X = df[['Open', 'High', 'Low', 'Volume', 'S_10', 'S_30']]
    y = df['Close']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    last_data = X.iloc[-1:].values
    prediction = model.predict(last_data)
    return prediction[0]

# --- 사이드바 설정 ---
st.sidebar.title("K-Stock AI 설정")
symbol = st.sidebar.text_input("종목코드 입력", value="005930")
use_real_data = st.sidebar.checkbox("KIS 실데이터 사용")

kis_token = None
if use_real_data:
    app_key = st.sidebar.text_input("KIS App Key", type="password")
    app_secret = st.sidebar.text_input("KIS App Secret", type="password")
    if app_key and app_secret:
        kis_token = get_kis_token(app_key, app_secret)
        if kis_token:
            st.sidebar.success("인증 성공")
        else:
            st.sidebar.error("인증 실패")

# --- 메인 대시보드 ---
st.title("📊 나만의 주식 AI Lab")
st.caption("AlphaSquare 스타일의 AI 주가 예측 앱")

if use_real_data and kis_token:
    df = fetch_kis_data(symbol, kis_token, app_key, app_secret)
    data_source = "실시간 API"
else:
    df = generate_demo_data(symbol)
    data_source = "데모 데이터"

if df is not None:
    last_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    diff = last_price - prev_price
    pct = (diff / prev_price) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{int(last_price):,}원", f"{pct:.2f}%")
    col2.metric("데이터 소스", data_source)
    
    predicted_price = predict_price(df)
    pred_diff = predicted_price - last_price
    col3.metric("AI 내일 예상가", f"{int(predicted_price):,}원", f"{pred_diff:+,2.0f}원")

    # 차트 생성
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="시세"))
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("데이터 상세 보기"):
        st.dataframe(df.tail(10), use_container_width=True)
else:
    st.error("데이터를 불러올 수 없습니다.")
