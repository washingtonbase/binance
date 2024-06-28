import threading
import time
import pickle
import json
import websocket

real_time_prices = []

def run_websocket():
    global real_time_prices

    def on_message(ws, message):
        global real_time_prices
        message_ = json.loads(message)
        real_time_prices.append({"t": message_['T'], "p": message_['p']})

    ws = websocket.WebSocketApp("wss://fstream.binance.com/ws/1000pepeusdc@aggTrade", on_message=on_message)
    ws.run_forever()

def save_to_pickle():
    global real_time_prices

    while True:
        time.sleep(60)  # Save every 60 seconds
        with open('real_time_prices.pkl', 'wb') as f:
            pickle.dump(real_time_prices, f)
        print("Saved to pickle file.")

websocket_thread = threading.Thread(target=run_websocket)
websocket_thread.start()

save_thread = threading.Thread(target=save_to_pickle)
save_thread.start()
