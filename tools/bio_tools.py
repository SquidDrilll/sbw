from agno.tools import Toolkit
from agno.tools.function import ToolResult
from agno.media import Image
from core.execution_context import get_current_channel
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
        self.register(self.recall_personality_profile)

    async def recall_personality_profile(self, name: str) -> str:
        """
        Recalls everything I know about a person from my long-term global memory.
        Use this when someone asks me to 'Judge', 'Roast', or 'Describe' a user.
        This searches across all channels I have ever seen.

        Args:
            name (str): The name of the person to recall memories of.
        """
        try:
            # Increased limit to 100 for a "real" deep dive
            messages = await db_manager.search_global_messages_by_name(name, limit=100)
            if not messages:
                return f"I actually don't have any memories of someone named '{name}' yet."
            
            log_text = [f"--- Memories of {name} (Extracted from Global Index) ---"]
            for msg in reversed(messages): # chronological order is better for 'thinking'
                timestamp = msg['created_at'].strftime('%Y-%m-%d %H:%M')
                log_text.append(f"[{timestamp}] {msg['content']}")
            
            return "\n".join(log_text)
        except Exception as e:
            logger.error(f"Recall failed: {e}")
            return "My memory is a bit fuzzy on that person right now."

    async def get_user_details(self, user_id: Union[int, str]) -> str:
        """Fetches technical Discord profile details."""
        channel = get_current_channel()
        try:
            u_id = int(user_id)
            user = await self.bot.fetch_user(u_id)
            details = [f"Name: {user.name}", f"ID: {user.id}", f"Display: {user.display_name}"]
            
            if channel and hasattr(channel, 'guild') and channel.guild:
                try:
                    member = await channel.guild.fetch_member(u_id)
                    details.append(f"Joined Server: {member.joined_at.strftime('%Y-%m-%d')}")
                except: pass 
            return "\n".join(details)
        except Exception as e:
            return f"Error: {e}"

    async def get_user_avatar(self, user_id: Union[int, str]) -> ToolResult:
        """Fetches a user's avatar."""
        try:
            u_id = int(user_id)
            user = await self.bot.fetch_user(u_id)
            url = user.avatar.url if user.avatar else user.default_avatar.url
            return ToolResult(content=f"Here is {user.name}'s face.", images=[Image(url=url)])
        except Exception as e:
            return ToolResult(content=f"Couldn't find an avatar: {e}")
