from agno.tools import Toolkit
from agno.tools.function import ToolResult
from agno.media import Image
from core.execution_context import get_current_channel
import logging
import discord
from typing import Optional, Union

logger = logging.getLogger(__name__)

class BioTools(Toolkit):
    def __init__(self, bot: discord.Client):
        super().__init__(name="bio_tools")
        self.bot = bot  # Dependency Injection: Stable access to the bot
        self.register(self.get_user_details)
        self.register(self.get_user_avatar)

    async def get_user_details(self, user_id: Union[int, str]) -> str:
        """
        Fetches details for a Discord user (username, roles, join date, etc.).
        
        Args:
            user_id (Union[int, str]): The Discord user ID.
        """
        channel = get_current_channel()
        
        try:
            # Fix: Ensure user_id is an integer for discord.py
            u_id = int(user_id)
            
            try:
                user = await self.bot.fetch_user(u_id)
            except discord.NotFound:
                return f"Error: User {user_id} not found."
            except discord.HTTPException as e:
                return f"Error: Discord API failure: {e}"

            details = [
                f"User: {user.name} (ID: {user.id})",
                f"Display Name: {user.display_name}",
                f"Created Account: {user.created_at.strftime('%Y-%m-%d')}",
                f"Bot: {user.bot}",
            ]
            
            # Context-aware guild details
            if channel and hasattr(channel, 'guild') and channel.guild:
                try:
                    member = await channel.guild.fetch_member(u_id)
                    details.append(f"Joined Server: {member.joined_at.strftime('%Y-%m-%d')}")
                    roles = [r.name for r in member.roles if r.name != "@everyone"]
                    if roles:
                        details.append(f"Roles: {', '.join(roles)}")
                    if member.nick:
                        details.append(f"Server Nickname: {member.nick}")
                except (discord.NotFound, discord.Forbidden):
                    pass 

            return "\n".join(details)
        
        except ValueError:
            return f"Error: '{user_id}' is not a valid numerical ID."
        except Exception as e:
            logger.error(f"Critical error in get_user_details: {e}", exc_info=True)
            return "Error: Internal lookup failure."

    async def get_user_avatar(self, user_id: Union[int, str]) -> ToolResult:
        """
        Fetches the avatar of a Discord user.
        """
        try:
            u_id = int(user_id)
            user = await self.bot.fetch_user(u_id)
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            
            return ToolResult(
                content=f"Avatar for {user.name}",
                images=[Image(url=avatar_url)]
            )
        except Exception as e:
            logger.error(f"Error getting avatar: {e}")
            return ToolResult(content=f"Error: {e}")
