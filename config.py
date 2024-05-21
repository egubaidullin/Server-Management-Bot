import os
from dotenv import load_dotenv
from typing import Set

load_dotenv()

def get_env_variable(var_name: str, default=None, required: bool = False):
    value = os.getenv(var_name, default)
    if required and value is None:
        raise EnvironmentError(f"Missing required environment variable: {var_name}")
    return value

TELEGRAM_TOKEN = get_env_variable('TELEGRAM_TOKEN', required=True)
ENCRYPTION_KEY = get_env_variable('ENCRYPTION_KEY', required=True)
SSH_CONNECT_ATTEMPTS = int(get_env_variable('SSH_CONNECT_ATTEMPTS', 3))
LOGGING_LEVEL = get_env_variable('LOGGING_LEVEL', 'INFO')
LOGGING_TARGET = int(get_env_variable('LOGGING_TARGET', 3))  # 1 - file, 2 - console, 3 - both
ALLOWED_TELEGRAM_IDS = {int(x) for x in get_env_variable('ALLOWED_TELEGRAM_IDS', '').split(',') if x.isdigit()}
SERVERS_PER_PAGE = int(get_env_variable('SERVERS_PER_PAGE', '20'))
