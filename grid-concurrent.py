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
import os
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
price_ws = None

    
class OrderWorkder():
    baseline_price = -1
    timestamp = -1
    orders = {}
    order_consts = {}
    gain = 0.0008
    stop_loss = 0.03
    order_ids = {}
    
    def __init__(self):
        self.baseline_price = get_price()
        self.timestamp = int(time.time_ns() / 10**6)
        self.orders = {
                'open-long-mid': False,
                'close-long-high': False,
                'close-long-low': False,
            
                'open-short-mid': False,
                'close-short-high': False,
                'close-short-low': False,
                'ended': False
            }
        
        self.order_consts = {
            'open-long-mid': [f'{self.timestamp}-open-long-mid', 'LONG', 0, round(self.baseline_price * (1 - self.gain), 7), 'BUY', 'LIMIT', int(5.5/self.baseline_price)],
            'close-long-high': [f'{self.timestamp}-close-long-high', 'LONG', 0, round(self.baseline_price * (1 ), 7), 'SELL', 'LIMIT', int(5.5/self.baseline_price)],
            'close-long-low': [f'{self.timestamp}-close-long-low', 'LONG', round(self.baseline_price * (1 - self.stop_loss), 7), 0, 'SELL', 'STOP_MARKET', int(5.5/self.baseline_price)],
            
            'open-short-mid': [f'{self.timestamp}-open-short-mid', 'SHORT', 0, round(self.baseline_price * (1 + self.gain), 7),  'SELL', 'LIMIT', int(5.5/self.baseline_price)],
            'close-short-low': [f'{self.timestamp}-close-short-low', 'SHORT', 0, round(self.baseline_price * (1 ), 7), 'BUY', 'LIMIT', int(5.5/self.baseline_price)],
            'close-short-high': [f'{self.timestamp}-close-short-high', 'SHORT',round(self.baseline_price * (1 + self.stop_loss), 7), 0, 'BUY', 'STOP_MARKET', int(5.5/self.baseline_price)]
        }
        
    def start(self):
        for key_ in [ 'open-long-mid', 'open-short-mid']:
            create_order(*(self.order_consts[key_]))
    
    def update(self, msg):
        client_order_id = msg['o']['c']
        order_timestamp, open_or_close, long_or_short, high_or_low = client_order_id.split('-')
        if not int(order_timestamp) == self.timestamp:
            return

        self.orders[f'{open_or_close}-{long_or_short}-{high_or_low}'] = msg['o']['X']

        if msg['o']['X'] == 'NEW':
            self.order_ids[client_order_id] = msg['o']['i']
        
        if msg['o']['X'] == 'FILLED':
            match f'{open_or_close}-{long_or_short}-{high_or_low}':
                case 'open-long-mid':
                    create_order(self.order_consts['close-long-high'])
                    create_order(self.order_consts['close-long-low'])
                    
                case 'open-short-mid':
                    create_order(self.order_consts['close-short-low'])
                    create_order(self.order_consts['close-short-high'])
                    
                case 'close-long-high' | 'close-short-low' | 'close-long-low' | 'close-short-high':
                    self.calculate_total_profit()
                    self.cancel_rest_orders()
                    
        
    def calculate_total_profit(self):
        params = {
            'symbol': '1000PEPEUSDC',
            'startTime': self.timestamp,
            'timestamp': int(time.time_ns() / 10**6)
        }
        
        params['signature'] = hashing(urlencode(params))
        all_orders = requests.get('https://fapi.binance.com/fapi/v1/userTrades', params=params, headers = {
            'X-MBX-APIKEY': api_key
        }).json()
        
        total_realized_pnl = 0
        total_commission = 0
        
        for order in all_orders:
            if order['orderId'] in self.order_ids.keys():
                total_realized_pnl += float(order['realizedPnl'])
                total_commission += float(order['commission'])
                
                total_profit = total_realized_pnl - total_commission
        
        with open('gain.txt', 'a+') as f:
            f.write(f'{self.timestamp} 收益: {total_profit} \n')
            print(f'{self.timestamp} 收益: {total_profit} \n')

        return total_profit

    def cancel_rest_orders(self):
        params = {
            'symbol': '1000PEPEUSDC',
            'timestamp': int(time.time_ns() / 10**6)
        }
        params['signature'] = hashing(urlencode(params))
        open_orders = requests.get('https://fapi.binance.com/fapi/v1/openOrders', params=params, headers = {
            'X-MBX-APIKEY': api_key
        }).json()
        
        for order in open_orders:
            if order['clientOrderId'].startswith(str(self.timestamp)):
                cancel_order(order['clientOrderId'])

