import os
import logging
from dotenv import load_dotenv
from fabric import Connection
from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
import re

from db import decrypt_password
import aiosqlite
from config import SERVERS_PER_PAGE

load_dotenv()

FAVORITE_COMMANDS_FILE = os.getenv("FAVORITE_COMMANDS_FILE", "favorite_commands.txt")
COMMAND_TIMEOUT = os.getenv("COMMAND_TIMEOUT", 10)

class ServerCallback(CallbackData, prefix="server"):
    id: int

class CommandCallback(CallbackData, prefix="command"):
    category: str
    command: str
    server_id: int

class PaginationCallback(CallbackData, prefix="page"):
    page: int

class CommandForm(StatesGroup):
    server_id = State()
    command = State()

class ManualCommandForm(StatesGroup):
    command = State()

async def cmd_execute_command(message: types.Message, state: FSMContext):
    await message.reply("Choose a server from the list:")
    await show_servers_for_selection(message, state)

async def show_servers_for_selection(message: types.Message, state: FSMContext, page: int = 1):
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT id, name, ip FROM servers') as cursor:
            servers = await cursor.fetchall()

            if not servers:
                await message.reply("No servers found.")
                return

            total_pages = (len(servers) + SERVERS_PER_PAGE - 1) // SERVERS_PER_PAGE
            start_index = (page - 1) * SERVERS_PER_PAGE
            end_index = min(start_index + SERVERS_PER_PAGE, len(servers))

            server_list = ""
            for i in range(start_index, end_index):
                server_list += f"{i + 1}. {servers[i][1]} ({servers[i][2]})\n"

            buttons = [
                types.InlineKeyboardButton(text=str(i + 1),
                                           callback_data=ServerCallback(id=servers[i][0]).pack())
                for i in range(start_index, end_index)
            ]

            pagination_buttons = []
            if page > 1:
                pagination_buttons.append(
                    types.InlineKeyboardButton(text="Previous",
                                               callback_data=PaginationCallback(page=page - 1).pack()))
            if page < total_pages:
                pagination_buttons.append(
                    types.InlineKeyboardButton(text="Next", callback_data=PaginationCallback(page=page + 1).pack()))

            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
            if pagination_buttons:
                keyboard.inline_keyboard.append(pagination_buttons)

            await message.reply(f"Servers (Page {page}/{total_pages}):\n{server_list}", reply_markup=keyboard)

