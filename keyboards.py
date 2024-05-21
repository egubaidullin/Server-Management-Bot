from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/add_server"), KeyboardButton(text="/list_servers")],
        [KeyboardButton(text="/delete_server"), KeyboardButton(text="/execute_command")]
    ],
    resize_keyboard=True
)
