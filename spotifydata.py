import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import requests
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

# Завантаження змінних середовища
load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

# Налаштування Spotify
if CLIENT_ID and CLIENT_SECRET:
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
else:
    sp = None
    print("WARNING: Spotify credentials not found in .env")

def resolve_url(url):
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        return url
    except:
        return url

def get_track_info(spotify_url):
    if not sp: return None
    spotify_url = resolve_url(spotify_url)
    try:
        if "track" not in spotify_url: return None
        track = sp.track(spotify_url, market="US")
        name = track['name']
        artist = track['artists'][0]['name']
        cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        return {"name": name, "artist": artist, "cover_url": cover_url, "full_name": f"{artist} - {name}"}
    except Exception as e:
        print(f"Error fetching track: {e}")
        return None

def get_playlist_tracks(url):
    if not sp: return []
    url = resolve_url(url)

    try:
        tracks = []
        if "album" in url:
            results = sp.album_tracks(url, market="US")
            album_info = sp.album(url, market="US")
            cover_url = album_info['images'][0]['url'] if album_info['images'] else None
            tracks_raw = results['items']
            is_album = True
        else:
            playlist_id = url.split("/playlist/")[1].split("?")[0]
            results = sp.playlist_tracks(playlist_id, market="US")
            tracks_raw = results['items']
            is_album = False
            cover_url = None

        while results['next']:
            results = sp.next(results)
            tracks_raw.extend(results['items'])
            
        final_data = []
        for item in tracks_raw:
            track = item if is_album else item['track']
            if not track: continue
            
            name = track['name']
            artist = track['artists'][0]['name']
            
            if is_album:
                track_cover = cover_url
            else:
                track_cover = track['album']['images'][0]['url'] if track['album']['images'] else None
            
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": track_cover,
                "full_name": f"{artist} - {name}"
            })
            
        return final_data

    except Exception as e:
        print(f"Error fetching playlist/album: {e}")
        return []

def get_artist_top_tracks(url):
    if not sp: return []
    url = resolve_url(url)
    try:
        artist_id = url.split("/artist/")[1].split("?")[0]
        results = sp.artist_top_tracks(artist_id, country="US")
        
        final_data = []
        for track in results['tracks']:
            name = track['name']
            artist = track['artists'][0]['name']
            cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
            
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": cover_url,
                "full_name": f"{artist} - {name}"
            })
        return final_data
    except Exception as e:
        print(f"Error fetching artist top tracks: {e}")
        return []

# --- Custom Logger to suppress warnings ---
class MyLogger:
    def debug(self, msg):
        pass # Ignore debug messages

    def warning(self, msg):
        # Ignore specific JS warning
        if "No supported JavaScript runtime" in msg:
            return
        print(f"WARNING: {msg}")

    def error(self, msg):
        print(f"ERROR: {msg}")

def download_track(search_query, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'quiet': True,
        'noplaylist': True,
        'ffmpeg_location': os.getcwd(),
        'logger': MyLogger(), # Use custom logger
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            if 'entries' in info: video_info = info['entries'][0]
            else: video_info = info
            base_filename = ydl.prepare_filename(video_info)
            mp3_filename = base_filename.rsplit('.', 1)[0] + '.mp3'
            if not os.path.exists(mp3_filename):
                 mp3_filename = base_filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return mp3_filename
    except Exception as e:
        print(f"Download error: {e}")
        return None

def download_cover(url, filename, output_dir="downloads"):
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        response = requests.get(url)
        with open(filepath, 'wb') as f: f.write(response.content)
        return filepath
    except Exception as e:
        print(f"Cover download error: {e}")
        return None

def set_mp3_cover(audio_path, cover_path):
    try:
        audio = MP3(audio_path, ID3=ID3)
        try: audio.add_tags()
        except error: pass
        with open(cover_path, 'rb') as albumart:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc=u'Cover', data=albumart.read()))
        audio.save()
        return True
    except Exception as e:
        print(f"Error embedding cover: {e}")
        return False
