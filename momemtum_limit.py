# 由于动量策略无法挂限价单，目前有两套方案： 在价格达到目标点位时，下一个稍微亏损的限价单，等待瞬时回撤将他成交； 另一个方案是直接市价买卖。这里就先采用方案1.

import threading
import time
from typing import List, Literal, Optional
from rich.console import Console
from rich.logging import RichHandler
import logging
import websocket
from typing import Type
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
import pickle
import copy
# 加载 .env 文件中的环境变量
dotenv_path = '.env'
load_dotenv(dotenv_path)

# 从环境变量中获取 API Key 和 API Secret
api_key = os.getenv('api_key')
api_secret = os.getenv('api_secret')

file_handler = logging.FileHandler('log.log', mode='a')
# 配置 logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(), file_handler]
)


def hashing(query_string):
    return hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

account_ws = None
trade_ws = None
price_ws = None

class Army():
    def __init__(self):
        self.current_total_gain = 0
        self.teams: List[Type['Team']] = []
        self.create_team()
        logging.info('创建了 Team ')
    
    def create_team(self):
        self.teams.append(Team(self))
    
    def start(self):
        logging.info(f'初始钱包余额{wallet_stream_instance.get_balance()}')
        while True:
            if wallet_stream_instance.get_balance() > 30:
                for team in self.teams:
                    team.check_timeout()
            else:
                logging.warn('保证金不足')
            with open('army.pkl', 'wb') as f:
                pickle.dump(copy.deepcopy(self), f)
            time.sleep(10)


class Team():
    def __init__(self, army):
        self.army: Army = None
        self.workers: List[Type['OrderWorker']] = []
        self.army = army
        
        self.create_worker()
    
    def create_worker(self):
        if wallet_stream_instance.get_balance():
            worker = OrderWorker(self)
            self.workers.append(worker)
            logging.info(f'创建了 worker {worker.timestamp}')
    
    def check_timeout(self):
        if self.workers[-1]:
            worker = self.workers[-1]
            
            match worker.status:
                case None:
                    if int(time.time_ns() / 10**6) - worker.timestamp > 20 * 1000:
                        worker.cleanup('timeout_to_fill')
                case 'opened':
                    if int(time.time_ns() / 10**6) - worker.opened_time > 10 * 1000:
                        worker.cleanup('timeout_to_close')


