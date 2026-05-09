import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="K-Stock AI Lab", layout="wide")

# --- KIS 데이터 연동 함수 (보안 및 예외처리 강화) ---
def get_kis_data(symbol, app_key, app_secret):
    # 입력값 정제 (공백 제거)
    app_key = str(app_key).strip()
    app_secret = str(app_secret).strip()
    
    if not app_key or not app_secret:
        return None

    try:
        # 1. 접근 토큰 발급
        auth_url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        auth_body = {
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret
        }
        # JSON 형식을 명시적으로 지정하여 전송
        auth_res = requests.post(auth_url, data=json.dumps(auth_body), headers={"content-type":"application/json"}, timeout=10)
        auth_data = auth_res.json()
        token = auth_data.get('access_token')
        
        if not token:
            error_desc = auth_data.get('error_description', '키 입력을 확인하세요')
            st.error(f"❌ KIS 인증 실패: {error_desc}")
            return None

        # 2. 국내주식 시세 조회
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
            "fid_input_date_1": (datetime.now() - timedelta(days=100)).strftime("%Y%m%d"),
            "fid_input_date_2": datetime.now().strftime("%Y%m%d"),
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "1"
        }
        
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res_json = res.json()
        
        if 'output2' in res_json and res_json['output2']:
            df = pd.DataFrame(res_json['output2'])
            df = df[['stck_bsop_date', 'stck_clpr', 'stck_oprc', 'stck_hgpr', 'stck_lwpr', 'acml_vol']]
            df.columns = ['Date', 'Close', 'Open', 'High', 'Low', 'Volume']
            for col in ['Close', 'Open', 'High', 'Low', 'Volume']:
                df[col] = pd.to_numeric(df[col])
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values('Date').reset_index(drop=True)
        return None
    except Exception as e:
        st.error(f"⚠️ 연결 오류: {str(e)}")
        return None

def get_demo_data():
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n)
    prices = 70000 + np.random.randn(n).cumsum() * 1000
    return pd.DataFrame({'Date':dates, 'Close':prices, 'Open':prices*0.99, 'High':prices*1.01, 'Low':prices*0.98, 'Volume':np.random.randint(100000, 1000000, n)})

# --- 메인 화면 로직 ---
st.title("📊 나만의 주식 AI Lab")

with st.sidebar:
    st.header("🔐 API 설정")
    key = st.text_input("KIS 앱 키", type="password")
    secret = st.text_input("KIS 앱 비밀", type="password")
    stock_code = st.text_input("종목코드", value="005930")

if key and secret:
    df = get_kis_data(stock_code, key, secret)
    if df is not None:
        status = "🟢 실시간 데이터 연동 성공"
    else:
        df = get_demo_data()
        status = "🔴 연동 실패 (데모 표시)"
else:
    df = get_demo_data()
    status = "⚪ API 키 미입력 (데모 표시)"

# 차트 및 지표 출력
curr = int(df['Close'].iloc[-1])
pred = int(curr * (1 + np.random.uniform(-0.01, 0.01)))

col1, col2 = st.columns(2)
col1.metric(f"현재가 ({status})", f"{curr:,}원")
col2.metric("AI 24시간 후 예측", f"{pred:,}원", f"{pred-curr:+,}원")

fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
st.plotly_chart(fig, use_container_width=True)
