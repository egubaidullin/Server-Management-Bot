from aiogram import types, Dispatcher
from aiogram.filters import Command
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cmd_open_webapp(message: types.Message):
    logger.info(f"User {message.from_user.id} requested to open WebApp")
    await message.answer("Please open the WebApp:", reply_markup=types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Open WebApp",
                                        web_app=types.WebAppInfo(url="https://calixtemayoraz.gitlab.io/web-interfacer-bot/"))] # Updated URL
        ]
    ))


async def process_web_app_data(message: types.Message):
    logger.info(f"Received message: {message}")
    if message.web_app_data:
        logger.info(f"Received WebApp data from user {message.from_user.id}")
        try:
            if message.web_app_data.data:
                logger.info(f"Raw WebApp data: {message.web_app_data.data}")
                data = json.loads(message.web_app_data.data)
                logger.info(f"Parsed data: {data}")

                # Extract data and display it
                firstname = data.get('firstname', '')
                lastname = data.get('lastname', '')
                username = data.get('username', '')

                await message.answer(f"Received data:\nFirstname: {firstname}\nLastname: {lastname}\nUsername: {username}")

            else:
                logger.warning("message.web_app_data.data is None")
                await message.answer("No WebApp data received. Please try again.")
        except json.JSONDecodeError:
            logger.error("Failed to parse WebApp data")
            await message.answer("Failed to parse WebApp data. Please try again.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            await message.answer(f"An unexpected error occurred. Please try again later.")
    else:
        logger.info("Message does not contain web_app_data")



def register_handlers_webapp(dp: Dispatcher):
    dp.message.register(cmd_open_webapp, Command(commands=["webapp"]))
    dp.message.register(process_web_app_data, lambda message: message.web_app_data is not None)