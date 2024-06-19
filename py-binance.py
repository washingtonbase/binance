import time

from binance import ThreadedWebsocketManager

import asyncio
from binance import AsyncClient, BinanceSocketManager


import dotenv

dotenv.load_dotenv()
import os

api_key = os.getenv('api_key')
api_secret = os.getenv('api_secret')

async def main():
    client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
    bm = BinanceSocketManager(client)
    # start any sockets here, i.e a trade socket
    ts = bm.user_socket()

    # then start receiving messages
    async with ts as tscm:
        while True:
            res = await tscm.recv()
            print(res)

    await client.close_connection()

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
