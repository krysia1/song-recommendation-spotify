import os
import pandas as pd
import urllib
import webbrowser
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import spotipy.util as util

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
print(CLIENT_SECRET)

scope = 'user-library-read'
token = util.prompt_for_user_token(
    scope, 
    client_id=CLIENT_ID, 
    client_secret=CLIENT_SECRET, 
    redirect_uri='http://localhost:8080/callback'
  )
spotify = spotipy.Spotify(auth=token)
playlist_dic = {}
playlist_cover_art = {}

for i in spotify.current_user_playlists()['items']:
    playlist_dic[i['name']] = i['uri'].split(':')[2]
    playlist_cover_art[i['uri'].split(':')[2]] = i['images'][0]['url']

print("PLAYLISTS: ", playlist_dic)


def generate_playlist_df(playlist_name, playlist_dic):
    
    playlist = pd.DataFrame()

    for i, j in enumerate(spotify.playlist(playlist_dic[playlist_name])['tracks']['items']):
        playlist.loc[i, 'artist'] = j['track']['artists'][0]['name']
        playlist.loc[i, 'track_name'] = j['track']['name']
        playlist.loc[i, 'track_id'] = j['track']['id']
        playlist.loc[i, 'image_url'] = j['track']['album']['images'][1]['url']
        playlist.loc[i, 'track_uri'] = j['track']['uri']


    # print(playlist.loc[0, 'url'])
    webbrowser.open(playlist.loc[0, 'track_uri'])

    return playlist

playlist_df = generate_playlist_df('Stretching', playlist_dic) 

# print("PLAYLIST STRETCHING: ", playlist_df)

# webbrowser.open(playlist_df[0])