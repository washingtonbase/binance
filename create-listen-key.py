import requests
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
dotenv_path = '.env'
load_dotenv(dotenv_path)

# 从环境变量中获取 API Key 和 API Secret
api_key = os.getenv('api_key')
api_secret = os.getenv('api_secret')

# Binance REST API Base URL
BASE_URL = 'https://dapi.binance.com'

# 创建 listen key 的函数
def create_listen_key(api_key):
    url = f'{BASE_URL}/dapi/v1/listenKey'
    headers = {
        'X-MBX-APIKEY': api_key
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()['listenKey']
    else:
        print(f"Failed to create listen key: {response.status_code}, {response.text}")
        return None

# 使用 API Key 来创建一个新的 listen key
listen_key = create_listen_key(api_key)
if listen_key:
    print(f"Created listen key: {listen_key}")

