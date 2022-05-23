import speech_recognition as sr

import os
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy
import spotipy.util as util

from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from random import randint

"""
run with command, set env variables
export SPOTIPY_CLIENT_ID='xxx' && export SPOTIPY_CLIENT_SECRET='xxx' &&
export SPOTIPY_REDIRECT_URI='URL from spotify dashboard' && python detect.py
"""

def levenshteinDistanceDP(token1, token2):
    distances = numpy.zeros((len(token1) + 1, len(token2) + 1))

    for t1 in range(len(token1) + 1):
        distances[t1][0] = t1

    for t2 in range(len(token2) + 1):
        distances[0][t2] = t2

    a = 0
    b = 0
    c = 0

    for t1 in range(1, len(token1) + 1):
        for t2 in range(1, len(token2) + 1):
            if token1[t1 - 1] == token2[t2 - 1]:
                distances[t1][t2] = distances[t1 - 1][t2 - 1]
            else:
                a = distances[t1][t2 - 1]
                b = distances[t1 - 1][t2]
                c = distances[t1 - 1][t2 - 1]

                if a <= b and a <= c:
                    distances[t1][t2] = a + 1
                elif b <= a and b <= c:
                    distances[t1][t2] = b + 1
                else:
                    distances[t1][t2] = c + 1

    # printDistances(distances, len(token1), len(token2))
    return distances[len(token1)][len(token2)]


