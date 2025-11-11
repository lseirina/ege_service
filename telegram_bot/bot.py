import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://backend:8000"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

state = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот ЕГЭ. Команды: /reg /add /view")

@dp.message(Command("reg"))
async def reg(message: types.Message):
    await message.answer("Введите имя:")
    state[message.from_user.id] = "name"

@dp.message(Command("add"))
async def add(message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/subjects") as resp:
            subjects = await resp.json()
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=s)] for s in subjects],
        resize_keyboard=True
    )
    
    state[message.from_user.id] = "subject"
    await message.answer("Выберите предмет:", reply_markup=keyboard)

@dp.message(Command("view"))
async def view(message: types.Message):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/students/{message.from_user.id}") as resp:
            scores = await resp.json()
    
    if scores == "not found":
        await message.answer("Сначала /reg")
        return
    
    if not scores:
        await message.answer("Нет баллов")
        return
    
    text = "\n".join(f"{s['subject']}: {s['score']}" for s in scores)
    await message.answer(text)

@dp.message()
async def all_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id not in state:
        return
    
    if state[user_id] == "name":
        name = message.text
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/students/{user_id}/{name}") as resp:
                result = await resp.text()
                if result == "ok":
                    await message.answer("Успешно")
                else:
                    await message.answer("Ошибка")
        del state[user_id]
    
    elif state[user_id] == "subject":
        subject = message.text
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/subjects") as resp:
                subjects = await resp.json()
        
        if subject not in subjects:
            await message.answer("Выберите из списка")
            return
        
        state[user_id] = {"step": "score", "subject": subject}
        await message.answer("Введите балл:", reply_markup=types.ReplyKeyboardRemove())
    
    elif isinstance(state[user_id], dict) and state[user_id].get("step") == "score":
        try:
            score = int(message.text)
        except:
            await message.answer("Введите число")
            return
        
        subject = state[user_id]["subject"]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/scores/{user_id}/{subject}/{score}") as resp:
                result = await resp.text()
                if result == "ok":
                    await message.answer("Сохранено")
                else:
                    await message.answer("Ошибка")
        del state[user_id]

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))