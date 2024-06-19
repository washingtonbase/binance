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


# 订阅账户数据流的函数
def subscribe_account_data_stream():
    def on_message(ws, message):
        print(f"Received message: {message}")

    def on_error(ws, error):
        print(f"Error: {error}")

    def on_close(ws):
        print("Connection closed")

    ws = websocket.WebSocketApp(f"wss://fstream.binance.com/ws/1000pepeusdc@depth10@100ms",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    # ws.on_open = on_open
    ws.run_forever()

if __name__ == "__main__":

    websocket.enableTrace(False)
    subscribe_account_data_stream()
