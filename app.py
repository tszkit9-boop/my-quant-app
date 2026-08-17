import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# ==========================================
# 頁面設定
# ==========================================
st.set_page_config(page_title="AI 量化交易系統 - 多券商版", layout="wide")
st.title("🤖 7合1 量化分析 + 多券商交易系統")
st.caption(f"更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ==========================================
# 券商 Adapter 抽象層
# ==========================================
class BrokerAdapter:
    """券商統一介面（所有券商都要跟呢個格式）"""
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        raise NotImplementedError
    
    def get_account_info(self):
        raise NotImplementedError
    
    def get_positions(self):
        raise NotImplementedError
    
    def get_order_status(self, order_id):
        raise NotImplementedError

# ---------- 富途牛牛 Adapter ----------
class FutuAdapter(BrokerAdapter):
    def __init__(self, host="127.0.0.1", port=11111, trade_pwd=None, env="SIMULATE"):
        self.host = host
        self.port = port
        self.trade_pwd = trade_pwd
        self.env = env  # "SIMULATE" 或 "REAL"
        self.connected = False
        
    def connect(self):
        try:
            from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdSide, OrderType
            self.ctx = OpenSecTradeContext(host=self.host, port=self.port)
            if self.trade_pwd:
                ret, data = self.ctx.unlock_trade(self.trade_pwd)
                if ret != RET_OK:
                    st.error(f"富途解鎖失敗：{data}")
                    return False
            self.connected = True
            return True
        except Exception as e:
            st.error(f"富途連線失敗：{e}")
            return False
    
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        from futu import TrdSide, OrderType, TrdEnv, RET_OK
        if not self.connected:
            if not self.connect():
                return {"success": False, "msg": "連線失敗"}
        
        trd_env = TrdEnv.SIMULATE if self.env == "SIMULATE" else TrdEnv.REAL
        trd_side = TrdSide.BUY if side.upper() == "BUY" else TrdSide.SELL
        order_type_enum = OrderType.NORMAL if order_type == "LIMIT" else OrderType.MARKET
        
        try:
            ret, data = self.ctx.place_order(
                price=price or 0,
                qty=qty,
                code=symbol,
                order_type=order_type_enum,
                trd_side=trd_side,
                trd_env=trd_env
            )
            if ret == RET_OK:
                return {"success": True, "order_id": data['order_id'][0], "msg": "訂單已提交"}
            else:
                return {"success": False, "msg": data}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def get_account_info(self):
        # 實作省略，保留功能接口
        return {"broker": "Futu", "status": "Connected" if self.connected else "Disconnected"}
    
    def get_positions(self):
        return []

# ---------- 老虎證券 Adapter ----------
class TigerAdapter(BrokerAdapter):
    def __init__(self, tiger_id=None, private_key=None, env="SIMULATE"):
        self.tiger_id = tiger_id
        self.private_key = private_key
        self.env = env
        self.connected = False
    
    def connect(self):
        try:
            from tigeropen.api import TigerOpenClient
            from tigeropen.common.consts import Language
            self.client = TigerOpenClient(self.tiger_id, self.private_key, Language.zh_CN)
            self.connected = True
            return True
        except Exception as e:
            st.error(f"老虎連線失敗：{e}")
            return False
    
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        if not self.connected:
            if not self.connect():
                return {"success": False, "msg": "連線失敗"}
        try:
            from tigeropen.trade.order import Order
            from tigeropen.common.consts import OrderStatus, OrderSide, OrderType as TigerOrderType
            order = Order(
                symbol=symbol,
                quantity=qty,
                side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
                order_type=TigerOrderType.LMT if order_type == "LIMIT" else TigerOrderType.MKT,
                limit_price=price or 0
            )
            resp = self.client.place_order(order)
            if resp and resp.order_id:
                return {"success": True, "order_id": resp.order_id, "msg": "訂單已提交"}
            return {"success": False, "msg": str(resp)}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def get_account_info(self):
        return {"broker": "Tiger", "status": "Connected" if self.connected else "Disconnected"}
    
    def get_positions(self):
        return []

# ---------- 長橋 Adapter ----------
class LongPortAdapter(BrokerAdapter):
    def __init__(self, app_key=None, app_secret=None, env="SIMULATE"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.env = env
        self.connected = False
    
    def connect(self):
        try:
            from longport.openapi import Config, TradeContext
            config = Config(self.app_key, self.app_secret)
            self.ctx = TradeContext(config)
            self.connected = True
            return True
        except Exception as e:
            st.error(f"長橋連線失敗：{e}")
            return False
    
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        if not self.connected:
            if not self.connect():
                return {"success": False, "msg": "連線失敗"}
        try:
            from longport.openapi import SubmitOrderOptions, OrderSide, OrderType as LPOrderType
            options = SubmitOrderOptions(
                symbol=symbol,
                quantity=qty,
                side=OrderSide.Buy if side.upper() == "BUY" else OrderSide.Sell,
                order_type=LPOrderType.LO if order_type == "LIMIT" else LPOrderType.MO,
                price=price or 0
            )
            resp = self.ctx.submit_order(options)
            if resp and resp.order_id:
                return {"success": True, "order_id": resp.order_id, "msg": "訂單已提交"}
            return {"success": False, "msg": str(resp)}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def get_account_info(self):
        return {"broker": "LongPort", "status": "Connected" if self.connected else "Disconnected"}
    
    def get_positions(self):
        return []

# ---------- IBKR Adapter ----------
class IBKRAdapter(BrokerAdapter):
    def __init__(self, host="127.0.0.1", port=7497, client_id=1, env="SIMULATE"):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.env = env
        self.connected = False
    
    def connect(self):
        try:
            from ib_async import IB
            self.ib = IB()
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            return True
        except Exception as e:
            st.error(f"IBKR 連線失敗：{e}")
            return False
    
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        if not self.connected:
            if not self.connect():
                return {"success": False, "msg": "連線失敗"}
        try:
            from ib_async import Stock, LimitOrder, MarketOrder
            contract = Stock(symbol, 'SMART', 'USD')
            if order_type == "LIMIT":
                order = LimitOrder(side.upper(), qty, price or 0)
            else:
                order = MarketOrder(side.upper(), qty)
            trade = self.ib.placeOrder(contract, order)
            return {"success": True, "order_id": trade.order.orderId, "msg": "訂單已提交"}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def get_account_info(self):
        return {"broker": "IBKR", "status": "Connected" if self.connected else "Disconnected"}
    
    def get_positions(self):
        return []

# ---------- Alpaca Adapter ----------
class AlpacaAdapter(BrokerAdapter):
    def __init__(self, api_key=None, secret_key=None, env="SIMULATE"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.env = env
        self.connected = False
    
    def connect(self):
        try:
            from alpaca.trading.client import TradingClient
            self.client = TradingClient(self.api_key, self.secret_key, paper=self.env == "SIMULATE")
            self.connected = True
            return True
        except Exception as e:
            st.error(f"Alpaca 連線失敗：{e}")
            return False
    
    def place_order(self, symbol, qty, side, order_type="LIMIT", price=None):
        if not self.connected:
            if not self.connect():
                return {"success": False, "msg": "連線失敗"}
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            if order_type == "LIMIT":
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
                    time_in_force=TimeInForce.GTC,
                    limit_price=price or 0
                )
            else:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
            resp = self.client.submit_order(order_data)
            return {"success": True, "order_id": resp.id, "msg": "訂單已提交"}
        except Exception as e:
            return {"success": False, "msg": str(e)}
    
    def get_account_info(self):
        return {"broker": "Alpaca", "status": "Connected" if self.connected else "Disconnected"}
    
    def get_positions(self):
        return []

# ==========================================
# 券商工廠（用家揀邊間就 return 邊間）
# ==========================================
def get_broker(broker_name, config):
    """根據用家選擇，回傳對應嘅 Adapter"""
    if broker_name == "富途牛牛":
        return FutuAdapter(
            host=config.get("host", "127.0.0.1"),
            port=config.get("port", 11111),
            trade_pwd=config.get("trade_pwd"),
            env=config.get("env", "SIMULATE")
        )
    elif broker_name == "老虎證券":
        return TigerAdapter(
            tiger_id=config.get("tiger_id"),
            private_key=config.get("private_key"),
            env=config.get("env", "SIMULATE")
        )
    elif broker_name == "長橋":
        return LongPortAdapter(
            app_key=config.get("app_key"),
            app_secret=config.get("app_secret"),
            env=config.get("env", "SIMULATE")
        )
    elif broker_name == "IBKR":
        return IBKRAdapter(
            host=config.get("host", "127.0.0.1"),
            port=config.get("port", 7497),
            client_id=config.get("client_id", 1),
            env=config.get("env", "SIMULATE")
        )
    elif broker_name == "Alpaca":
        return AlpacaAdapter(
            api_key=config.get("api_key"),
            secret_key=config.get("secret_key"),
            env=config.get("env", "SIMULATE")
        )
    else:
        return None

# ==========================================
# 技術分析函數
# ==========================================
def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_stock(ticker, period="6mo"):
    data = yf.download(ticker, period=period, interval="1d", progress=False)
    if data.empty:
        return None
    
    # RSI
    rsi = compute_rsi(data)
    
    # MACD
    exp12 = data['Close'].ewm(span=12, adjust=False).mean()
    exp26 = data['Close'].ewm(span=26, adjust=False).mean()
    macd = exp12 - exp26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    
    # 均線
    sma20 = data['Close'].rolling(20).mean()
    sma50 = data['Close'].rolling(50).mean()
    
    # 布林帶
    bb_mid = data['Close'].rolling(20).mean()
    bb_std = data['Close'].rolling(20).std()
    bb_upper = bb_mid + (bb_std * 2)
    bb_lower = bb_mid - (bb_std * 2)
    
    # 最新值
    latest = {
        'price': float(data['Close'].iloc[-1]),
        'rsi': float(rsi.iloc[-1]),
        'macd': float(macd.iloc[-1]),
        'macd_signal': float(macd_signal.iloc[-1]),
        'sma20': float(sma20.iloc[-1]),
        'sma50': float(sma50.iloc[-1]),
        'bb_upper': float(bb_upper.iloc[-1]),
        'bb_lower': float(bb_lower.iloc[-1]),
        'data': data
    }
    latest['macd_diff'] = latest['macd'] - latest['macd_signal']
    
    # 評分
    score = 0
    signals = []
    
    if latest['rsi'] < 30:
        score += 1
        signals.append("超賣")
    elif latest['rsi'] > 70:
        score -= 1
        signals.append("超買")
    else:
        signals.append("中性")
    
    if latest['macd_diff'] > 0:
        score += 1
        signals.append("MACD轉強")
    else:
        score -= 1
        signals.append("MACD轉弱")
    
    if latest['price'] > latest['sma20']:
        score += 1
    if latest['price'] > latest['sma50']:
        score += 1
    
    if latest['price'] < latest['bb_lower']:
        score += 1
        signals.append("跌破下軌")
    elif latest['price'] > latest['bb_upper']:
        score -= 1
        signals.append("突破上軌")
    
    if score >= 2:
        trend = "🔥 偏向買入"
    elif score <= -2:
        trend = "⚠️ 偏向賣出"
    else:
        trend = "⏸️ 中性持有"
    
    latest['score'] = score
    latest['trend'] = trend
    latest['signals'] = ', '.join(signals)
    
    return latest

# ==========================================
# 主畫面
# ==========================================

# ---------- Sidebar：券商設定 ----------
with st.sidebar:
    st.header("🏦 券商設定")
    
    # 可選券商清單
    broker_list = ["富途牛牛", "老虎證券", "長橋", "IBKR", "Alpaca"]
    selected_broker = st.selectbox("選擇券商", broker_list)
    
    # 交易環境
    trade_env = st.selectbox("交易環境", ["SIMULATE (模擬)", "REAL (真實)"])
    env = "SIMULATE" if "SIMULATE" in trade_env else "REAL"
    
    st.divider()
    st.subheader("🔑 API 憑證")
    st.caption("請輸入你嘅券商 API 憑證（不會儲存）")
    
    # 根據不同券商顯示不同設定
    if selected_broker == "富途牛牛":
        host = st.text_input("OpenD Host", "127.0.0.1")
        port = st.number_input("OpenD Port", value=11111)
        trade_pwd = st.text_input("交易密碼", type="password")
        broker_config = {"host": host, "port": port, "trade_pwd": trade_pwd, "env": env}
        
    elif selected_broker == "老虎證券":
        tiger_id = st.text_input("Tiger ID")
        private_key = st.text_area("Private Key", height=100)
        broker_config = {"tiger_id": tiger_id, "private_key": private_key, "env": env}
        
    elif selected_broker == "長橋":
        app_key = st.text_input("App Key")
        app_secret = st.text_input("App Secret", type="password")
        broker_config = {"app_key": app_key, "app_secret": app_secret, "env": env}
        
    elif selected_broker == "IBKR":
        host = st.text_input("Gateway Host", "127.0.0.1")
        port = st.number_input("Gateway Port", value=7497)
        client_id = st.number_input("Client ID", value=1)
        broker_config = {"host": host, "port": port, "client_id": client_id, "env": env}
        
    elif selected_broker == "Alpaca":
        api_key = st.text_input("API Key")
        secret_key = st.text_input("Secret Key", type="password")
        broker_config = {"api_key": api_key, "secret_key": secret_key, "env": env}
    
    # 連線測試按鈕
    if st.button("🔗 測試連線"):
        broker = get_broker(selected_broker, broker_config)
        if broker:
            with st.spinner("連線中..."):
                result = broker.connect()
                if result:
                    st.success(f"✅ {selected_broker} 連線成功！")
                else:
                    st.error(f"❌ {selected_broker} 連線失敗，請檢查憑證")

# ---------- 主畫面：股票分析 ----------
col1, col2 = st.columns([2, 1])

with col1:
    ticker = st.text_input("輸入股票代號", value="TSLA").upper()
    period = st.selectbox("數據週期", ["1mo", "3mo", "6mo", "1y"], index=2)

with col2:
    st.write("")
    st.write("")
    analyze_btn = st.button("🚀 分析", use_container_width=True)

# ---------- 分析結果 ----------
if analyze_btn and ticker:
    with st.spinner("分析中..."):
        result = analyze_stock(ticker, period)
        
        if result is None:
            st.error("無法獲取數據，請檢查股票代號")
            st.stop()
        
        # 顯示主要指標
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最新價格", f"${result['price']:.2f}")
        col2.metric("RSI (14天)", f"{result['rsi']:.1f}", 
                    delta="超買" if result['rsi'] > 70 else "超賣" if result['rsi'] < 30 else "中性")
        col3.metric("MACD差額", f"{result['macd_diff']:.2f}")
        col4.metric("綜合信號", result['trend'])
        
        st.divider()
        
        # 詳細指標
        st.subheader("📊 詳細指標")
        c1, c2, c3 = st.columns(3)
        c1.write(f"**SMA20**：${result['sma20']:.2f}")
        c1.write(f"**SMA50**：${result['sma50']:.2f}")
        c2.write(f"**布林上軌**：${result['bb_upper']:.2f}")
        c2.write(f"**布林下軌**：${result['bb_lower']:.2f}")
        c3.write(f"**信號標籤**：{result['signals']}")
        c3.write(f"**綜合評分**：{result['score']}")
        
        # 圖表
        st.subheader("📈 走勢圖")
        fig, ax = plt.subplots(figsize=(12, 5))
        data = result['data']
        ax.plot(data.index, data['Close'], label='價格', color='black')
        ax.plot(data.index, data['Close'].rolling(20).mean(), label='SMA20', linestyle='--', color='blue')
        ax.plot(data.index, data['Close'].rolling(50).mean(), label='SMA50', linestyle='--', color='orange')
        
        # 布林帶
        bb_mid = data['Close'].rolling(20).mean()
        bb_std = data['Close'].rolling(20).std()
        ax.fill_between(data.index, bb_mid - (bb_std * 2), bb_mid + (bb_std * 2), alpha=0.1, color='gray')
        
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_title(f'{ticker} 技術分析圖')
        st.pyplot(fig)
        
        # ---------- 交易執行區 ----------
        st.divider()
        st.subheader("💹 交易執行")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            qty = st.number_input("買入股數", min_value=1, value=10)
            
        with col2:
            order_type = st.selectbox("訂單類型", ["LIMIT (限價單)", "MARKET (市價單)"])
            is_limit = "LIMIT" in order_type
            
        with col3:
            if is_limit:
                price = st.number_input("限價 ($)", min_value=0.01, value=result['price'], format="%.2f")
            else:
                price = None
                st.info("市價單將以當前市場價格成交")
        
        # 交易按鈕（只允許在買入信號時顯示）
        if "買入" in result['trend']:
            if st.button(f"📈 買入 {ticker} ({qty}股)", type="primary", use_container_width=True):
                # 獲取券商 Adapter
                broker = get_broker(selected_broker, broker_config)
                if broker:
                    with st.spinner(f"正在透過 {selected_broker} 下單..."):
                        # 連接
                        if not broker.connected:
                            broker.connect()
                        
                        # 執行下單
                        order_result = broker.place_order(
                            symbol=ticker,
                            qty=qty,
                            side="BUY",
                            order_type="LIMIT" if is_limit else "MARKET",
                            price=price
                        )
                        
                        if order_result['success']:
                            st.success(f"✅ 訂單已提交！訂單號：{order_result.get('order_id', 'N/A')}")
                            st.info(f"📌 {selected_broker} 環境：{env}")
                        else:
                            st.error(f"❌ 下單失敗：{order_result.get('msg', '未知錯誤')}")
                else:
                    st.error("❌ 無法連接券商，請檢查設定")
        else:
            st.info("⏸️ 當前信號為「中性」或「賣出」，不觸發買入交易")

# ---------- Footer ----------
st.divider()
st.caption("⚠️ 免責聲明：本系統僅供參考，不構成投資建議。所有交易風險自負。")
st.caption(f"🚀 支援券商：{', '.join(broker_list)} | 環境：{env}")