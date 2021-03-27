import requests
import json
import webbrowser
import argparse
import math
from requests_oauthlib import OAuth2Session
from secrets import client_id, client_secret, spotify_user_id

scope = 'playlist-modify-public'
redirect_uri = 'https://example.com'

playlist_names = ['Calm', 'Relaxed', 'Standard', 'Energetic']
oauth = None
playlist_size = 0

def main():
	global playlist_size

	parser = argparse.ArgumentParser(description='Sort Spotify playlist by energy.')
	parser.add_argument('id', help='The ID of the playlist to be sorted. The ID is the last part of the 								Spotify URI which can be found by right-clicking the playlist and 									selecting "Copy Spotify URI" under the "Share" option')

	args = parser.parse_args()
	playlist_id = args.id
	#Acquire authorization token for private requests
	oauth = getToken()
	#Request the playlist with the id given by the user
	r = oauth.get('https://api.spotify.com/v1/playlists/{}'.format(playlist_id))
	#Check if the request was successful
	if (r.status_code != requests.codes.ok):
		print("Request for playlist failed! Response code is: %d", r.status_code)
		return
	response = r.json()
	playlist_size = response['tracks']['total']
	#Request the tracks of the playlist in chunks of 100 to avoid API limitations
	playlist = [oauth.get('https://api.spotify.com/v1/playlists/{}/tracks?offset={}'
				.format(playlist_id, i*100)).json()
				for i in range(math.ceil(playlist_size/100))]
	
	populatePlaylists(sortByEnergy(playlist))

#Sorts the tracks into 4 groups based on their energy level
def sortByEnergy(playlist):
	newPlaylists = [[],[],[],[]]
	features = []
	#Collect every id and add it to the request string, separated by '%2C' aka ','
	for response in playlist:
		requestString = 'https://api.spotify.com/v1/audio-features?ids='
		for track in response['items']:
			requestString += track['track']['id'] + '%2C'
		#Cut off the last '%2C'
		requestString = requestString[:-3]
		features.append(oauth.get(requestString).json())

	#Go through every track and sort based on energy level
	for response in features:
		for track in response['audio_features']:
			energy = track['energy']

			if energy < 0.25:
				newPlaylists[0].append(track['uri'])
			elif energy < 0.5:
				newPlaylists[1].append(track['uri'])
			elif energy < 0.75:
				newPlaylists[2].append(track['uri'])
			else:
				newPlaylists[3].append(track['uri'])
	return newPlaylists

#Creates the playlists and adds the tracks to it
def populatePlaylists(playlists):
	index = 0
	for playlist in playlists:
		#Specify the name of the playlist
		request_body = json.dumps({
			'name' : playlist_names[index]
		})
		query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
		#Make the post request to create the playlist
		response = oauth.post(query, data=request_body)
		response_json = response.json()

		#Dump the uris from the playlist into the request_body
		uri_chunks = [playlist[x:x+100] for x in range(0, len(playlist), 100)]

		for chunk in uri_chunks:
			request_body = json.dumps(chunk)
			query = "https://api.spotify.com/v1/playlists/{}/tracks".format(response_json['id'])
			#Make the post request to add the songs in request_body to the playlist
			response = oauth.post(query, request_body)
		index += 1

def getToken():
	global oauth
	oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
	#Create authorization url
	authorization_url, state = oauth.authorization_url('https://accounts.spotify.com/authorize')
	#Open the url in a browser
	webbrowser.open(authorization_url)
	#The response is the url the user is redirected to after accepting the scopes
	authorization_response = input('Enter the callback URL here\n')

	#Use the response url to fetch a token from spotify
	token = oauth.fetch_token(
		token_url='https://accounts.spotify.com/api/token',
		authorization_response=authorization_response,
		client_secret=client_secret
	)
	return oauth

main()