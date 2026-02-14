import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Налаштування логування (щоб бачити помилки в консолі)
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота та диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Обробник команди /start
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(f"Привіт, {message.from_user.first_name}! 👋\n\n"
                         "Надішли мені посилання на трек або плейлист Spotify, "
                         "і я спробую його завантажити.")

# Обробник текстових повідомлень (фільтр на посилання Spotify)
@dp.message(F.text.contains("open.spotify.com"))
async def handle_spotify_link(message: types.Message):
    await message.answer("🔍 Посилання отримано! Починаю обробку...")
    
    try:
        # TODO: Інтеграція з другом (spotifydata.py)
        # Тут ви викличете функцію твого друга. Оскільки aiogram асинхронний,
        # а бібліотеки для скачування часто синхронні, краще запускати їх в окремому потоці,
        # щоб бот не "тупив".
        
        # Приклад (поки закоментований):
        # track_info = await asyncio.to_thread(spotifydata.get_track_info, message.text)
        # file_path = await asyncio.to_thread(spotifydata.download_track, message.text)
        
        # await message.reply_document(types.FSInputFile(file_path))
        
        # Тимчасова відповідь:
        await message.answer("✅ (Тут буде файл з піснею, коли твій друг допише spotifydata.py)")
        
    except Exception as e:
        await message.answer(f"❌ Сталася помилка: {e}")

# Обробник будь-якого іншого тексту
@dp.message()
async def echo_handler(message: types.Message):
    await message.answer("Це не схоже на посилання Spotify. Спробуй ще раз! 🎵")

# Запуск бота
async def main():
    print("Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зупинено.")