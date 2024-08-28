from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.filters.base import Filter
import ipapi


class LocationFilter(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.location is not None


async def cmd_get_location(message: types.Message):
    await message.reply("Please share your location with me.", reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Share Location", request_location=True)]
        ],
        resize_keyboard=True
    ))


async def process_location(message: types.Message):
    if message.location:
        ip_info = ipapi.location(ip=None, output='json')
        if ip_info:
            formatted_info = (
                f"🌐 **IP Information**\n"
                f"🔹 **IP:** {ip_info['ip']}\n"
                f"🔹 **City:** {ip_info['city']}\n"
                f"🔹 **Region:** {ip_info['region']}\n"
                f"🔹 **Country:** {ip_info['country_name']} ({ip_info['country']})\n"
                f"🔹 **Latitude:** {ip_info['latitude']}\n"
                f"🔹 **Longitude:** {ip_info['longitude']}\n"
                f"🔹 **Timezone:** {ip_info['timezone']}\n"
                f"🔹 **Currency:** {ip_info['currency_name']} ({ip_info['currency']})\n"
                f"🔹 **Languages:** {ip_info['languages']}\n"
                f"🔹 **ASN:** {ip_info['asn']}\n"
                f"🔹 **Organization:** {ip_info['org']}\n"
            )
            await message.reply(formatted_info, parse_mode="Markdown")
        else:
            await message.reply("Failed to retrieve IP information.")
    else:
        await message.reply("Location not received. Please try again.")


def register_handlers_location(dp: Dispatcher):
    dp.message.register(cmd_get_location, Command(commands=["get_location"]))
    dp.message.register(process_location, LocationFilter())
