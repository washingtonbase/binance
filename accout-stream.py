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

# Binance REST API Base URL
BASE_URL = 'https://fapi.binance.com'

# 创建 listen key 的函数
def create_listen_key(api_key):
    url = f'{BASE_URL}/fapi/v1/listenKey'
    headers = {
        'X-MBX-APIKEY': api_key
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()['listenKey']
    else:
        print(f"Failed to create listen key: {response.status_code}, {response.text}")
        return None

# 订阅账户数据流的函数
def subscribe_account_data_stream(listen_key):
    def on_message(ws, message):
        print(f"Received message: {message}")

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")

    ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/{listen_key}",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_open = on_open
    ws.run_forever()

if __name__ == "__main__":
    # 创建 listen key
    listen_key = create_listen_key(api_key)
    if listen_key:
        print(f"Created listen key: {listen_key}")

        # 订阅账户数据流
        subscribe_account_data_stream(listen_key)
    else:
        print("Failed to create listen key.")