class OrderWorker():
    def __init__(self, team: Team):
        self.order_ids = {}
        self.trigger = 0.0003
        self.trigger_drawback = 0.00002
        self.gain = self.trigger - self.trigger_drawback + 0.0002 + 0.0002 + 0.0005
        self.stop_loss = 0.003
        self.team = team
        self.status: Optional[Literal[None, "opened", "closed", "timeout_to_fill", "timeout_to_close"]] = None 
        self.baseline_price = get_price()
        self.timestamp = int(time.time_ns() / 10**6)
        
        value_per_position = 15
        self.order_consts = {
            'open-long-mid': [f'{self.timestamp}-open-long-mid', 'LONG', round(self.baseline_price * (1 + self.trigger), 7), round(self.baseline_price * (1 + self.trigger - self.trigger_drawback), 7), 'BUY', 'STOP', int(value_per_position/self.baseline_price)],
            'close-long-high': [f'{self.timestamp}-close-long-high', 'LONG', 0, round(self.baseline_price * (1 + self.gain), 7), 'SELL', 'LIMIT', int(value_per_position/self.baseline_price)],
            'close-long-low': [f'{self.timestamp}-close-long-low', 'LONG', round(self.baseline_price * (1 - self.stop_loss), 7), 0, 'SELL', 'STOP_MARKET', int(value_per_position/self.baseline_price)],
            'close-long-market': [f'{self.timestamp}-close-long-market', 'LONG', 0, 0, 'SELL', 'MARKET', int(value_per_position/self.baseline_price)],
            
            'open-short-mid': [f'{self.timestamp}-open-short-mid', 'SHORT', round(self.baseline_price * (1 - self.trigger), 7), round(self.baseline_price * (1 - self.trigger + self.trigger_drawback), 7),  'SELL', 'STOP', int(value_per_position/self.baseline_price)],
            'close-short-low': [f'{self.timestamp}-close-short-low', 'SHORT', 0, round(self.baseline_price * (1- self.gain ), 7), 'BUY', 'LIMIT', int(value_per_position/self.baseline_price)],
            'close-short-high': [f'{self.timestamp}-close-short-high', 'SHORT',round(self.baseline_price * (1 + self.stop_loss), 7), 0, 'BUY', 'STOP_MARKET', int(value_per_position/self.baseline_price)],
            'close-short-market': [f'{self.timestamp}-close-short-market', 'SHORT', 0, 0, 'BUY', 'MARKET', int(value_per_position/self.baseline_price)]
        }
        self.direction = None # None long short
        self.opened_time = None
        account_stream_instance.subscribe(self)
        self.start()
    def start(self):
        for key_ in [ 'open-long-mid', 'open-short-mid']:
            create_order(*(self.order_consts[key_]))
        logging.info(f'{self.timestamp} 工人启动')
    
    def update(self, msg):
        client_order_id = msg['o']['c']
        order_timestamp, open_or_close, long_or_short, high_or_low = client_order_id.split('-')
        if not int(order_timestamp) == self.timestamp:
            return

        if msg['o']['X'] == 'NEW':
            self.order_ids[client_order_id] = msg['o']['i']
        
        if msg['o']['X'] == 'FILLED':
            self.opened_time = int(msg['o']['T'])
            match f'{open_or_close}-{long_or_short}-{high_or_low}':
                case 'open-long-mid':
                    self.status = 'opened'
                    self.direction = 'long'
                    create_order(*(self.order_consts['close-long-high']))
                    create_order(*(self.order_consts['close-long-low']))
                    cancel_order(f'{self.timestamp}-open-short-mid')
                case 'open-short-mid':
                    self.status = 'opened'
                    self.direction = 'short'
                    create_order(*(self.order_consts['close-short-low']))
                    create_order(*(self.order_consts['close-short-high']))
                    cancel_order(f'{self.timestamp}-open-long-mid')
                case _:
                    self.cleanup('closed')
    
    def cleanup(self, status):
        self.status = status
        print(status)
        match status:
            case 'closed':
                self.calculate_total_profit()
                self.cancel_rest_orders()
                account_stream_instance.unsubscribe(self)
                self.team.create_worker()
            case 'timeout_to_fill':
                self.cancel_rest_orders()
                account_stream_instance.unsubscribe(self)
                self.team.create_worker()

            case 'timeout_to_close':
                create_order(*self.order_consts[f'close-{self.direction}-market'])

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
        total_profit = 0
        for order in all_orders:
            if order['orderId'] in self.order_ids.values():
                total_realized_pnl += float(order['realizedPnl'])
                total_commission += float(order['commission'])
                
                total_profit = total_realized_pnl - total_commission
        
        with open('gain.txt', 'a+') as f:
            f.write(f'{self.timestamp} 收益: {total_profit} \n')
            logging.info(f'{self.timestamp} 收益: {total_profit} \n')
        
        self.team.army.current_total_gain += total_profit
        logging.info(f'{self.timestamp} 当前总收益 {self.team.army.current_total_gain}')

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
                logging.info(f'canceld {order["clientOrderId"]}')
                cancel_order(order['clientOrderId'])

        