def work():
    for i in range(10):
        worker = OrderWorkder()
        
        



class AccountWS:
    def __init__(self):
        self.observers = []

        listen_key = ''
        BASE_URL = 'https://fapi.binance.com'

        url = f'{BASE_URL}/fapi/v1/listenKey'
        headers = {
            'X-MBX-APIKEY': api_key
        }
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            listen_key = response.json()['listenKey']

        global accout_ws
        
        accout_ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/{listen_key}",
                                    on_message=self.on_message,
                                    on_error=print,
                                    )

    def subscribe(self, observer):
        self.observers.append(observer)

    def unsubscribe(self, observer):
        self.observers.remove(observer)

    def notify(self, message):
        for observer in self.observers:
            observer.update(message)

    def on_message(self, ws, message):
        msg = json.loads(message)
        if msg['e'] == 'ORDER_TRADE_UPDATE':        
            self.notify(msg)
    def run(self):
        accout_ws.run_forever()

def trade_stream():
    global trade_ws

    def on_message(ws, message):
        logger.info(f"[red]{message}[/]", extra={"markup": True})
        pass


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


def price_stream():
    global price_ws

    def on_error(ws, error):
        logger.error(error)

    def on_close(ws):
        logger.info('closed')


    price_ws = websocket.WebSocketApp(f"wss://ws-fapi.binance.com/ws-fapi/v1",
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_open = on_open
    
    price_ws.run_forever()

condition = threading.Condition()

price = None


def get_price():

    global price_ws, condition, price


    def on_message(ws, message):
        with condition:
            global price
            price = message
            condition.notify()



    price_ws.on_message = on_message


    # 构建要发送的 JSON 数据
    payload = {
        "id": "51e2affb-0aba-4821-ba75-f2625006eb43",
        "method": "ticker.price",
        "params": {
            "symbol": "1000PEPEUSDC"
        }
    }

    # 将 JSON 数据转换为字符串并发送
    price_ws.send(json.dumps(payload))
    
    with condition:
        condition.wait()
        price_obj = json.loads(price)
        return float(price_obj['result']['price'])



def create_order(newClientOrderId, positionSide, stopPrice, price, side, type, quantity):
    logger.warn(f'newClientOrderId: {newClientOrderId}, positionSide: {positionSide}, stopPrice: {stopPrice}, price: {price}, side: {side}, type: {type}')
    timestamp = int(time.time_ns() / 1000000)
    params = {
        "apiKey": api_key,
        "newClientOrderId": newClientOrderId,
        "newOrderRespType": "RESULT",
        "positionSide": positionSide,

        "quantity": quantity,
        "side": side,
        "symbol": "1000PEPEUSDC",
        "timeInForce": 'GTX' if type == 'LIMIT' else 'GTC',
        "timestamp": timestamp,
        "type": type
        
    }

    if type in ['STOP', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET', 'STOP_MARKET']:
        params['stopPrice'] = stopPrice

    if not type.endswith('MARKET'):
        params['price'] = price

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


def cancel_order(clientOrderId):
    params = {
        "apiKey": api_key,
        "origClientOrderId": clientOrderId,
        "timestamp": int(time.time_ns() / 10**6),
        'symbol': '1000PEPEUSDC'
    }
    params = sorted(params.items())

    params = {k: v for k, v in params}

    params['signature'] = hashing(urlencode(params))
    
    payload = {
        "id": clientOrderId,
        "method": "order.cancel",
        "params": params,
    }
    trade_ws.send(json.dumps(payload))
    

    
def terminate():
    params = {
        'symbol': '1000PEPEUSDC',
        'timestamp': int(time.time_ns() / 10**6),
    }
    
    params['signature'] = hashing(urlencode(params))
    requests.delete('https://fapi.binance.com/fapi/v1/allOpenOrders', params=params, headers = {
        'X-MBX-APIKEY': api_key
    })
    


if __name__ == "__main__":
    from datetime import datetime
    print(datetime.now().strftime("%H:%M:%S"))

    account_stream_instance = AccountWS()
    
    t_account_stream = threading.Thread(target=account_stream_instance.run, name='账户监听')
    t_account_stream.start()
    
    t_price_stream = threading.Thread(target=price_stream, name='订单簿')
    t_price_stream.start()

    t_trade_stream = threading.Thread(target=trade_stream, name='交易执行')
    t_trade_stream.start()
    
    