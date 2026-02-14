import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from dotenv import load_dotenv
import spotifydata

# Завантаження змінних середовища
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привіт, {message.from_user.first_name}! 👋\nНадішли посилання на трек Spotify.")

@dp.message(F.text.contains("open.spotify.com/track"))
async def handle_spotify_track(message: types.Message):
    status_msg = await message.answer("🔍 Шукаю інформацію про трек...")
    
    try:
        url = message.text.strip()
        
        # 1. Info
        track_info = await asyncio.to_thread(spotifydata.get_track_info, url)
        if not track_info:
            await status_msg.edit_text("❌ Не вдалося отримати дані з Spotify.")
            return

        await status_msg.edit_text(f"🎵 {track_info['full_name']}\n⬇️ Завантажую...")

        # 2. Cover
        # Прибираємо зайві символи з назви файлу
        safe_name = "".join([c for c in track_info['name'] if c.isalnum() or c in (' ', '.', '_')]).strip()
        cover_filename = f"{safe_name}_cover.jpg"
        
        cover_path = None
        if track_info['cover_url']:
            print(f"DEBUG: Downloading cover from {track_info['cover_url']}")
            cover_path = await asyncio.to_thread(spotifydata.download_cover, track_info['cover_url'], cover_filename, DOWNLOAD_DIR)

        # 3. Audio
        search_query = f"{track_info['artist']} - {track_info['name']}"
        print(f"DEBUG: Downloading audio for query: {search_query}")
        audio_path = await asyncio.to_thread(spotifydata.download_track, search_query, DOWNLOAD_DIR)

        if not audio_path or not os.path.exists(audio_path):
            await status_msg.edit_text("❌ Не вдалося завантажити аудіо.")
            return

        # 4. Embed cover inside MP3
        if cover_path and os.path.exists(cover_path):
             await asyncio.to_thread(spotifydata.set_mp3_cover, audio_path, cover_path)

        # 5. Send Files
        await status_msg.edit_text("uploading... 🚀")
        
        # Спочатку надсилаємо велике фото (якщо воно є)
        if cover_path and os.path.exists(cover_path):
            photo_file = FSInputFile(cover_path)
            await message.answer_photo(photo_file, caption=f"💿 Обкладинка: {track_info['full_name']}")

        # Потім надсилаємо аудіо
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

        # 6. Cleanup (Видалення файлів)
        await asyncio.sleep(1)
        try:
            print("DEBUG: Cleaning up temporary files...")
            os.remove(audio_path)
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)
            print("DEBUG: Cleanup complete.")
        except Exception as e:
            print(f"Cleanup error: {e}")

    except Exception as e:
        print(f"Global Error: {e}")
        await status_msg.edit_text(f"❌ Помилка: {e}")

async def main():
    print("Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зупинено.")
