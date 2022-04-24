import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
client_secret=CLIENT_SECRET,
redirect_uri='http://localhost:8080/callback',
scope='user-read-currently-playing'))

current_track = spotify.current_user_playing_track()

if current_track == None:
    print("CURRENTLY PLAYING: None")
else:
    current_track_name = spotify.current_user_playing_track()['item']['name']
    artists = [artist for artist in spotify.current_user_playing_track()['item']['artists']]
    current_track_artists = ', '.join([artist['name'] for artist in artists])
    current_track_album = spotify.current_user_playing_track()['item']['album']['name']
    print("CURRENTLY PLAYING: ", current_track_name, "by", current_track_artists, "from", current_track_album)
