import websocket
import json
import time
import hmac
import hashlib

import copy
import os
import dotenv
from urllib.parse import urlencode

dotenv.load_dotenv()

api_secret = os.getenv('api_secret')
api_key = os.getenv('api_key')

print(api_key)

def hashing(query_string):
    return hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def on_message(ws, message):
    print(f"Received message: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws):
    print("Connection closed")

def on_open(ws):
    print("Connection established")
    
    timestamp = int(time.time()) * 1000

    params = {
        "apiKey": api_key,
        "timestamp": timestamp
    }

    params['signature'] = hashing(urlencode(params))

    # 构建要发送的 JSON 数据
    payload = {
        "id": timestamp,
        "method": "session.logon",
        "params": params,
    }
    
    # 将 JSON 数据转换为字符串并发送
    ws.send(json.dumps(payload))

    

if __name__ == "__main__":
    websocket.enableTrace(True)  # 开启调试信息，可选

    ws = websocket.WebSocketApp("wss://ws-fapi.binance.com/ws-fapi/v1",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open

    ws.run_forever()
