#!/usr/bin/env python3

import asyncio
import websockets
import threading
import time
import random

def gen_data():
    print("Generating data...")
    time.sleep(3)
    data = "test" + str(random.randint(1, 10))
    
    return data

async def send(client, data):
    await client.send(data)

async def handler(client, path):
    # Register.
    print("Websocket Client Connected.", client)
    clients.append(client)
    while True:
        try:
            print("ping", client)
            pong_waiter = await client.ping()
            await pong_waiter
            print("pong", client)
            time.sleep(3)
        except Exception as e:
            clients.remove(client)
            print("Websocket Client Disconnected", client)
            break

clients = []
start_server = websockets.serve(handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
threading.Thread(target = asyncio.get_event_loop().run_forever).start()

print("Socket Server Running. Starting main loop.")

while True:
    data = str(gen_data())
    message_clients = clients.copy()
    for client in message_clients:
        print("Sending", data, "to", client)
        try:
            asyncio.run(send(client, data))
        except:
            # Clients might have disconnected during the messaging process,
            # just ignore that, they will have been removed already.
            pass