async def show_favorite_commands(message: types.Message, server_id: int):
    commands = {}
    try:
        with open(FAVORITE_COMMANDS_FILE, 'r', encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    current_category = line[1:].strip()
                    commands[current_category] = []
                elif line:
                    command, description = line.split("|", 1)
                    commands[current_category].append((command.strip(), description.strip()))
    except FileNotFoundError:
        await message.reply(f"File '{FAVORITE_COMMANDS_FILE}' not found. Enter command manually:")
        await message.answer()
        return

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for category, category_commands in commands.items():
        buttons = [
            types.InlineKeyboardButton(
                text=f"{command} - {description}",
                callback_data=CommandCallback(category=category, command=command, server_id=server_id).pack()
            )
            for command, description in category_commands
        ]

        for button in buttons:
            keyboard.inline_keyboard.append([button])

    keyboard.inline_keyboard.append([types.InlineKeyboardButton(
        text="Enter command manually",
        callback_data=CommandCallback(category='manual', command='manual', server_id=server_id).pack()
    )])

    await message.reply("Choose a command to execute:", reply_markup=keyboard)


async def execute_command_with_timeout(conn: Connection, command: str):
    try:
        timeout = int(os.getenv("COMMAND_TIMEOUT", "10"))
        logging.info(f"Executing command '{command}' with timeout {timeout} seconds")
        result = conn.run(command, hide=True, warn=True, timeout=timeout)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = f"```{stdout}```\n" if stdout else ""
        output += f"```{stderr}```" if stderr else ""
        # Добавление отладочной информации
        logging.info(f"Command stdout: {stdout}")
        logging.info(f"Command stderr: {stderr}")
        return output
    except ValueError:
        logging.error(f"Invalid timeout value: {os.getenv('COMMAND_TIMEOUT')}")
        return "Invalid timeout value."
    except Exception as e:
        return f"Failed to execute command: {str(e)}"



async def process_command_selection(callback_query: types.CallbackQuery, callback_data: CommandCallback, state: FSMContext):
    server_id = callback_data.server_id
    command = callback_data.command

    if callback_data.category == 'manual' and command == 'manual':
        # Handle manual command input
        await state.update_data(server_id=server_id)
        await state.set_state(ManualCommandForm.command)
        await callback_query.message.reply("Enter the command you want to execute:")
        await callback_query.answer()
        return  # Stop further processing

    # Execute command from favorite commands file
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT ip, port, login, password FROM servers WHERE id = ?', (server_id,)) as cursor:
            server = await cursor.fetchone()
            if server:
                ip, port, login, password = server
                password = await decrypt_password(password)
                conn = Connection(host=ip, user=login, port=port, connect_kwargs={"password": password})
                try:
                    output = await execute_command_with_timeout(conn, command)
                    await callback_query.message.reply(output, parse_mode="Markdown")
                except Exception as e:
                    await callback_query.message.reply(f"Failed to execute command: {str(e)}")
                finally:
                    conn.close()

    await callback_query.answer()


async def process_manual_command(callback_query: types.CallbackQuery, state: FSMContext):
    callback_data = CommandCallback.unpack(callback_query.data)
    await state.update_data(server_id=callback_data.server_id)
    await state.set_state(ManualCommandForm.command)
    await callback_query.message.reply("Enter the command you want to execute:")
    await callback_query.answer()

async def process_manual_command_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_data = await state.get_data()
    if 'server_id' not in user_data:
        await message.reply("Error: Server ID not found. Please start the process again.")
        await state.clear()
        return

    server_id = user_data['server_id']
    command = message.text.strip()

    # Validate and sanitize input
    if not command:
        await message.reply("Please enter a command.")
        return

    if not re.match(r"^[a-zA-Z0-9_\s\.\/\-]+$", command):
        await message.reply("Invalid characters in command.")
        return

    # Get user role
    user = data.get('user')
    if user and user.role != 'admin':
        # Dynamically create whitelist from FAVORITE_COMMANDS_FILE
        allowed_commands = []
        try:
            with open(FAVORITE_COMMANDS_FILE, 'r', encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("#") and "|" in line:
                        allowed_commands.append(line.split("|", 1)[0].strip())
        except FileNotFoundError:
            await message.reply(f"File '{FAVORITE_COMMANDS_FILE}' not found.")
            return

        # Check against whitelist
        if command not in allowed_commands:
            await message.reply("This command is not allowed.")
            return

    # Execute command
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT ip, port, login, password FROM servers WHERE id = ?', (server_id,)) as cursor:
            server = await cursor.fetchone()
            if server:
                ip, port, login, password = server
                password = await decrypt_password(password)
                conn = Connection(host=ip, user=login, port=port, connect_kwargs={"password": password})
                try:
                    output = await execute_command_with_timeout(conn, command)
                    output = re.sub(r"^```|```$", "", output)  # Remove leading and trailing ```
                    # await message.reply(f"```\n{output}\n```", parse_mode="Markdown")
                    await message.reply(f"<pre>\n{output}\n</pre>", parse_mode="HTML")
                except Exception as e:
                    await message.reply(f"Failed to execute command: {str(e)}")
                finally:
                    conn.close()

    await state.clear()

async def process_server_selection(callback_query: types.CallbackQuery, callback_data: ServerCallback,
                                   state: FSMContext):
    await state.update_data(server_id=callback_data.id)
    await show_favorite_commands(callback_query.message, callback_data.id)
    await callback_query.answer()

async def process_pagination(callback_query: types.CallbackQuery, callback_data: PaginationCallback,
                             state: FSMContext):
    await show_servers_for_selection(callback_query.message, state, callback_data.page)
    await callback_query.answer()

def register_handlers_command_execution(dp: Dispatcher):
    dp.message.register(cmd_execute_command, Command(commands=["execute_command"]))
    dp.callback_query.register(process_command_selection, CommandCallback.filter())
    dp.callback_query.register(process_manual_command, lambda c: c.data.startswith("command:manual"))
    dp.message.register(process_manual_command_input, ManualCommandForm.command)
    dp.callback_query.register(process_pagination, PaginationCallback.filter())
    dp.callback_query.register(process_server_selection, ServerCallback.filter())