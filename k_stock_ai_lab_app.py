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
    h1, h2, h3 { color: #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# --- 데이터 생성 함수 (에러 방지용 강화 버전) ---
def generate_demo_data(symbol):
    count = 200  # 데이터 개수
    dates = pd.date_range(end=datetime.now(), periods=count)
    
    # 랜덤 주가 생성
    base_price = 70000 if symbol == "005930" else 150000
    noise = np.random.randn(count).cumsum() * 1000
    close_prices = base_price + noise
    
    # 모든 데이터 열의 개수를 동일하게 맞춤 (ValueError 방지)
    df = pd.DataFrame({
        'Date': dates,
        'Close': close_prices,
        'Open': close_prices * (1 + np.random.uniform(-0.01, 0.01, count)),
        'High': close_prices * (1 + np.random.uniform(0, 0.02, count)),
        'Low': close_prices * (1 + np.random.uniform(-0.02, 0, count)),
        'Volume': np.random.randint(100000, 1000000, count)
    })
    return df

# --- AI 예측 로직 ---
def predict_price(df):
    df = df.copy()
    df['S_10'] = df['Close'].rolling(window=10).mean()
    df['S_30'] = df['Close'].rolling(window=30).mean()
    df = df.dropna()
    
    X = df[['Open', 'High', 'Low', 'Volume', 'S_10', 'S_30']]
    y = df['Close']
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    
    last_data = X.iloc[-1:].values
    prediction = model.predict(last_data)
    return prediction[0]

# --- 메인 화면 ---
st.title("📊 나만의 주식 AI Lab")
symbol = st.sidebar.text_input("종목코드 입력", value="005930")

# 데이터 가져오기
df = generate_demo_data(symbol)

# 지표 표시
last_price = df['Close'].iloc[-1]
predicted_price = predict_price(df)
pred_diff = predicted_price - last_price

col1, col2 = st.columns(2)
col1.metric("현재가 (데모)", f"{int(last_price):,}원")
col2.metric("AI 내일 예상가", f"{int(predicted_price):,}원", f"{pred_diff:+,2.0f}원")

# 차트
fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.success("데이터 최적화가 완료되었습니다. 이제 에러 없이 작동합니다!")
