import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import requests
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

# Завантажуємо змінні середовища
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

def get_track_info(spotify_url):
    """
    Отримує інформацію про трек з Spotify.
    """
    if not sp:
        return None

    try:
        if "track" not in spotify_url:
            return None

        track = sp.track(spotify_url)
        name = track['name']
        artist = track['artists'][0]['name']
        cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        
        return {
            "name": name,
            "artist": artist,
            "cover_url": cover_url,
            "full_name": f"{artist} - {name}"
        }
    except Exception as e:
        print(f"Error fetching Spotify info: {e}")
        return None

def download_track(search_query, output_dir="downloads"):
    """
    Шукає трек на YouTube та завантажує його як MP3.
    """
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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            
            if 'entries' in info:
                video_info = info['entries'][0]
            else:
                video_info = info

            base_filename = ydl.prepare_filename(video_info)
            # yt-dlp змінює розширення на .mp3
            mp3_filename = base_filename.rsplit('.', 1)[0] + '.mp3'
            
            # Перевірка на випадок, якщо yt-dlp залишив старе розширення в назві
            if not os.path.exists(mp3_filename):
                 mp3_filename = base_filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            
            return mp3_filename
    except Exception as e:
        print(f"Download error: {e}")
        return None

def download_cover(url, filename, output_dir="downloads"):
    """Завантажує картинку"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        response = requests.get(url)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    except Exception as e:
        print(f"Cover download error: {e}")
        return None

def set_mp3_cover(audio_path, cover_path):
    """
    Вшиває обкладинку прямо в файл MP3.
    """
    try:
        audio = MP3(audio_path, ID3=ID3)
        
        # Додаємо ID3 тег, якщо його немає
        try:
            audio.add_tags()
        except error:
            pass

        # Додаємо картинку
        with open(cover_path, 'rb') as albumart:
            audio.tags.add(
                APIC(
                    encoding=3, # 3 is for utf-8
                    mime='image/jpeg', # image/jpeg or image/png
                    type=3, # 3 is for the cover image
                    desc=u'Cover',
                    data=albumart.read()
                )
            )
        audio.save()
        return True
    except Exception as e:
        print(f"Error embedding cover: {e}")
        return False