class AccountWS:
    def __init__(self):
        global account_ws
        self.observers:List[OrderWorker] = []

        self.listen_key = ''
        BASE_URL = 'https://fapi.binance.com'

        self.url = f'{BASE_URL}/fapi/v1/listenKey'
        self.headers = {
            'X-MBX-APIKEY': api_key
        }
        response = requests.post(self.url, headers=self.headers)
        if response.status_code == 200:
            self.listen_key = response.json()['listenKey']

        
        account_ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/{self.listen_key}",
                                    on_message=self.on_message,
                                    on_error=logging.error,
                                    )

    def subscribe(self, observer):
        self.observers.append(observer)

    def unsubscribe(self, observer):
        self.observers.remove(observer)

    def notify(self, message):
        for observer in self.observers:
            observer.update(message)

    def on_message(self, ws, message):
        logging.info(message)
        msg = json.loads(message)
        if msg['e'] == 'ORDER_TRADE_UPDATE':        
            self.notify(msg)

    def run(self):
        global account_ws
        account_ws.run_forever()

    def update_listen_key(self):
        while True:
            time.sleep(1200)
            requests.put(self.url, headers=self.headers)


class WalletWS():
    wallet_ws = ws = websocket.WebSocketApp('wss://ws-fapi.binance.com/ws-fapi/v1')
    condition = threading.Condition()
    current_price = None
    
    def __init__(self):
        pass
    def get_balance(self):
        def on_message(ws, message):
            with self.condition:
                # logging.info(json.loads(message)['result']['assets'])
                self.current_price = float([ass['availableBalance'] for ass in json.loads(message)['result']['assets'] if ass['asset'] == 'USDC'][0])
                self.condition.notify()
        self.wallet_ws.on_message = on_message
        
        timestamp = int(time.time_ns() / 10**6)
        params = {
            "apiKey": api_key,
            "timestamp": timestamp
            
        }
        params = sorted(params.items())

        params = {k: v for k, v in params}

        params['signature'] = hashing(urlencode(params))

        # 构建要发送的 JSON 数据
        payload = {
            "id": timestamp,
            "method": "account.status",
            "params": params,
        }
        self.wallet_ws.send(json.dumps(payload))
        
        with self.condition:
            self.condition.wait()
            return self.current_price

    def run(self):
        self.wallet_ws.run_forever()

def trade_stream():
    global trade_ws

    def on_message(ws, message):
        logging.info(message)
        msg = json.loads(message)
        if not msg['status'] == 200:
            logging.error(f'这个下单发生了错误 {msg}')
        


    def on_error(ws, error):
        logging.error(error)

    def on_close(ws):
        logging.info('closed')


    trade_ws = websocket.WebSocketApp("wss://ws-fapi.binance.com/ws-fapi/v1",
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

    trade_ws.run_forever()

def price_stream():
    global price_ws
    def on_error(ws, error):
        logging.error(error)

    def on_close(ws):
        logging.info('closed')


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
    global trade_ws
    # logging.warn(f'newClientOrderId: {newClientOrderId}, positionSide: {positionSide}, stopPrice: {stopPrice}, price: {price}, side: {side}, type: {type}')
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

    if type == 'MARKET':
        del params['timeInForce']
    
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
    global trade_ws
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

if __name__ == "__main__":
    
    from datetime import datetime
    logging.info(datetime.now().strftime("%H:%M:%S"))

    account_stream_instance = AccountWS()
    t_account_stream = threading.Thread(target=account_stream_instance.run, name='账户监听')
    t_account_stream.start()
    
    t_update_listenkey = threading.Thread(target=account_stream_instance.update_listen_key, name='更新listenkey')
    t_update_listenkey.start()
    
    t_price_stream = threading.Thread(target=price_stream, name='订单簿')
    t_price_stream.start()

    t_trade_stream = threading.Thread(target=trade_stream, name='交易执行')
    t_trade_stream.start()

    wallet_stream_instance = WalletWS()
    t_wallet_stream = threading.Thread(target=wallet_stream_instance.run, name='余额监控')
    t_wallet_stream.start()
    
    time.sleep(3)
    
    army = Army()
    t_worker_thread = threading.Thread(target=army.start, name = '军队')
    t_worker_thread.start()
