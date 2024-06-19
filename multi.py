import threading
import time
from rich.console import Console
from rich.logging import RichHandler
import logging
import websocket

import requests
import websocket
import json
import time
import os
from dotenv import load_dotenv
from urllib.parse import urlencode
import hmac
import hashlib

# 加载 .env 文件中的环境变量
dotenv_path = '.env'
load_dotenv(dotenv_path)

# 从环境变量中获取 API Key 和 API Secret
api_key = os.getenv('api_key')
api_secret = os.getenv('api_secret')

# 配置 logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
    handlers=[RichHandler()]
)
logger = logging.getLogger('rich')


def hashing(query_string):
    return hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

accout_ws = None
trade_ws = None
orderbook_ws = None
# 订阅账户数据流的函数
def account_stream():
    listen_key = ''
    BASE_URL = 'https://fapi.binance.com'

    url = f'{BASE_URL}/fapi/v1/listenKey'
    headers = {
        'X-MBX-APIKEY': api_key
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        listen_key = response.json()['listenKey']


    def on_message(ws, message):
        logger.info(f"[blue]{message}[/]", extra={"markup": True})

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")

    global accout_ws
    accout_ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/{listen_key}",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    accout_ws.run_forever()

def trade_stream():
    global trade_ws

    def on_message(ws, message):
        logger.info(f"[red]{message}[/]", extra={"markup": True})

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")

    def on_open(ws):
        print("Connection established")
        
        timestamp = int(time.time()) * 1000
        price = 0.01164
        
        params = {
            "apiKey": api_key,
            "newClientOrderId": "fuckyou2",
            "newOrderRespType": "RESULT",
            "positionSide": "LONG",
            "price": price,

            "quantity": int(5.1 / price),
            "side": "BUY",
            "symbol": "1000PEPEUSDC",
            "timeInForce": "GTC",
            "timestamp": timestamp,
            "type": "STOP",
            "stopPrice": price,
            
        }

        params = sorted(params.items())

        params = {k: v for k, v in params}

        params['signature'] = hashing(urlencode(params))

        # 构建要发送的 JSON 数据
        payload = {
            "id": 'supoerman',
            "method": "order.place",
            "params": params,
        }
        
    
        # 将 JSON 数据转换为字符串并发送
        trade_ws.send(json.dumps(payload))

    trade_ws = websocket.WebSocketApp("wss://ws-fapi.binance.com/ws-fapi/v1",
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
    trade_ws.on_open = on_open

    trade_ws.run_forever()




def orderbook_stream():
    global orderbook_ws

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")


    orderbook_ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/1000pepeusdc@depth10@100ms",
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_open = on_open
    
    orderbook_ws.run_forever()


def get_current_orderbook():
    payload = {
        "id": "none",
        "method": "depth",
        "params": {
            "symbol": "1000PEPEUSDC"
        }
    }

    # 将 JSON 数据转换为字符串并发送
    trade_ws.send(json.dumps(payload))
    


action_orderid = {}
orderid_action ={}
orderid_detail = {}



if __name__ == "__main__":
    t_account_stream = threading.Thread(target=account_stream, name='账户监听')
    t_account_stream.start()

    t_trade_stream = threading.Thread(target=trade_stream, name='交易执行')
    t_trade_stream.start()

    t_orderbook_stream = threading.Thread(target=orderbook_stream, name='订单簿')
    t_orderbook_stream.start()
