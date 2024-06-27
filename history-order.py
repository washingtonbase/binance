import requests
import time

import hmac
import hashlib
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
dotenv_path = '.env'
load_dotenv(dotenv_path)

# 从环境变量中获取 API Key 和 API Secret
api_key = os.getenv('api_key')
api_secret = os.getenv('api_secret')


params = {
    'symbol': '1000PEPEUSDC',
    'startTime': 1719473296774,
    'timestamp': int(time.time_ns() / 10**6)
}


def hashing(query_string):
    return hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

params['signature'] = hashing(urlencode(params))

response = requests.get('https://fapi.binance.com/fapi/v1/allOrders', params=params, headers = {
        'X-MBX-APIKEY': api_key
    })
print(response.json())