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
        logger.error(error)

    def on_close(ws):
        logger.info('closed')

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
        logger.error(error)

    def on_close(ws):
        logger.info('closed')

    def on_open(ws):
        action()

    trade_ws = websocket.WebSocketApp("wss://ws-fapi.binance.com/ws-fapi/v1",
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
    trade_ws.on_open = on_open

    trade_ws.run_forever()


def orderbook_stream():
    global orderbook_ws

    def on_error(ws, error):
        logger.error(error)

    def on_close(ws):
        logger.info('closed')


    orderbook_ws = websocket.WebSocketApp(f"wss://ws-fapi.binance.com/ws-fapi/v1",
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_open = on_open
    
    orderbook_ws.run_forever()

action_orderid = {}
orderid_action ={}
orderid_detail = {}


condition = threading.Condition()

orderbook = None


def get_orderbook():

    global orderbook_ws, condition, orderbook


    def on_message(ws, message):
        with condition:
            global orderbook
            orderbook = message
            condition.notify()



    orderbook_ws.on_message = on_message


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
    orderbook_ws.send(json.dumps(payload))
    
    with condition:
        condition.wait()
        orderbook_obj = json.loads(orderbook)
        return [
            float(orderbook_obj['result']['bids'][-1][0]), 
            float(orderbook_obj['result']['asks'][-1][0])
        ]


current_action = 0

def create_order(newClientOrderId, positionSide, stopPrice, price, side, type, quantity):
    logger.warn(f'newClientOrderId: {newClientOrderId}, positionSide: {positionSide}, stopPrice: {stopPrice}, price: {price}, side: {side}, type: {type}')
    timestamp = int(time.time()) * 1000
    params = {
        "apiKey": api_key,
        "newClientOrderId": newClientOrderId,
        "newOrderRespType": "RESULT",
        "positionSide": positionSide,
        "price": price,

        "quantity": quantity,
        "side": side,
        "symbol": "1000PEPEUSDC",
        "timeInForce": "GTC",
        "timestamp": timestamp,
        "type": type,
        "stopPrice": stopPrice,
        
    }

    params = sorted(params.items())

    params = {k: v for k, v in params}

    params['signature'] = hashing(urlencode(params))

    # 构建要发送的 JSON 数据
    payload = {
        "id": newClientOrderId,
        "method": "order.place",
        "params": params,
    }
    trade_ws.send(json.dumps(payload))


def action():
    [low_bid, high_ask] = get_orderbook()
    global current_action
    current_action += 1
    args = [
        [f'{current_action}-6', 'LONG', high_ask, round(high_ask * 1.002, 7), 'SELL', 'TAKE_PROFIT', int(5.5/high_ask)],
        [f'{current_action}-5', 'LONG', high_ask, high_ask, 'BUY', 'STOP', int(5.5/high_ask)],
        [f'{current_action}-4', 'LONG', high_ask, round(high_ask * 0.998, 7), 'SELL', 'TAKE_PROFIT', int(5.5/high_ask)],

        [f'{current_action}-3', 'SHORT', low_bid, round(low_bid * 1.002, 7), 'SELL', 'STOP', int(5.5/low_bid)],
        [f'{current_action}-2', 'SHORT', low_bid, low_bid, 'BUY', 'TAKE_PROFIT', int(5.5/low_bid)],
        [f'{current_action}-1', 'SHORT', low_bid, round(low_bid * 0.998, 7), 'SELL', 'STOP', int(5.5/low_bid)],

    ]
    for arg in args:
        create_order(*arg)
    


if __name__ == "__main__":
    t_account_stream = threading.Thread(target=account_stream, name='账户监听')
    # t_account_stream.start()

    t_trade_stream = threading.Thread(target=trade_stream, name='交易执行')
    t_trade_stream.start()

    t_orderbook_stream = threading.Thread(target=orderbook_stream, name='订单簿')
    t_orderbook_stream.start()
