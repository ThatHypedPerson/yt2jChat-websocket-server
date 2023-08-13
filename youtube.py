import os
import sys
from dotenv import load_dotenv
load_dotenv()

import pytchat

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

## YouTube API Requests
api_service_name = "youtube"
api_version = "v3"
api_key = os.environ["api_key"]

youtubeAPI = googleapiclient.discovery.build(
	api_service_name, api_version, developerKey = api_key)

## YouTube OAuth Requests
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
client_secrets_file = "client_secret.json"

flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
	client_secrets_file, scopes)

def getCredentials():
	global youtubeOAuth
	try:
		with open('credentials.pkl', 'rb') as f:
			credentials = pickle.load(f)
		if credentials is None:
			print("Please supply a valid credentials.pkl")
		else:
			youtubeOAuth = googleapiclient.discovery.build(
				"youtube", "v3", credentials=credentials)
	
	# basic error logging, too lazy to implement proper logging
	except Exception as error:
		with open('error.txt', "w") as f:
			f.write(str(error))
		print(error)

chat = None
def updateStreamID(url = None):
	# skip checking for a new stream when given a url
	if not url is None:
		createChat(url)
		return
	
	# OAuth Request (more accurate, usable by anyone)
	try:
		request = youtubeOAuth.liveBroadcasts().list(
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
			request = youtubeOAuth.playlistItems().list_next(request, response)
		
		# do nothing when there is no active stream
		if len(streams) == 0:
			return
		
		# get latest "active" livestream
		for stream in streams:
			if stream["status"]["lifeCycleStatus"] == "active":
				streamID = stream['snippet']['thumbnails']['default']['url']
				parseStreamID(streamID)
				return
		
		# get latest stream if none are live
		streamID = streams[0]['snippet']['thumbnails']['default']['url']
		parseStreamID(streamID)
	
	# API Request (only usable by me, the person who made this)
	except:
		# i'm lazy so just get the first result in the "streams" playlist
		request = youtubeAPI.playlistItems().list(
			part = "snippet",
			maxResults = 1,
			playlistId = "PLAWgoOAOTXvFT_H--Vnu0KrbPEgnpO8QG"
		)
		response = request.execute()
		streamID = response["items"][0]['snippet']['thumbnails']['default']['url']
		parseStreamID(streamID)

def parseStreamID(url):
	streamID = url[23:url.find("/", 23)] # could hardcode but nah
	createChat(streamID)

def createChat(url):
	global chat
	if chat:
		chat.terminate()
	print("updating chat to:", url)
	chat = pytchat.create(video_id=url, interruptable=False)

def processMessage(message):
	# include messageEx to add emotes
	info = formatMessage(message)
	processed = {
		"username": message.author.name,
		"info": info,
		"message": message.message
	}
	return processed

def formatMessage(message):
	# format youtube author details to twitch IRC info
	badges = ""
	badge_info = True

	# include badgeUrl later

	if message.author.isChatOwner:
		badges += "broadcaster/1"
	if message.author.isChatModerator:
		badges += "moderator/1"
	if message.author.isVerified:
		badges += "partner/1"
	if message.author.isChatSponsor: # test/expand when memberships are enabled
		badges += "subscriber/0"
	if badges == "":
		badges = True
	

	info = {
		"badge-info": badge_info,
		"badges": badges, # (only check for listed below)
		"color": True,
		"display-name": message.author.name,
		"emotes": True,
		"first-msg": "0",
		"flags": True,
		"id": message.id.replace(".", ""),
		"mod": 1 if message.author.isChatModerator else 0,
		"returning-chatter": "0",
		"room-id": "133875470", # change?
		"subscriber": "0", # update for memberships
		"tmi-sent-ts": message.timestamp,
		"turbo": "0",
		"user-id": message.author.channelId,
		"user-type": True # need to implement mod user-type
	}

	return info

getCredentials()
updateStreamID()