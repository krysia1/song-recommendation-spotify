import os
import pandas as pd
import webbrowser
import spotipy
import spotipy.util as util

from dotenv import load_dotenv

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

spotify_data = pd.read_csv('data/SpotifyFeatures.csv')

#print(spotify_data)

spotify_features_df = spotify_data
genre_OHE = pd.get_dummies(spotify_features_df.genre)
key_OHE = pd.get_dummies(spotify_features_df.key)

scaled_features = MinMaxScaler().fit_transform([
    spotify_features_df['acousticness'].values,
    spotify_features_df['danceability'].values,
    spotify_features_df['duration_ms'].values,
    spotify_features_df['energy'].values,
    spotify_features_df['instrumentalness'].values,
    spotify_features_df['liveness'].values,
    spotify_features_df['loudness'].values,
    spotify_features_df['speechiness'].values,
    spotify_features_df['tempo'].values,
    spotify_features_df['valence'].values
])

spotify_features_df[['acousticness','danceability','duration_ms','energy','instrumentalness','liveness','loudness','speechiness','tempo','valence']] = scaled_features.T

spotify_features_df = spotify_features_df.drop('genre',axis = 1)
spotify_features_df = spotify_features_df.drop('artist_name', axis = 1)
spotify_features_df = spotify_features_df.drop('track_name', axis = 1)
spotify_features_df = spotify_features_df.drop('popularity',axis = 1)
spotify_features_df = spotify_features_df.drop('key', axis = 1)
spotify_features_df = spotify_features_df.drop('mode', axis = 1)
spotify_features_df = spotify_features_df.drop('time_signature', axis = 1)

spotify_features_df = spotify_features_df.join(genre_OHE)
spotify_features_df = spotify_features_df.join(key_OHE)

#print(spotify_features_df)

scope = 'user-library-read'
token = util.prompt_for_user_token(
    scope,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri='http://localhost:8080/callback'
)
spotify = spotipy.Spotify(auth=token)
playlist_dic = {}

for i in spotify.current_user_playlists()['items']:
    playlist_dic[i['name']] = i['uri'].split(':')[2]

#print("PLAYLISTS: ", playlist_dic)


def generate_playlist_df(playlist_name, playlist_dic, spotify_data):

    playlist = pd.DataFrame()

    for i, j in enumerate(spotify.playlist(playlist_dic[playlist_name])['tracks']['items']):
        playlist.loc[i, 'artist'] = j['track']['artists'][0]['name']
        playlist.loc[i, 'track_name'] = j['track']['name']
        playlist.loc[i, 'track_id'] = j['track']['id']
        playlist.loc[i, 'image_url'] = j['track']['album']['images'][1]['url']
        playlist.loc[i, 'track_uri'] = j['track']['uri']
        playlist.loc[i, 'date_added'] = j['added_at']
        
        
    playlist['date_added'] = pd.to_datetime(playlist['date_added'])
    
    playlist = playlist[playlist['track_id'].isin(spotify_data['track_id'].values)].sort_values('date_added',ascending = False)

    return playlist


playlist_df = generate_playlist_df('Impreza w podróży', playlist_dic, spotify_data)

#print("PLAYLIST STRETCHING: ", playlist_df)
#webbrowser.open(playlist_df.loc[0, 'track_uri'])


def generate_playlist_vector(spotify_features, playlist_df, weight_factor):

    spotify_features_playlist = spotify_features[spotify_features['track_id'].isin(playlist_df['track_id'].values)]
    spotify_features_playlist = spotify_features_playlist.merge(playlist_df[['track_id','date_added']], on = 'track_id', how = 'inner')
    
    spotify_features_playlist.drop_duplicates('track_id', inplace=True)

    spotify_features_nonplaylist = spotify_features[~spotify_features['track_id'].isin(playlist_df['track_id'].values)]

    playlist_feature_set = spotify_features_playlist.sort_values('date_added',ascending=False)

    most_recent_date = playlist_feature_set.iloc[0,-1]

    for ix, row in playlist_feature_set.iterrows():
        playlist_feature_set.loc[ix,'days_from_recent'] = int((most_recent_date.to_pydatetime() - row.iloc[-1].to_pydatetime()).days)
        

    playlist_feature_set['weight'] = playlist_feature_set['days_from_recent'].apply(lambda x: weight_factor ** (-x))
#    print("playlist_feature_set:", playlist_feature_set)

    playlist_feature_set_weighted = playlist_feature_set.copy()

    playlist_feature_set_weighted.update(playlist_feature_set_weighted.iloc[:,:-3].mul(playlist_feature_set_weighted.weight.astype(int),0))

    playlist_feature_set_weighted_final = playlist_feature_set_weighted.iloc[:, :-3]
#    print("playlist_feature_set_weighted_final:", playlist_feature_set_weighted_final)
#    playlist_feature_set_weighted_final = playlist_feature_set_weighted_final.drop('artist_name', axis = 1)
#    playlist_feature_set_weighted_final = playlist_feature_set_weighted_final.drop('track_name', axis = 1)
    
#    print(playlist_feature_set_weighted_final.sum(axis = 0))

    return playlist_feature_set_weighted_final.sum(axis = 0), spotify_features_nonplaylist


playlist_vector, nonplaylist_df = generate_playlist_vector(spotify_features_df, playlist_df, 1.2)
#print(playlist_vector.shape)
#print(nonplaylist_df)


def generate_recommendation(spotify_data, playlist_vector, nonplaylist_df):

    non_playlist = spotify_data[spotify_data['track_id'].isin(nonplaylist_df['track_id'].values)]
    nonplaylist_df = nonplaylist_df.drop(['track_id'], axis = 1)
    playlist_vector = playlist_vector.drop(labels = 'track_id')

    similarity = cosine_similarity(nonplaylist_df.values, playlist_vector.values.reshape(1, -1))[:,0]
    
    non_playlist['sim'] = similarity
    non_playlist_top10 = non_playlist.sort_values('sim', ascending = False).head(10)
    non_playlist_top10['url'] = non_playlist_top10['track_id'].apply(lambda x: spotify.track(x)['album']['images'][1]['url'])
    non_playlist_top10['uri'] = non_playlist_top10['track_id'].apply(lambda x: spotify.track(x)['uri'])

    return  non_playlist_top10
    

top10 = generate_recommendation(spotify_data, playlist_vector, nonplaylist_df)
print(top10)

webbrowser.open(top10.iloc[0]['uri'])
