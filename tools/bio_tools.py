from agno.tools import Toolkit
from agno.tools.function import ToolResult
from agno.media import Image
# Import from the core folder we just created
from core.execution_context import get_current_channel
import logging
import discord
from typing import Optional, Union

logger = logging.getLogger(__name__)

class BioTools(Toolkit):
    def __init__(self):
        super().__init__(name="bio_tools")
        self.register(self.get_user_details)
        self.register(self.get_user_avatar)

    def _get_discord_client(self, channel=None) -> Optional[discord.Client]:
        """Helper to get the Discord client from the current channel context."""
        if channel:
            # 1. Try getting from guild (Public API approach, safer)
            if hasattr(channel, 'guild') and channel.guild:
                 # In some versions of discord.py, guild.me.client might work, 
                 # but sticking to the _state method as fallback is reliable for self-bots.
                 pass

            # 2. Try to get client from channel state (Private API, works for DMs and Guilds)
            if hasattr(channel, '_state') and hasattr(channel._state, '_get_client'):
                return channel._state._get_client()
                
            # 3. Fallback: Try getting from guild state
            guild = getattr(channel, 'guild', None)
            if guild and hasattr(guild, '_state') and hasattr(guild._state, '_get_client'):
                return guild._state._get_client()
        return None

    async def get_user_details(self, user_id: int) -> str:
        """
        Fetches details for a Discord user by their ID (username, roles, join date, etc.).
        Use this when you need to know more about the person you are talking to.
        
        Args:
            user_id (int): The Discord user ID.
            
        Returns:
            str: Formatted user details.
        """
        channel = get_current_channel()
        if not channel:
            return "Error: No execution context found."
        
        try:
            client = self._get_discord_client(channel)
            if not client:
                return "Error: Cannot access Discord client."
            
            # Fetch user
            try:
                user = await client.fetch_user(user_id)
            except discord.NotFound:
                return f"User {user_id} not found."

            # Build details
            details = [
                f"User: {user.name} (ID: {user.id})",
                f"Display Name: {user.display_name}",
                f"Created Account: {user.created_at.strftime('%Y-%m-%d')}",
                f"Bot: {user.bot}",
            ]
            
            # If in a guild, try to get member details (roles, join date)
            if getattr(channel, 'guild', None):
                try:
                    member = await channel.guild.fetch_member(user_id)
                    details.append(f"Joined Server: {member.joined_at.strftime('%Y-%m-%d')}")
                    roles = [r.name for r in member.roles if r.name != "@everyone"]
                    if roles:
                        details.append(f"Roles: {', '.join(roles)}")
                    if member.nick:
                        details.append(f"Server Nickname: {member.nick}")
                except:
                    pass # User might not be in this guild, just return basic info

            return "\n".join(details)
        
        except Exception as e:
            return f"Error fetching user details: {e}"

    async def get_user_avatar(self, user_id: int) -> ToolResult:
        """
        Fetches the avatar of a Discord user to see what they look like.
        
        Args:
            user_id (int): The Discord user ID.
        """
        channel = get_current_channel()
        if not channel:
            return ToolResult(content="Error: No context.")
        
        try:
            client = self._get_discord_client(channel)
            user = await client.fetch_user(user_id)
            avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
            
            return ToolResult(
                content=f"Avatar for {user.name}",
                images=[Image(url=avatar_url)]
            )
        except Exception as e:
            return ToolResult(content=f"Error getting avatar: {e}")
