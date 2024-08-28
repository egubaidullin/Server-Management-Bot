import logging
import asyncio
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram.types import Message

from db import init_db
from config import TELEGRAM_TOKEN, LOGGING_LEVEL, LOGGING_TARGET
from keyboards import main_keyboard
from access_middleware import AccessMiddleware
import server_management
import command_execution
import webapp_handler
from utils import setup_logging

setup_logging(LOGGING_LEVEL, LOGGING_TARGET & 1, LOGGING_TARGET & 2)

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.message.middleware(AccessMiddleware())


async def on_startup(dispatcher):
    await init_db()


async def send_welcome(message: types.Message):
    await message.answer("Welcome to the Server Management Bot!", reply_markup=main_keyboard)


dp.message.register(send_welcome, CommandStart())

server_management.register_handlers_server_management(dp)
command_execution.register_handlers_command_execution(dp)
webapp_handler.register_handlers_webapp(dp)


async def main():
    await on_startup(dp)
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
