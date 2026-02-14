import spotipy
import yt_dlp
import requests
from spotipy.oauth2 import SpotifyOAuth



track = None
album = None
link = input("Enter the Spotify playlist link: ")

def link():
        if link.startswith("https://open.spotify.com/track/"):
            track = link.split("/")[-1]
            return track
        else:
            if link.startswith("https://open.spotify.com/playlist/"):
                album = link.split("/")[-1]
            return album


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri="http://localhost:8888/callback", scope="playlist-read-private"))

playlist_id = link()

results = sp.playlist_items(playlist_id)
tracks =  results['items']

for i, item in enumerate(tracks):
    track = item['track']
    print(f"{i + 1}. {track['name']} by {track['artists'][0]['name']}")


track = input("Enter the name of the track you want to download: ")


image_url = track['album']['images'][0]['url']
track_name = track['name']

img_data = requests.get(image_url).content

with open(f"{track_name}.jpg", "wb") as handler:
    handler.write(img_data)

print(f"Album cover for '{track_name}' has been downloaded")

def download_track(artist, track_name):
     search_query = f"{artist} - {track_name}"
     yt_dlp = {
          'format': 'bestaudio/best',
            'outtmpl':f'{artist} - {track_name}',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
     }



print(f"searching for '{search_query}' on YouTube...")

with yt_dlp.YoutubeDL(yt_dlp) as ydl:
     yt_dlp.download([f"ytsearch:{search_query}"])

download_spotify_track_as_mp3(artist, track)