import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://backend:8000"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

state = {}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот ЕГЭ. Команды: /register /enter_scores /view_scores")

@dp.message(Command("register"))
async def register(message: types.Message):
    logger.info(f"User {message.from_user.id} started registration")
    await message.answer("Введите имя:")
    state[message.from_user.id] = "name"

@dp.message(Command("enter_scores"))
async def enter_scores(message: types.Message):
    logger.info(f"User {message.from_user.id} started entering scores")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/subjects") as resp:
            subjects = await resp.json()
    
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=s)] for s in subjects],
        resize_keyboard=True
    )
    
    state[message.from_user.id] = "subject"
    await message.answer("Выберите предмет:", reply_markup=keyboard)

@dp.message(Command("view_scores"))
async def view_scores(message: types.Message):
    logger.info(f"User {message.from_user.id} requested to view scores")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/students/{message.from_user.id}") as resp:
            result = await resp.text()
    
    if result == "not found":
        logger.warning(f"User {message.from_user.id} tried to view scores but not registered")
        await message.answer("Сначала /reg")
        return
    
    scores = eval(result) if result != "not found" else []
    
    if not scores:
        logger.info(f"User {message.from_user.id} has no scores yet")
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
                if "ok" in result:
                    logger.info(f"User {user_id} registered successfully with name: {name}")
                    await message.answer("Успешно")
                elif "already_exists":
                    logger.info(f"User {user_id} already registered, tried to change name to: {name}")
                    await message.answer("вы уже зарегистрированы")
                else:
                    logger_error(f"Registration errro for user {user_id}: {result}")
                    await message.answer("Ошибка регистрации")
        del state[user_id]
    
    elif state[user_id] == "subject":
        subject = message.text
        logger.info(f"User {user_id} selected subject: {subject}")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/subjects") as resp:
                subjects = await resp.json()
        
        if subject not in subjects:
            logger.warning(f"User {user_id} selected invalid subject: {subject}")
            await message.answer("Выберите из списка")
            return
        
        state[user_id] = {"step": "score", "subject": subject}
        await message.answer("Введите балл:", reply_markup=types.ReplyKeyboardRemove())
    
    elif isinstance(state[user_id], dict) and state[user_id].get("step") == "score":
        try:
            score = int(message.text)
            if not 0 <= score <= 100:
                logger.warning(f"User {user_id} entered invalid score: {score}")
                await message.answer("Баллы должны быть от 0 до 100")
                return
        except:
            logger.warning(f"User {user_id} entered non-numeric score: {message.text}")
            await message.answer("Введите число")
            return
        
        subject = state[user_id]["subject"]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/scores/{user_id}/{subject}/{score}") as resp:
                result = await resp.text()
                if "ok" in result:
                    logger.info(f"User {user_id} successfully saved score {score} for {subject}")
                    await message.answer("Сохранено")
                else:
                    logger.error(f"Score save error for user {user_id}: {result}")
                    await message.answer("Ошибка сохранения")
        del state[user_id]

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))