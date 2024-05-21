# Server-Management-Bot

Server-Management-Bot is a Telegram bot designed to manage servers and execute commands remotely over SSH (only passwords). It allows authorized users to add, delete, and list servers, as well as execute predefined commands or manually enter commands. The bot currently only supports passwords and usernames for server authentication. SSL key support is planned for a future update.

## Dependencies

- Python 3.7+
- aiogram
- aiosqlite
- cryptography
- fabric
- python-dotenv

## Installation

1. Clone the repository:

```bash
git clone https://github.com/egubaidullin/Server-Management-Bot
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root directory and add the following environment variables:

```
TELEGRAM_TOKEN=your_telegram_bot_token
ENCRYPTION_KEY=your_encryption_key
SSH_CONNECT_ATTEMPTS=3  # (optional, default: 3)
LOGGING_LEVEL=INFO  # (optional, default: INFO)
LOGGING_TARGET=3  # 1 - file, 2 - console, 3 - both (optional, default: 3)
ALLOWED_TELEGRAM_IDS=user1_id,user2_id  # Comma-separated list of allowed Telegram user IDs
SERVERS_PER_PAGE=20  # (optional, default: 20)
FAVORITE_COMMANDS_FILE=favorite_commands.txt  # (optional, default: favorite_commands.txt)
COMMAND_TIMEOUT=10  # (optional, default: 10)
```

Replace `your_telegram_bot_token` and `your_encryption_key` with your actual values.

4. Create a `roles.json` file in the project root directory with the following structure:

```json
{
  "admin": {
    "users": [telegram_id_1, telegram_id_2],
    "commands": []
  },
  "user_btn_access": {
    "users": [telegram_id_3, telegram_id_4],
    "commands": ["/start", "/list_servers", "/execute_command", "uptime", "df -h"]
  }
}
```

Replace `telegram_id_1`, `telegram_id_2`, `telegram_id_3`, and `telegram_id_4` with the actual Telegram user IDs. The `admin` role allows users to execute any command, while the `user_btn_access` role restricts users to execute specific commands listed in the `commands` array.

5. Create a `bot.db` file in the project root directory using the following command:

```bash
touch bot.db
```

This file will be used as the SQLite database to store server information.

## Usage

1. Run the bot:

```bash
python main.py
```

2. Start a conversation with the bot in Telegram and use the following commands:

- `/add_server`: Add a new server by providing the server name, IP address, port, login, and password.
- `/list_servers`: List all available servers.
- `/delete_server`: Delete an existing server by selecting its number from the list.
- `/execute_command`: Execute a command on a selected server from the list of favorite commands or manually enter a command.

## Customization

You can customize the list of favorite commands by editing the `favorite_commands.txt` file. The file should follow the format:

```
# Category
command1 | Description for command1
command2 | Description for command2
# Another Category
command3 | Description for command3
```

Each category should start with a `#` followed by the category name. Commands and their descriptions should be separated by a `|` character.
