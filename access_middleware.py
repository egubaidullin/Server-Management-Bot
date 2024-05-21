from aiogram.types import Message
from user import User
from command_execution import ManualCommandForm
import logging

class AccessMiddleware:
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        role = User.get_user_role(user_id)
        logging.info(f"User ID: {user_id}, Role: {role}") # Log user ID and role

        if not role:
            await event.answer("You are not authorized to use this bot.")
            return

        user = User(user_id, role)

        # Check if the message is a command
        if event.text and event.text.startswith('/'):
            # Check if the user is entering a command manually
            state = data.get('state')
            if state and await state.get_state() == ManualCommandForm.command:
                # Skip permission check for manually entered commands
                logging.info(f"Skipping permission check for manually entered command.")
            else:
                # Perform permission check for other commands
                command = event.text.split()[0]
                logging.info(f"Checking permission for command: {command}")
                if not user.has_permission(command):
                    await event.answer("You don't have permission to use this command.")
                    return

        data['user'] = user
        return await handler(event, data)