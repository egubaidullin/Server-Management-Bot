from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from models import Server
from db import encrypt_password
import aiosqlite
import ipaddress
import logging


class ServerForm(StatesGroup):
    name = State()
    ip = State()
    port = State()
    login = State()
    password = State()

class DeleteServerForm(StatesGroup):
    server_id = State()

async def cmd_delete_server(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT id, name, ip FROM servers') as cursor:
            servers = await cursor.fetchall()
            if servers:
                server_list = "\n".join([f"{i+1}. {row[1]} ({row[2]})" for i, row in enumerate(servers)])
                await message.reply(f"Available servers:\n{server_list}\n\nEnter the number of the server to delete:")
                await state.set_state(DeleteServerForm.server_id)
            else:
                await message.reply("No servers found.")

async def process_delete_server_id(message: types.Message, state: FSMContext):
    try:
        server_number = int(message.text)
        async with aiosqlite.connect('bot.db') as db:
            async with db.execute('SELECT id FROM servers') as cursor:
                server_ids = await cursor.fetchall()
                if 0 < server_number <= len(server_ids):
                    server_id = server_ids[server_number - 1][0]
                    await db.execute('DELETE FROM servers WHERE id = ?', (server_id,))
                    await db.commit()
                    await message.reply(f"Server #{server_number} deleted successfully.")
                else:
                    await message.reply("Invalid server number.")
    except ValueError:
        await message.reply("Invalid input. Please enter a number.")
    finally:
        await state.clear()

async def cmd_add_server(message: types.Message, state: FSMContext):
    await state.set_state(ServerForm.name)
    await message.reply("Enter server name:")

async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.reply("Server name is done.\nEnter server IPv4 address:")
    await message.delete()
    await state.set_state(ServerForm.ip)

async def process_ip(message: types.Message, state: FSMContext):
    try:
        ipaddress.IPv4Address(message.text)
        await state.update_data(ip=message.text)
        await message.reply("IPv4 address is done.\nEnter server port:")
        await message.delete()
        await state.set_state(ServerForm.port)
    except ipaddress.AddressValueError:
        await message.reply("Invalid IPv4 address. Please enter a valid IPv4 address.")

async def process_port(message: types.Message, state: FSMContext):
    try:
        port = int(message.text)
        if 1 <= port <= 65535:
            await state.update_data(port=port)
            await message.reply("Server port is done.\nEnter login (alphanumeric characters and underscore):")
            await message.delete()
            await state.set_state(ServerForm.login)
        else:
            await message.reply("Invalid port number. Please enter a port between 1 and 65535.")
    except ValueError:
        await message.reply("Invalid port number. Please enter a number.")

async def process_login(message: types.Message, state: FSMContext):
    if message.text.isalnum() or "_" in message.text:
        await state.update_data(login=message.text)
        await message.reply("Login is done.\nEnter password:")
        await message.delete()
        await state.set_state(ServerForm.password)
    else:
        await message.reply("Invalid login. Please use only alphanumeric characters and underscore.")

async def process_password(message: types.Message, state: FSMContext):
    await state.update_data(password=await encrypt_password(message.text))
    user_data = await state.get_data()

    try:
        async with aiosqlite.connect('bot.db') as db:
            await db.execute('''
                INSERT INTO servers (name, ip, port, login, password) VALUES (?, ?, ?, ?, ?)
            ''', (user_data['name'], user_data['ip'], user_data['port'], user_data['login'], user_data['password']))
            await db.commit()

        await state.clear()

        server_info = f"**Server added:**\n" \
                       f"Name: {user_data['name']}\n" \
                       f"IP: {user_data['ip']}\n" \
                       f"Port: {user_data['port']}\n" \
                       f"Login: {user_data['login']}\n"
        await message.reply(server_info, parse_mode="Markdown")

        await message.delete()

    except Exception as e:
        logging.error(f"Failed to add server: {e}")
        await message.reply("Failed to add server. Please try again later.")

def register_handlers_server_management(dp: Dispatcher):
    dp.message.register(cmd_add_server, Command(commands='add_server'))
    dp.message.register(cmd_delete_server, Command(commands='delete_server'))
    dp.message.register(process_name, ServerForm.name)
    dp.message.register(process_ip, ServerForm.ip)
    dp.message.register(process_port, ServerForm.port)
    dp.message.register(process_login, ServerForm.login)
    dp.message.register(process_password, ServerForm.password)
    dp.message.register(process_delete_server_id, DeleteServerForm.server_id)
