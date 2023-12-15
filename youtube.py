import os
from dotenv import load_dotenv
load_dotenv()

import pytchat
from urllib.parse import urlparse, parse_qs

import pickle # store/read credentials
import time # chat update logic
import pprint

# Google API imports
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth.transport.requests
from google.oauth2.credentials import Credentials

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

# https://stackoverflow.com/a/73789465
def getCredentials():
	credentials = None
	if os.path.exists("credentials.token"):
		credentials = Credentials.from_authorized_user_file("credentials.token", scopes)
	if not credentials or not credentials.valid:
		if credentials and credentials.expired and credentials.refresh_token:
			credentials.refresh(google.auth.transport.requests.Request())
		else:
			# easier to manually get the right tokens locally than on a server
			input("add a valid credentials.token before continuing")
			getCredentials()
			return
	global youtubeOAuth
	youtubeOAuth = googleapiclient.discovery.build(
				"youtube", "v3", credentials=credentials)

chat = None

# need to fix: will always default to latest unlisted stream rather than a current stream
def updateChat():
	global is_alive
	if is_alive:
		createChat()
		is_alive = checkStreamState()
	elif time.time() - last_updated > 60:
		print("attempting to find a new stream")
		updateStreamID()
		is_alive = checkStreamState()
		if is_alive:
			createChat()

def checkStreamState():
	global stream_id
	if stream_id is None or stream_id == "":
		return False
	request = youtubeOAuth.liveBroadcasts().list(
		part = "snippet,contentDetails,status",
		id = stream_id,
		maxResults = 1
	)
	response = request.execute()
	print("checking status of:", response["items"][0]['snippet']['title'])
	return response["items"][0]["status"]["lifeCycleStatus"] != "complete" \
		and response["items"][0]["status"]["privacyStatus"] != "private"

stream_id = ""
def updateStreamID(url = None):
	# skip checking for a new stream when given a url
	if not url is None:
		global is_alive
		is_alive = True
		stream_id = parseStreamID(url)
	else:
		getStreamID()
	
def getStreamID():	
	# OAuth Request
	global stream_id
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
				# only look at active/soon to be active streams
				if item["status"]["lifeCycleStatus"] != "complete" \
					and item["status"]["privacyStatus"] != "private":
						streams.append(item)
			request = youtubeOAuth.playlistItems().list_next(request, response)
		
		# do nothing when there is no active stream
		if len(streams) == 0:
			return stream_id
		
		# get latest "active" livestream
		for stream in streams:
			if stream["status"]["lifeCycleStatus"] == "active":
				stream_id = stream['snippet']['thumbnails']['default']['url'][23:34]
				title = stream['snippet']['title']
				print("updating stored stream to:", title)
		
		# get latest stream if none are live
		stream_id = streams[0]['snippet']['thumbnails']['default']['url'][23:34]
		title = stream['snippet']['title']
		print("updating stored stream to:", title)
	
	# attempt to refresh OAuth if it fails
	except google.auth.exceptions.RefreshError:
		getCredentials()

# https://gist.github.com/kmonsoor/2a1afba4ee127cce50a0
def parseStreamID(url):
	if url.startswith(('youtu', 'www')):
		url = 'http://' + url
		
	query = urlparse(url)
	
	if 'youtube' in query.hostname:
		if query.path == '/watch':
			return parse_qs(query.query)['v'][0]
		elif query.path.startswith(('/embed/', '/v/')):
			return query.path.split('/')[2]
	elif 'youtu.be' in query.hostname:
		return query.path[1:]

last_updated = 0
is_alive = False
def createChat():
	global chat
	global stream_id
	global last_updated
	if chat:
		chat.terminate()
	print("updating chat to:", stream_id)
	chat = pytchat.create(video_id=stream_id, interruptable=False)
	last_updated = time.time()

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
# updateChat()
# updateStreamID()