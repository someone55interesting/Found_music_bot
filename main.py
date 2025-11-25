import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from shazamio import Shazam

# --- НАСТРОЙКИ ---
# Получи токен у @BotFather в Telegram и вставь сюда внутрь кавычек
TOKEN = os.getenv("BOT_TOKEN")

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

# --- ХЭНДЛЕР: ПРИВЕТСТВИЕ ---
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "Привет, бро! 🎧\n"
        "Я бесплатный музыкальный бот.\n\n"
        "1. Отправь мне **название песни**, и я найду её.\n"
        "2. Отправь мне **голосовое** или **аудиофайл** с музыкой, и я скажу, что это играет."
    )

# --- ХЭНДЛЕР: ПОИСК ПО ТЕКСТУ ---
@dp.message(F.text)
async def search_by_text(message: Message):
    query = message.text
    await message.answer(f"🔎 Ищу: {query}...")
    
    try:
        # Ищем треки
        search_results = await shazam.search_track(query=query, limit=1)
        
        # Разбираем результат (немного json магии)
        if search_results and 'tracks' in search_results and 'hits' in search_results['tracks']:
            track = search_results['tracks']['hits'][0]
            title = track['heading']['title']
            artist = track['heading']['subtitle']
            
            # Можно вытащить картинку и ссылку, но пока дадим просто текст
            response = f"🎵 **Нашел!**\n\n🎤 Артист: {artist}\n🎼 Трек: {title}"
            
            # Если есть ссылка на фото обложки
            image_url = track['images'].get('default')
            if image_url:
                await message.answer_photo(image_url, caption=response)
            else:
                await message.answer(response)
        else:
            await message.answer("Ничего не нашел, брат. Попробуй по-другому.")
            
    except Exception as e:
        await message.answer(f"Ошибка при поиске: {e}")

# --- ХЭНДЛЕР: РАСПОЗНАВАНИЕ ФАЙЛА (ГОЛОС ИЛИ АУДИО) ---
@dp.message(F.content_type.in_({'voice', 'audio', 'document'}))
async def recognize_file(message: Message):
    await message.answer("👂 Слушаю... дай секунду.")
    
    # Определяем файл
    if message.voice:
        file_id = message.voice.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.document:
         # Проверка, что документ — это аудио (по mime_type)
        if 'audio' in message.document.mime_type:
            file_id = message.document.file_id
        else:
            await message.answer("Брат, это не музыкальный файл.")
            return
    else:
        return

    # Скачиваем файл во временную папку
    file = await bot.get_file(file_id)
    file_path = f"temp_{file_id}.ogg"
    await bot.download_file(file.file_path, file_path)

    try:
        # Распознаем через ShazamIO
        out = await shazam.recognize_song(file_path)
        
        if out and 'track' in out:
            track_info = out['track']
            title = track_info['title']
            artist = track_info['subtitle']
            image_url = track_info['images'].get('coverart')
            
            caption = f"🎧 **Распознал!**\n\n🎤 Артист: {artist}\n🎼 Трек: {title}"
            
            if image_url:
                await message.answer_photo(image_url, caption=caption)
            else:
                await message.answer(caption)
        else:
            await message.answer("Не смог распознать, слишком много шума или трек редкий.")
            
    except Exception as e:
        await message.answer("Произошла ошибка при распознавании.")
        print(e)
    finally:
        # Удаляем временный файл, чтобы не засорять память
        if os.path.exists(file_path):
            os.remove(file_path)

# --- ЗАПУСК ---
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())