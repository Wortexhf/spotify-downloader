import asyncio
import logging
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv
import spotifydata
import requests

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- HELPER: DOWNLOAD & SEND ---
async def download_and_send_track(message: types.Message, track_info: dict, status_msg: types.Message = None, send_photo_msg: bool = True):
    """
    Downloads and sends a single track.
    """
    text = f"⬇️ Downloading: {track_info['full_name']}..."
    if not status_msg:
        status_msg = await message.answer(text)
    else:
        await status_msg.edit_text(text)
    
    try:
        # 1. Download Cover
        safe_name = "".join([c for c in track_info['name'] if c.isalnum() or c in (' ', '.', '_')]).strip()
        cover_filename = f"{safe_name}_cover.jpg"
        
        cover_path = None
        if track_info.get('cover_url'):
            cover_path = await asyncio.to_thread(spotifydata.download_cover, track_info['cover_url'], cover_filename, DOWNLOAD_DIR)
        
        # 2. Download Audio
        search_query = f"{track_info['artist']} - {track_info['name']}"
        audio_path = await asyncio.to_thread(spotifydata.download_track, search_query, DOWNLOAD_DIR)

        if not audio_path or not os.path.exists(audio_path):
            await status_msg.edit_text(f"❌ Download failed: {track_info['full_name']}")
            return False

        # 3. Embed Cover
        if cover_path and os.path.exists(cover_path):
             await asyncio.to_thread(spotifydata.set_mp3_cover, audio_path, cover_path)

        # 4. Send Files
        await status_msg.edit_text("🚀 Uploading...")
        
        if send_photo_msg and cover_path and os.path.exists(cover_path):
           photo = FSInputFile(cover_path)
           try:
               await message.answer_photo(photo)
           except Exception as e:
               print(f"Error sending photo: {e}")

        audio_file = FSInputFile(audio_path)
        thumbnail_file = FSInputFile(cover_path) if cover_path and os.path.exists(cover_path) else None

        await message.answer_audio(
            audio_file,
            caption=f"🎧 {track_info['full_name']}",
            performer=track_info['artist'],
            title=track_info['name'],
            thumbnail=thumbnail_file
        )

        await status_msg.delete()

        # 5. Cleanup
        await asyncio.sleep(1)
        try:
            if audio_path and os.path.exists(audio_path): os.remove(audio_path)
            if cover_path and os.path.exists(cover_path): os.remove(cover_path)
        except Exception as e:
            print(f"Cleanup error: {e}")
            
        return True

    except Exception as e:
        print(f"Error processing track {track_info.get('name')}: {e}")
        await status_msg.edit_text(f"❌ Error: {e}")
        return False

# --- HELPER: URL UTILS ---
def extract_url(text):
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    if match:
        return match.group(0)
    return text.strip()

def resolve_url(url):
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        return url
    except:
        return url

# --- COMMAND HANDLERS ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 **Hello, {message.from_user.first_name}!**\n\n"
        "I am a **Spotify Downloader Bot**. 🎵\n"
        "I can download music in high quality with cover art.\n\n"
        "**Supported links:**\n"
        "🔹 **Track:** `open.spotify.com/track/...`\n"
        "🔹 **Album:** `open.spotify.com/album/...`\n\n"
        "🚀 **Just send me a link to start!**"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "❓ **Help**\n\n"
        "1. **Send a link:** Copy a link from Spotify (Track or Album) and paste it here.\n"
        "2. **Wait:** Albums may take some time to process.\n\n"
        "⚠️ **Note:** Playlists and Artist profiles are currently not supported.\n\n"
        "commands:\n"
        "/start - Restart bot\n"
        "/help - Show this message"
    )
    await message.answer(help_text, parse_mode="Markdown")

# --- MAIN LINK HANDLER ---

@dp.message(F.text.contains("spotify"))
async def handle_spotify_link(message: types.Message):
    status_msg = await message.answer("🔎 Processing link...")

    raw_url = extract_url(message.text)
    real_url = await asyncio.to_thread(resolve_url, raw_url)
    print(f"DEBUG: Processing URL: {real_url}")

    # --- TRACK ---
    if "/track/" in real_url:
        track_info = await asyncio.to_thread(spotifydata.get_track_info, real_url)
        if track_info:
            await download_and_send_track(message, track_info, status_msg=status_msg, send_photo_msg=True)
        else:
            await status_msg.edit_text("❌ Track not found or invalid link.")
            
    # --- ALBUM ---
    elif "/album/" in real_url:
        type_str = "ALBUM"
        await status_msg.edit_text(f"🔍 Analyzing {type_str}...")
        
        tracks = await asyncio.to_thread(spotifydata.get_playlist_tracks, real_url)
        
        if not tracks:
            await status_msg.edit_text(f"❌ Failed to load {type_str}.")
            return

        count = len(tracks)
        await status_msg.edit_text(f"✅ Found {count} tracks. Starting download...")
        
        # Album Cover (send once)
        if count > 0:
            first_track = tracks[0]
            if first_track.get('cover_url'):
                temp_cover = "temp_album_cover.jpg"
                await asyncio.to_thread(spotifydata.download_cover, first_track['cover_url'], temp_cover, DOWNLOAD_DIR)
                full_cover_path = os.path.join(DOWNLOAD_DIR, temp_cover)
                if os.path.exists(full_cover_path):
                    await message.answer_photo(FSInputFile(full_cover_path), caption=f"💿 {first_track['artist']} - Album")
                    os.remove(full_cover_path)

        successful = 0
        for i, track in enumerate(tracks):
            # Don't send large photo again for albums
            result = await download_and_send_track(message, track, send_photo_msg=False)
            if result: successful += 1
            await asyncio.sleep(3)

        await message.answer(f"🏁 Done! Downloaded: {successful}/{count}")
    
    else:
        # If it's a playlist or artist, explain that we don't support it yet
        if "/playlist/" in real_url or "/artist/" in real_url:
             await status_msg.edit_text("⚠️ Sorry, I currently support only **Tracks** and **Albums**.")
        else:
             await status_msg.edit_text("🤔 Unknown Spotify link type.")

async def main():
    print("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
#test
