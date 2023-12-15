#!/usr/bin/env python3

import asyncio
import os
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
			message = await client.recv()
			print("recieved:", message)

			message = message.split()
			if message[0] == "update":
				if len(message) > 1: # explicit url given
					youtube.updateStreamID(message[1])
				else:
					youtube.updateStreamID(None) # grab first stream
			elif message[0] == "reload":
				youtube.getCredentials() # update .pkl file
			
		except Exception as error:
			print(type(error), str(error))
			clients.remove(client)
			print("Websocket Client Disconnected.", client)
			break

def broadcast(message):
	for client in message_clients:
		try:
			asyncio.run(send(client, message))
		except:
			pass

clients = []
start_server = websockets.serve(handler, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
threading.Thread(target = asyncio.get_event_loop().run_forever).start()

print("Started.")

while True:
	try:
		# chat seems to go inactive after an hour
		youtube.updateChat()
		if youtube.chat is not None:
			while youtube.chat.is_alive():
				data = youtube.chat.get()
				items = data.items
				for message in items:
					message_clients = clients.copy()
					message = youtube.processMessage(message)
					broadcast(json.dumps(message))
					print(message["username"] + ":", message["message"]) # console output
				# check for a new message every second
				time.sleep(1)
	except KeyboardInterrupt:
		os._exit(0)
		# sys.exit() # doesn't work for some reason
	except Exception as e:
		print(type(e), str(e))
		os._exit(0)