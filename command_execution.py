import os
import logging
from dotenv import load_dotenv
from fabric import Connection
from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import re
import xml.etree.ElementTree as ET
import hashlib

from db import decrypt_password
import aiosqlite
from config import SERVERS_PER_PAGE


load_dotenv()
FAVORITE_COMMANDS_FILE = os.getenv("FAVORITE_COMMANDS_FILE", "favorite_commands.xml")
COMMAND_TIMEOUT = os.getenv("COMMAND_TIMEOUT", 10)
TELEGRAM_MESSAGE_CHUNK_SIZE = int(os.getenv("TELEGRAM_MESSAGE_CHUNK_SIZE", 4096))

# Create a mapping of command IDs to commands
COMMAND_MAP = {}

class ServerCallback(CallbackData, prefix="server"):
    id: int

class CommandCallback(CallbackData, prefix="command"):
    category: str
    command: str
    server_id: int

class CommandCallback(CallbackData, prefix="cmd"):
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

def generate_command_id(command: str) -> str:
    """Generates a short unique ID for a command."""
    command_id = hashlib.md5(command.encode()).hexdigest()[:8]  # Use only the first 8 characters for brevity
    COMMAND_MAP[command_id] = command
    return command_id

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
        if not os.path.exists(FAVORITE_COMMANDS_FILE):
            raise FileNotFoundError(f"File '{FAVORITE_COMMANDS_FILE}' does not exist.")
        
        tree = ET.parse(FAVORITE_COMMANDS_FILE)
        root = tree.getroot()
        
        if root.tag != "commands":
            raise ValueError("Invalid XML structure: root element should be 'commands'")
        
        for category in root.findall('category'):
            category_name = category.get('name')
            if not category_name:
                logging.warning("Found category without name, skipping")
                continue
            
            commands[category_name] = []
            for command in category.findall('command'):
                name_elem = command.find('name')
                desc_elem = command.find('description')
                if name_elem is not None and desc_elem is not None:
                    name = name_elem.text
                    description = desc_elem.text
                    if name and description:
                        commands[category_name].append((name.strip(), description.strip()))
                    else:
                        logging.warning(f"Skipping command in category '{category_name}' due to missing name or description")
                else:
                    logging.warning(f"Skipping command in category '{category_name}' due to missing name or description element")
        
        if not commands:
            raise ValueError("No valid commands found in the XML file")
        
    except FileNotFoundError as e:
        await message.reply(f"{str(e)} Enter command manually:")
        return
    except ET.ParseError as e:
        await message.reply(f"Error parsing '{FAVORITE_COMMANDS_FILE}': {str(e)}. Enter command manually:")
        return
    except ValueError as e:
        await message.reply(f"{str(e)}. Enter command manually:")
        return
    except Exception as e:
        logging.exception("Unexpected error while parsing favorite commands")
        await message.reply(f"An unexpected error occurred. Enter command manually:")
        return

    builder = InlineKeyboardBuilder()
    for category, category_commands in commands.items():
        for command, description in category_commands:
            command_id = generate_command_id(command)
            builder.button(
                text=f"{command} - {description}",
                callback_data=CommandCallback(category=category, command=command_id, server_id=server_id).pack()
            )
    
    builder.button(
        text="Enter command manually",
        callback_data=CommandCallback(category='manual', command='manual', server_id=server_id).pack()
    )

    builder.adjust(1)  # One button per row

    await message.reply("Choose a command to execute:", reply_markup=builder.as_markup())


async def execute_command_with_timeout(conn: Connection, command: str):
    try:
        timeout = int(os.getenv("COMMAND_TIMEOUT", "10"))
        logging.info(f"Executing command '{command}' with timeout {timeout} seconds")
        result = conn.run(command, hide=True, warn=True, timeout=timeout)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        output = f"```{stdout}```\n" if stdout else ""
        output += f"```{stderr}```" if stderr else ""
        # Log the output for debugging
        logging.info(f"Command stdout: {stdout}")
        logging.info(f"Command stderr: {stderr}")

        # Split output into chunks of 4096 characters each
        chunks = [output[i:i+TELEGRAM_MESSAGE_CHUNK_SIZE] for i in range(0, len(output), TELEGRAM_MESSAGE_CHUNK_SIZE)]

        return chunks
    except ValueError:
        logging.error(f"Invalid timeout value: {os.getenv('COMMAND_TIMEOUT')}")
        return ["Invalid timeout value."]
    except Exception as e:
        return [f"Failed to execute command: {str(e)}"]



async def process_command_selection(callback_query: types.CallbackQuery, callback_data: CommandCallback, state: FSMContext):
    server_id = callback_data.server_id
    command_id = callback_data.command

    if callback_data.category == 'manual' and command_id == 'manual':
        # Handle manual command input
        await state.update_data(server_id=server_id)
        await state.set_state(ManualCommandForm.command)
        await callback_query.message.reply("Enter the command you want to execute:")
        await callback_query.answer()
        return  # Stop further processing

    # Retrieve the full command using the command_id
    command = COMMAND_MAP.get(command_id)

    # Execute command from favorite commands file
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute('SELECT ip, port, login, password FROM servers WHERE id = ?', (server_id,)) as cursor:
            server = await cursor.fetchone()
            if server:
                ip, port, login, password = server
                password = await decrypt_password(password)
                conn = Connection(host=ip, user=login, port=port, connect_kwargs={"password": password})
                try:
                    output_chunks = await execute_command_with_timeout(conn, command)
                    formatted_output_chunks = [f"<pre><code>{chunk.strip('`')}</code></pre>" for chunk in output_chunks]  # Format each chunk as code using HTML and remove backticks
                    for chunk in formatted_output_chunks:
                        await callback_query.message.reply(chunk, parse_mode="HTML")
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
            if not os.path.exists(FAVORITE_COMMANDS_FILE):
                raise FileNotFoundError(f"File '{FAVORITE_COMMANDS_FILE}' does not exist.")
            
            tree = ET.parse(FAVORITE_COMMANDS_FILE)
            root = tree.getroot()
            for command_elem in root.findall('.//command/name'):
                if command_elem.text:
                    allowed_commands.append(command_elem.text.strip())
            
            if not allowed_commands:
                raise ValueError("No valid commands found in the XML file")
            
        except FileNotFoundError as e:
            await message.reply(f"{str(e)}")
            return
        except ET.ParseError as e:
            await message.reply(f"Error parsing '{FAVORITE_COMMANDS_FILE}': {str(e)}")
            return
        except ValueError as e:
            await message.reply(f"{str(e)}")
            return
        except Exception as e:
            logging.exception("Unexpected error while parsing favorite commands")
            await message.reply("An unexpected error occurred while processing your command.")
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
                    output_chunks = await execute_command_with_timeout(conn, command)
                    for chunk in output_chunks:
                        await message.reply(chunk)
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