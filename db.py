import aiosqlite
from cryptography.fernet import Fernet
from config import ENCRYPTION_KEY

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

async def encrypt_password(password: str) -> str:
    return cipher_suite.encrypt(password.encode()).decode()

async def decrypt_password(encrypted_password: str) -> str:
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

async def init_db() -> None:
    try:
        async with aiosqlite.connect('bot.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    ip TEXT,
                    port INTEGER,
                    login TEXT,
                    password TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE
                )
            ''')
            await db.commit()
    except Exception as e:
        print(f"Failed to initialize the database: {e}")
