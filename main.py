#!/usr/bin/env python3

import asyncio
import websockets
import threading
import time
import json

import youtube

async def send(client, data):
	await client.send(data)

async def handler(client, path):
	print("Websocket Client Connected.", client)
	clients.append(client)
	while True:
		try:
			pong_waiter = await client.ping()
			await pong_waiter
			time.sleep(3)
		except Exception as e:
			clients.remove(client)
			break

def broadcast(message):
	for client in message_clients:
		try:
			asyncio.run(send(client, message))
		except:
			pass

clients = []
start_server = websockets.serve(handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
threading.Thread(target = asyncio.get_event_loop().run_forever).start()

print("Socket Server Running. Starting main loop.")

new_id_counter = 0
while True:
	time.sleep(10)
	
	new_id_counter += 1
	if new_id_counter == 6:
		youtube.updateLiveChatID()
		new_id_counter = 0
	
	messages = youtube.getMessages()
	message_clients = clients.copy()
	for message in messages:
		print(message)
		broadcast(json.dumps(message))

	removed = youtube.getRemoved()
	for message in removed:
		print(message)
		broadcast(json.dumps(message))
	