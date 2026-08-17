import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="AI 量化分析系統", layout="wide")
st.title("🤖 7合1 量化分析系統（免費分享版）")
st.caption(f"更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 側邊欄輸入
ticker = st.text_input("輸入股票代號", value="TSLA").upper()
period = st.selectbox("數據週期", ["1mo", "3mo", "6mo", "1y"], index=2)

if st.button("🚀 分析"):
    with st.spinner("分析中..."):
        # 下載數據
        data = yf.download(ticker, period=period, interval="1d", progress=False)
        if data.empty:
            st.error("無數據，請檢查股票代號")
            st.stop()
        
        # ---- 技術指標 ----
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        exp12 = data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        
        # 均線
        sma20 = data['Close'].rolling(20).mean()
        sma50 = data['Close'].rolling(50).mean()
        
        # 布林帶
        bb_mid = data['Close'].rolling(20).mean()
        bb_std = data['Close'].rolling(20).std()
        bb_upper = bb_mid + (bb_std * 2)
        bb_lower = bb_mid - (bb_std * 2)
        
        # 最新值
        latest_price = data['Close'].iloc[-1]
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd.iloc[-1]
        latest_signal = signal.iloc[-1]
        latest_sma20 = sma20.iloc[-1]
        latest_sma50 = sma50.iloc[-1]
        latest_bb_upper = bb_upper.iloc[-1]
        latest_bb_lower = bb_lower.iloc[-1]
        
        macd_diff = latest_macd - latest_signal
        
        # ---- 判斷信號 ----
        score = 0
        signals = []
        
        if latest_rsi < 30:
            score += 1
            signals.append("超賣")
        elif latest_rsi > 70:
            score -= 1
            signals.append("超買")
        
        if macd_diff > 0:
            score += 1
            signals.append("MACD轉強")
        else:
            score -= 1
            signals.append("MACD轉弱")
        
        if latest_price > latest_sma20:
            score += 1
        if latest_price > latest_sma50:
            score += 1
        
        if latest_price < latest_bb_lower:
            score += 1
            signals.append("跌破下軌")
        elif latest_price > latest_bb_upper:
            score -= 1
            signals.append("突破上軌")
        
        if score >= 2:
            trend = "🔥 偏向買入"
        elif score <= -2:
            trend = "⚠️ 偏向賣出"
        else:
            trend = "⏸️ 中性持有"
        
        # ---- 顯示結果 ----
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最新價格", f"${latest_price:.2f}")
        col2.metric("RSI (14天)", f"{latest_rsi:.1f}", 
                    delta="超買" if latest_rsi > 70 else "超賣" if latest_rsi < 30 else "中性")
        col3.metric("MACD差額", f"{macd_diff:.2f}")
        col4.metric("綜合信號", trend)
        
        st.divider()
        
        # 詳細數據
        st.subheader("📊 詳細指標")
        col1, col2, col3 = st.columns(3)
        col1.write(f"**SMA20**：${latest_sma20:.2f}")
        col1.write(f"**SMA50**：${latest_sma50:.2f}")
        col2.write(f"**布林上軌**：${latest_bb_upper:.2f}")
        col2.write(f"**布林下軌**：${latest_bb_lower:.2f}")
        col3.write(f"**信號標籤**：{', '.join(signals)}")
        col3.write(f"**綜合評分**：{score}")
        
        # ---- 圖表 ----
        st.subheader("📈 走勢圖")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data.index, data['Close'], label='價格', color='black')
        ax.plot(data.index, sma20, label='SMA20', linestyle='--', color='blue')
        ax.plot(data.index, sma50, label='SMA50', linestyle='--', color='orange')
        ax.fill_between(data.index, bb_lower, bb_upper, alpha=0.1, color='gray')
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_title(f'{ticker} 技術分析圖')
        st.pyplot(fig)
        
        st.caption("⚠️ 免責聲明：僅供參考，不構成投資建議")

st.sidebar.markdown("""
### 📌 使用方法
1. 輸入股票代號（例如 TSLA、AAPL、0700.HK）
2. 選擇數據週期
3. 禁「分析」按鈕
4. 即時睇到信號

### 🆓 免費分享版
- 完全免費
- 無需安裝
- 任何裝置都用得
""")