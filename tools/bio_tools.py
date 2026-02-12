from agno.tools import Toolkit
from agno.tools.function import ToolResult
from agno.media import Image
# Import from the core folder for channel context (guild check)
from core.execution_context import get_current_channel
import logging
import discord
from typing import Optional, Union

logger = logging.getLogger(__name__)

class BioTools(Toolkit):
    def __init__(self, bot: discord.Client):
        super().__init__(name="bio_tools")
        self.bot = bot # Dependency Injection: Store the bot instance
        self.register(self.get_user_details)
        self.register(self.get_user_avatar)

    async def get_user_details(self, user_id: int) -> str:
        """
        Fetches details for a Discord user by their ID (username, roles, join date, etc.).
        Use this when you need to know more about the person you are talking to.
        
        Args:
            user_id (int): The Discord user ID.
            
        Returns:
            str: Formatted user details or error message.
        """
        # We still need context to know if we are in a guild for role checks
        channel = get_current_channel()
        
        try:
            # Safe access using the injected bot instance
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                return f"Error: User with ID {user_id} not found."
            except discord.HTTPException as e:
                return f"Error: Discord API failure: {str(e)}"

            # Build details
            details = [
                f"User: {user.name} (ID: {user.id})",
                f"Display Name: {user.display_name}",
                f"Created Account: {user.created_at.strftime('%Y-%m-%d')}",
                f"Bot: {user.bot}",
            ]
            
            # If in a guild, try to get member details (roles, join date)
            if channel and getattr(channel, 'guild', None):
                try:
                    member = await channel.guild.fetch_member(user_id)
                    details.append(f"Joined Server: {member.joined_at.strftime('%Y-%m-%d')}")
                    roles = [r.name for r in member.roles if r.name != "@everyone"]
                    if roles:
                        details.append(f"Roles: {', '.join(roles)}")
                    if member.nick:
                        details.append(f"Server Nickname: {member.nick}")
                except discord.NotFound:
                    # User isn't in this specific guild, which is fine
                    pass 
                except Exception as e:
                    logger.warning(f"Failed to fetch member details: {e}")

            return "\n".join(details)
        
        except Exception as e:
            logger.error(f"Critical error in get_user_details: {e}", exc_info=True)
            return "Error: An unexpected internal error occurred while fetching user details."

    async def get_user_avatar(self, user_id: int) -> ToolResult:
        """
        Fetches the avatar of a Discord user to see what they look like.
        
        Args:
            user_id (int): The Discord user ID.
        """
        try:
            user = await self.bot.fetch_user(user_id)
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            
            return ToolResult(
                content=f"Avatar for {user.name}",
                images=[Image(url=avatar_url)]
            )
        except discord.NotFound:
            return ToolResult(content=f"Error: User {user_id} not found.")
        except Exception as e:
            logger.error(f"Error getting avatar: {e}", exc_info=True)
            return ToolResult(content="Error: Could not retrieve avatar.")
