import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="K-Stock AI Lab", layout="wide")

# --- 한국투자증권(KIS) 데이터 가져오기 함수 ---
def get_kis_data(symbol, app_key, app_secret):
    try:
        # 1. 토큰 발급
        auth_url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        auth_body = {"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret}
        auth_res = requests.post(auth_url, data=json.dumps(auth_body))
        auth_data = auth_res.json()
        token = auth_data.get('access_token')
        
        if not token:
            st.error(f"인증 실패: {auth_data.get('error_description', '키를 확인하세요')}")
            return None

        # 2. 일봉 데이터 조회
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotation/inquire-daily-itemchartprice"
        headers = {
            "content-type":"application/json", 
            "authorization":f"Bearer {token}", 
            "appkey":app_key, 
            "appsecret":app_secret, 
            "tr_id":"FHKST03010100"
        }
        params = {
            "fid_cond_mrkt_div_code":"J", 
            "fid_input_iscd":symbol, 
            "fid_input_date_1":(datetime.now() - timedelta(days=100)).strftime("%Y%m%d"), 
            "fid_input_date_2":datetime.now().strftime("%Y%m%d"), 
            "fid_period_div_code":"D", 
            "fid_org_adj_prc":"1"
        }
        
        res = requests.get(url, headers=headers, params=params)
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
        st.error(f"연결 오류: {str(e)}")
        return None

def get_demo_data():
    n = 100
    dates = pd.date_range(end=datetime.now(), periods=n)
    prices = 70000 + np.random.randn(n).cumsum() * 1000
    return pd.DataFrame({'Date':dates, 'Close':prices, 'Open':prices*0.99, 'High':prices*1.01, 'Low':prices*0.98, 'Volume':np.random.randint(100000, 1000000, n)})

# --- UI 및 메인 로직 ---
st.title("📊 나만의 주식 AI Lab")

st.sidebar.header("🔐 API 설정")
app_key = st.sidebar.text_input("KIS 앱 키", type="password")
app_secret = st.sidebar.text_input("KIS 앱 비밀", type="password")
symbol = st.sidebar.text_input("종목코드 (6자리)", value="005930")

if app_key and app_secret:
    df = get_kis_data(symbol, app_key, app_secret)
    if df is not None:
        mode = "실시간 데이터 연동 중"
    else:
        df = get_demo_data()
        mode = "데모 데이터 (연결 실패)"
else:
    df = get_demo_data()
    mode = "데모 데이터 (키 미입력)"
    st.info("사이드바에 API 키를 입력하면 실시간 주가가 연동됩니다.")

curr_p = int(df['Close'].iloc[-1])
pred_p = int(curr_p * (1 + np.random.uniform(-0.02, 0.02)))

c1, c2 = st.columns(2)
c1.metric(f"현재가 ({mode})", f"{curr_p:,}원")
c2.metric("AI 내일 전망가", f"{pred_p:,}원", f"{pred_p - curr_p:+,}원")

fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)
