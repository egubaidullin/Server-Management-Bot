# user.py
import json

class User:
    def __init__(self, telegram_id: int, role: str):
        self.telegram_id = telegram_id
        self.role = role

    @staticmethod
    def load_roles(file_path: str = 'roles.json'):
        with open(file_path, 'r') as file:
            return json.load(file)

    @classmethod
    def get_user_role(cls, telegram_id: int):
        roles = cls.load_roles()
        for role, details in roles.items():
            if telegram_id in details['users']:
                return role
        return None

    def has_permission(self, command: str):
        if self.role == 'admin':
            return True  # Admins can execute any command

        roles = self.load_roles()
        return command in roles[self.role]['commands']