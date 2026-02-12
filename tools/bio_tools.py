from agno.tools import Toolkit
from agno.tools.function import ToolResult
from agno.media import Image
from core.execution_context import get_current_channel
# Import the DB manager to access global history
from core.database import db_manager
import logging
import discord
from typing import Optional, Union

logger = logging.getLogger(__name__)

class BioTools(Toolkit):
    def __init__(self, bot: discord.Client):
        super().__init__(name="bio_tools")
        self.bot = bot
        self.register(self.get_user_details)
        self.register(self.get_user_avatar)
        self.register(self.read_user_logs) # New Tool

    async def read_user_logs(self, name: str) -> str:
        """
        Searches the bot's entire memory (across all servers) for messages sent by a specific person.
        Use this to judge someone, analyze their personality, or remember what they said,
        even if they are not in the current server.

        Args:
            name (str): The display name or username to search for (e.g., "Forbit").
        """
        try:
            messages = await db_manager.search_global_messages_by_name(name, limit=50)
            if not messages:
                return f"No records found for anyone named '{name}' in my memory."
            
            # Format the logs for the AI
            log_text = [f"--- Chat Logs for {name} ---"]
            for msg in messages:
                # Minimal format: Content [Time]
                timestamp = msg['created_at'].strftime('%Y-%m-%d')
                log_text.append(f"[{timestamp}] {msg['content']}")
            
            return "\n".join(log_text)
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return "Error: Could not access memory archives."

    async def get_user_details(self, user_id: Union[int, str]) -> str:
        """Fetches Discord profile details (roles, join date) by ID."""
        channel = get_current_channel()
        try:
            try:
                u_id = int(user_id)
            except ValueError:
                return f"Error: '{user_id}' is not a valid ID."
            
            try:
                user = await self.bot.fetch_user(u_id)
            except discord.NotFound:
                return f"User {user_id} not found."

            details = [
                f"User: {user.name} (ID: {user.id})",
                f"Display Name: {user.display_name}",
                f"Bot: {user.bot}",
            ]
            
            if channel and hasattr(channel, 'guild') and channel.guild:
                try:
                    member = await channel.guild.fetch_member(u_id)
                    details.append(f"Joined: {member.joined_at.strftime('%Y-%m-%d')}")
                    roles = [r.name for r in member.roles if r.name != "@everyone"]
                    if roles: details.append(f"Roles: {', '.join(roles)}")
                except: pass 

            return "\n".join(details)
        except Exception as e:
            return f"Error: {e}"

    async def get_user_avatar(self, user_id: Union[int, str]) -> ToolResult:
        """Fetches the avatar of a Discord user."""
        try:
            u_id = int(user_id)
            user = await self.bot.fetch_user(u_id)
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            return ToolResult(content=f"Avatar for {user.name}", images=[Image(url=avatar_url)])
        except Exception as e:
            return ToolResult(content=f"Error: {e}")ssssssssss