class SpotipyApp:
    load_dotenv()

    SPOTIPY_CLIENT_ID = os.environ.get("CLIENT_ID")
    SPOTIPY_CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
    SPOTIPY_REDIRECT_URI = 'http://localhost:8080/callback'

    scope = [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-recently-played",
        "user-read-playback-position",
        "app-remote-control",
        "streaming",
        "playlist-modify-public",
        "user-library-modify",
        "user-read-currently-playing",
        "user-library-read",
        "playlist-modify-private",
    ]
    sp = None
    recognizer = None
    microphone = None
    text = None

    spotify_data = pd.read_csv('data/SpotifyFeatures.csv')

    spotify_features_df = spotify_data

    spotify_features_df = spotify_features_df.drop('genre',axis = 1)
    spotify_features_df = spotify_features_df.drop('artist_name', axis = 1)
    spotify_features_df = spotify_features_df.drop('track_name', axis = 1)
    spotify_features_df = spotify_features_df.drop('popularity',axis = 1)
    spotify_features_df = spotify_features_df.drop('key', axis = 1)
    spotify_features_df = spotify_features_df.drop('mode', axis = 1)
    spotify_features_df = spotify_features_df.drop('time_signature', axis = 1)


    def __init__(
        self,
    ):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=self.scope, client_id=self.SPOTIPY_CLIENT_ID, client_secret=self.SPOTIPY_CLIENT_SECRET, redirect_uri=self.SPOTIPY_REDIRECT_URI, cache_path='./tokens.txt'))
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.sp.volume(100)

        self.app_loop()

    def get_closest_title_url(self, items, title, artist=None):
        class reversor:
            def __init__(self, obj):
                self.obj = obj

            def __eq__(self, other):
                return other.obj == self.obj

            def __lt__(self, other):
                return other.obj < self.obj

        small_objects = list(
            map(
                lambda x: {
                    "popularity": x["popularity"],
                    "distance": levenshteinDistanceDP(x["name"], title),
                    "url": x["external_urls"]["spotify"],
                    "artists": list(map(lambda x: x["name"], x["artists"])),
                },
                items,
            )
        )
        small_objects.sort(key=lambda x: (x["distance"], reversor(x["popularity"])))
        if artist is not None:
            filtered_objects = list(
                filter(lambda x: artist in x["artists"], small_objects)
            )
            if len(filtered_objects) == 0:
                return small_objects[0]["url"]
            else:
                return filtered_objects[0]["url"]
        return small_objects[0]["url"]

    def handle_next_song(
        self,
    ):
        self.sp.next_track()

    def handle_previous_song(
        self,
    ):
        self.sp.previous_track()

    def handle_set_volume(
        self,
    ):
        tokens = self.text.split(" ")
        for token in tokens:
            if "%" in token:
                number = int(token[:-1])
                self.sp.volume(number)
                break

    def handle_search_and_play(self):
        tokens = self.text.split(" ")

        idx = tokens.index("playing") + 1
        title = tokens[idx:]
        title = " ".join(title)

        print("title:", title)

        searchResults = self.sp.search(title, 10, 0, "track")
        tracks_dict = searchResults["tracks"]
        tracks_items = tracks_dict["items"]

        song_url = self.get_closest_title_url(tracks_items, title)

        self.sp.add_to_queue(song_url)
        self.sp.next_track()

    def handle_search_and_play_artist(
        self,
    ):
        tokens = self.text.split(" ")

        if "by the artist" in self.text:
            idx_end = tokens.index("by")
            idx_artist = tokens.index("artist") + 1

        idx = tokens.index("playing") + 1
        title = tokens[idx:idx_end]
        title = " ".join(title)

        artist = tokens[idx_artist:]
        artist = " ".join(artist)

        print("title:", title, "----", artist)

        searchResults = self.sp.search(title, 10, 0, "track")

        tracks_dict = searchResults["tracks"]
        tracks_items = tracks_dict["items"]

        song_url = self.get_closest_title_url(tracks_items, title, artist)

        self.sp.add_to_queue(song_url)
        self.sp.next_track()

    def handle_similar_artist(
        self,
    ):
        current_track = self.sp.currently_playing()
        if current_track == None:
            print("CURRENTLY PLAYING: None")
        else:
            artists = [artist for artist in current_track['item']['artists']]
            artist_ID = artists[0]['id']
            similar_artists = self.sp.artist_related_artists(artist_ID)['artists']
            idx = numpy.random.randint(0, len(similar_artists))
            similar_track = self.sp.artist_top_tracks(similar_artists[idx]['id'], country='US')['tracks']
            idx = numpy.random.randint(0, len(similar_track))

            self.sp.add_to_queue(similar_track[idx]['id'])
            self.sp.next_track()

    def handle_start(
        self,
    ):
        self.sp.start_playback()

    def handle_stop(
        self,
    ):
        self.sp.pause_playback()

    def get_current_song(
        self,
    ):
        current_track = self.sp.current_user_playing_track()

        if current_track == None:
            print("CURRENTLY PLAYING: None")
        else:
            current_track_name = self.sp.current_user_playing_track()['item']['name']
            artists = [artist for artist in self.sp.current_user_playing_track()['item']['artists']]
            current_track_artists = ', '.join([artist['name'] for artist in artists])
            current_track_album = self.sp.current_user_playing_track()['item']['album']['name']
            print("CURRENTLY PLAYING: ", current_track_name, "by", current_track_artists, "from", current_track_album)

    def generate_song_vector(
        self,
    ):
        current_track = self.sp.current_user_playing_track()
        if current_track == None:
            print("Nothing is playing")
        else:
            current_track_id = self.sp.current_user_playing_track()['item']['id']
            current_track_features_list = self.sp.audio_features(tracks=[current_track_id])
            current_track_features = current_track_features_list[0]
            
            current_track_df = pd.DataFrame(dict(
                track_id=[current_track_id],
                acousticness=[current_track_features['acousticness']], 
                danceability=[current_track_features['danceability']], 
                duration_ms=[current_track_features['duration_ms']], 
                energy=[current_track_features['energy']],
                instrumentalness=[current_track_features['instrumentalness']],
                liveness=[current_track_features['liveness']],
                loudness=[current_track_features['loudness']],
                speechiness=[current_track_features['speechiness']],
                tempo=[current_track_features['tempo']],
                valence=[current_track_features['valence']]))

            spotify_features_nonsong = self.spotify_features_df[self.spotify_features_df['track_id'] != current_track_id]

            return current_track_df.sum(axis = 0), spotify_features_nonsong


    def generate_playlist_df(
        self,
    ):
        current_track = self.sp.current_user_playing_track()
        if current_track == None:
            print("Nothing is playing")
        else:
            current_playlist_uri = self.sp.current_user_playing_track()['context']['uri']

            current_playlist_id = current_playlist_uri[17:]
            playlist = pd.DataFrame()

            for i, j in enumerate(self.sp.playlist(current_playlist_id)['tracks']['items']):
                playlist.loc[i, 'track_id'] = j['track']['id']

            return playlist


    def generate_playlist_vector(
        self, playlist_df
    ):

        current_playlist_features_list = self.sp.audio_features(tracks=playlist_df['track_id'].values)
        playlist_features_df = pd.DataFrame()

        for i, j in enumerate(current_playlist_features_list):
            playlist_features_df.loc[i, 'track_id'] = j['id']
            playlist_features_df.loc[i, 'acousticness'] = j['acousticness']
            playlist_features_df.loc[i, 'danceability'] = j['danceability']
            playlist_features_df.loc[i, 'duration_ms'] = j['duration_ms']
            playlist_features_df.loc[i, 'energy'] = j['energy']
            playlist_features_df.loc[i, 'instrumentalness'] = j['instrumentalness']
            playlist_features_df.loc[i, 'liveness'] = j['liveness']
            playlist_features_df.loc[i, 'loudness'] = j['loudness']
            playlist_features_df.loc[i, 'speechiness'] = j['speechiness']
            playlist_features_df.loc[i, 'tempo'] = j['tempo']
            playlist_features_df.loc[i, 'valence'] = j['valence']

        spotify_features_nonplaylist = self.spotify_features_df[~self.spotify_features_df['track_id'].isin(playlist_df['track_id'].values)]

        return playlist_features_df.sum(axis = 0), spotify_features_nonplaylist


    def generate_recommendation(
        self, spotify_data, song_vector, nonsong_df
    ):
        non_song = spotify_data[spotify_data['track_id'].isin(nonsong_df['track_id'].values)]
        nonsong_df = nonsong_df.drop(['track_id'], axis = 1)
        song_vector = song_vector.drop(labels = 'track_id')

        similarity = cosine_similarity(nonsong_df.values, song_vector.values.reshape(1, -1))[:,0]
        
        non_song['sim'] = similarity
        non_playlist_top10 = non_song.sort_values('sim', ascending = False).head(10)
        non_playlist_top10['uri'] = non_playlist_top10['track_id'].apply(lambda x: self.sp.track(x)['uri'])

        print(non_playlist_top10)
        song_url = non_playlist_top10.iloc[randint(0, 9)]['uri']
        self.sp.add_to_queue(song_url)
        self.sp.next_track()


    def app_loop(
        self,
    ):
        print("You can talk now")
        while True:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source)
            try:
                self.text = self.recognizer.recognize_google(audio)
                # self.text = "start playing The Girl From Ipanema by the artist Stan Getz"
                print(self.text)
                tokens = self.text.split(" ")

                if any(x in tokens for x in ["play", "start"]) and len(tokens) < 3:
                    self.handle_start()
                elif any(x in tokens for x in ["stop", "pause"]):
                    self.handle_stop()
                elif all(x in tokens for x in ["like", "this"]):
                    self.handle_similar_artist()
                elif all(x in tokens for x in ["start", "playing", "by", "the", "artist"]):
                    self.handle_search_and_play_artist()
                elif all(x in tokens for x in ["start", "playing",]):
                    self.handle_search_and_play()
                elif all(x in tokens for x in ["artist"]):
                    self.handle_similar_artist()
                elif all(x in tokens for x in ["set", "volume", "to"]):
                    self.handle_set_volume()
                elif all(x in tokens for x in ["play", "next", "song"]):
                    self.handle_next_song()
                elif all(x in tokens for x in ["next"]):
                    self.handle_next_song()
                elif any(x in tokens for x in ["previous", "back", "last"]):
                    self.handle_previous_song()
                elif all(x in tokens for x in ["what's", "currently", "playing"]):
                    self.get_current_song()
                elif all(x in tokens for x in ["recommend", "based", "on", "this", "song"]):
                    song_vector, nonsong_df = self.generate_song_vector()
                    self.generate_recommendation(self.spotify_data, song_vector, nonsong_df)
                elif all(x in tokens for x in ["recommend", "based", "on", "this", "playlist"]):
                    playlist_vector, nonplaylist_df = self.generate_playlist_vector(self.generate_playlist_df())
                    self.generate_recommendation(self.spotify_data, playlist_vector, nonplaylist_df)

            except sr.UnknownValueError:
                pass


if __name__ == "__main__":

    SpotipyApp()
