import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from shazamio import Shazam
from typing import Optional, Tuple

# Берем токен из переменных окружения (безопасно)
TOKEN = os.getenv("BOT_TOKEN") 
# Если запускаешь локально и лень настраивать env, раскомментируй строку ниже и вставь токен:

bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

# =============================
# Форматирование результата
# =============================
def format_track_info(track_data: dict) -> Tuple[str, Optional[str], Optional[str]]:
    title = track_data.get("title", "Неизвестно")
    subtitle = track_data.get("subtitle", "")
    image = track_data.get("images", {}).get("coverart")
    url = track_data.get("url", "")

    text = f"🎵 <b>{title}</b>\n👤 {subtitle}\n\n"
    if url:
        text += f"🔗 <a href=\"{url}\">Слушать</a>"

    return text, image, url

# =============================
# Анализ файла (универсальная функция)
# =============================
async def process_and_recognize(message: Message, file_id: str, file_ext: str):
    # Создаем уникальное имя файла
    file_path = f"temp_{file_id}{file_ext}"
    
    try:
        # 1. Скачиваем файл
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_path)
        
        # 2. Распознаем через Shazam
        # ВАЖНО: Для работы с .mp4 нужен установленный FFmpeg в системе!
        out = await shazam.recognize_song(file_path)
        
        # 3. Проверяем результат
        if out and 'track' in out:
            track = out['track']
            text, image, _ = format_track_info(track)
            if image:
                await message.answer_photo(photo=image, caption=text, parse_mode="HTML")
            else:
                await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("🤷‍♂️ Не смог распознать этот трек.")
            
    except Exception as e:
        print(f"ОШИБКА ПРИ РАСПОЗНАВАНИИ: {e}") # Смотри сюда в терминале!
        await message.answer("⚠ Произошла ошибка при обработке файла.")
        
    finally:
        # 4. Удаляем файл, даже если была ошибка
        if os.path.exists(file_path):
            os.remove(file_path)

# =============================
# Хэндлеры
# =============================

@dp.message(F.text == "/start")
async def start_cmd(msg: Message):
    await msg.answer("👋 Привет! Кидай мне музыку, видео или голосовое, я найду трек.")

@dp.message(F.text)
async def search_by_text(msg: Message):
    try:
        res = await shazam.search_track(msg.text)
        if res and "tracks" in res and "hits" in res["tracks"] and res["tracks"]["hits"]:
            track = res["tracks"]["hits"][0]["track"]
            text, image, _ = format_track_info(track)
            await msg.answer_photo(photo=image, caption=text, parse_mode="HTML")
        else:
            await msg.answer("❌ Ничего не найдено.")
    except Exception as e:
        print(f"Ошибка поиска текста: {e}")
        await msg.answer("⚠ Ошибка при поиске.")

@dp.message(F.voice)
async def voice_handler(msg: Message):
    await msg.answer("🎧 Слушаю голосовое...")
    await process_and_recognize(msg, msg.voice.file_id, ".ogg")

@dp.message(F.audio)
async def audio_handler(msg: Message):
    await msg.answer("🎧 Слушаю аудио...")
    await process_and_recognize(msg, msg.audio.file_id, ".mp3")

@dp.message(F.video)
async def video_handler(msg: Message):
    await msg.answer("👀 Смотрю видео и слушаю...")
    # Сохраняем как mp4. Shazamio сам вытащит звук, если есть FFmpeg
    await process_and_recognize(msg, msg.video.file_id, ".mp4")

@dp.message(F.document)
async def doc_handler(msg: Message):
    # Обработка файлов, отправленных как документ
    if msg.document.mime_type and 'audio' in msg.document.mime_type:
        await msg.answer("🎧 Анализирую файл...")
        await process_and_recognize(msg, msg.document.file_id, ".mp3")
    elif msg.document.mime_type and 'video' in msg.document.mime_type:
        await msg.answer("👀 Анализирую видео-файл...")
        await process_and_recognize(msg, msg.document.file_id, ".mp4")
    else:
        await msg.answer("Это не похоже на музыку или видео.")

# =============================
# Запуск
# =============================
async def main():
    print("Bot started! 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
