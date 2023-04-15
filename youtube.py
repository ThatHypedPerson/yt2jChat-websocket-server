import os
import sys

import pickle # store/read credentials

# Google API imports
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth.transport.requests

# YouTube API setup

# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client_secrets_file = "client_secret.json"

scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

# Get credentials and create an API client
flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
	client_secrets_file, scopes)

def getCredentials():
	global credentials
	try:
		with open('credentials.pkl', 'rb') as f:
			credentials = pickle.load(f)
		if credentials is None:
			print("Please supply a valid credentials.pkl")
			sys.exit()
		if credentials.expired:
			credentials = refreshCredentials(credentials)
	
	# basic error logging, too lazy to implement proper logging
	except Exception as error:
		with open('error.txt', "w") as f:
			f.write(str(error))
		print(error)
		sys.exit()

def refreshCredentials(credentials):
	request = google.auth.transport.requests.Request()
	credentials.refresh(request)
	with open('credentials.pkl', 'wb') as f:
		pickle.dump(credentials, f, pickle.HIGHEST_PROTOCOL)
	return credentials

liveChatID = ""
def updateLiveChatID():
	global liveChatID
	
	request = youtube.liveBroadcasts().list(
		part = "snippet,contentDetails,status",
		broadcastStatus = "all",
		broadcastType = "all",
		maxResults = 50
	)

	streams = []
	while request is not None:
		response = request.execute()
		for item in response["items"]:
			if item["status"]["lifeCycleStatus"] != "complete": # only look at active/soon to be active streams
				streams.append(item)
			elif item['snippet']['liveChatId'] == liveChatID:
					clearCache()
		request = youtube.playlistItems().list_next(request, response)
	
	# give an empty value if there is no active stream
	if len(streams) == 0:
		liveChatID = ""
		global read
		read = False
		return
	
	# get latest "active" livestream
	for stream in streams:
		if stream["status"]["lifeCycleStatus"] == "active":
			liveChatID = stream['snippet']['liveChatId']
			checkLive(stream)
			return
	
	# return latest stream if none are live
	liveChatID = streams[0]['snippet']['liveChatId']
	checkLive(streams[0])

read = False
def checkLive(stream):
	global read
	if stream["status"]["lifeCycleStatus"] in ("ready", "live")\
		and not stream["status"]["privacyStatus"] == "private":
			read = True
	else:
		read = False

message_ids = []
removed_ids = []
def getMessages():
	global read
	if not read:
		print("skipping messages")
		return
	request = youtube.liveChatMessages().list(
		liveChatId = liveChatID,
		part = "snippet,authorDetails"
	)
	response = request.execute()

	global message_ids
	global removed_ids
	messages = []
	all_messages = []
	for message in response["items"]:
		if message["id"].replace(".", "") not in message_ids:
			info = formatMessage(message)
			messages.append({
				"username": message['authorDetails']['displayName'],
				"info": info,
				"message": message['snippet']['displayMessage']
				})
			message_ids.append(message["id"].replace(".", ""))
		
		all_messages.append(message["id"].replace(".", "")) # used to check for deleted messages
	
	# find any deleted messages
	removed_ids = list(set(message_ids).difference(all_messages))
	
	return messages
	
def getRemoved():
	messages = []
	global message_ids
	global removed_ids
	for message in removed_ids:
		messages.append({"info": "deleted", "message": message})
		message_ids.remove(message)
	removed_ids = []
	return messages	

def formatMessage(message):
	# format youtube author details to twitch IRC info
	badges = ""
	badge_info = True

	if message['authorDetails']['isChatOwner']:
		badges += "broadcaster/1"
	if message['authorDetails']['isChatModerator']:
		badges += "moderator/1"
	if message['authorDetails']['isChatSponsor']:
		badges += "partner/1"
	if message['authorDetails']['isVerified']: # expand when memberships are enabled
		badges += "subscriber/0"
	if badges == "":
		badges = True
	

	info = {
		"badge-info": badge_info,
		"badges": badges, # (only check for listed below)
		"color": True,
		"display-name": message["authorDetails"]["displayName"],
		"emotes": True,
		"first-msg": "0",
		"flags": True,
		"id": message["id"].replace(".", ""),
		"mod": 1 if message["authorDetails"]["isChatModerator"] else 0,
		"returning-chatter": "0",
		"room-id": "133875470", # change?
		"subscriber": "0", # update for memberships
		"tmi-sent-ts": message["snippet"]["publishedAt"], # (change to epoch time?)
		"turbo": "0",
		"user-id": message["authorDetails"]["channelId"],
		"user-type": True # need to implement mod user-type
	}

	return info

def clearCache():
	global message_ids
	message_ids = []

getCredentials()
youtube = googleapiclient.discovery.build(
		"youtube", "v3", credentials=credentials)
updateLiveChatID()