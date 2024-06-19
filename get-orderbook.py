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
import math
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

trade_ws = None


condition = threading.Condition()



def trade_stream():
    global trade_ws

    def on_message(ws, message):
        logger.info(f"[red]{message}[/]", extra={"markup": True})

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")

    trade_ws = websocket.WebSocketApp("wss://ws-fapi.binance.com/ws-fapi/v1",
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

    trade_ws.run_forever()

orderbook = None

def func(orderbook_):
    orderbook = json.loads(orderbook_)
    _1 = float(orderbook['result']['bids'][0][0])
    _2 = float(orderbook['result']['bids'][-1][0])

    _3 = float(orderbook['result']['asks'][0][0])
    _4 = float(orderbook['result']['asks'][-1][0])

    # print([abs((_1 - _2 )/ _1),  abs((_3 - _4 )/ _3)])
    print(orderbook)


def get_orderbook(func):

    global trade_ws, condition, orderbook


    def on_message(ws, message):
        with condition:
            global orderbook
            orderbook = message
            condition.notify()



    trade_ws.on_message = on_message


    # 构建要发送的 JSON 数据
    payload = {
        "id": "51e2affb-0aba-4821-ba75-f2625006eb43",
        "method": "depth",
        "params": {
            "symbol": "1000PEPEUSDT",
            "limit": 100
        }
    }

    # 将 JSON 数据转换为字符串并发送
    trade_ws.send(json.dumps(payload))
    
    with condition:
        condition.wait()
        func(orderbook)


def thread2():
    time.sleep(2)
    for i in range(1):
        get_orderbook(func)

if __name__ == "__main__":
    t1 = threading.Thread(target=trade_stream)
    t2 = threading.Thread(target=thread2)

    t1.start()
    t2.start()