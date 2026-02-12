import logging
from core.database import db_manager
from core.config import MAX_HISTORY

logger = logging.getLogger("ContextCache")

async def build_history_string(channel_id: int, bot_id: int) -> str:
    """Builds a formatted history string from the DB for model context."""
    history = await db_manager.get_messages(channel_id, limit=MAX_HISTORY)
    if not history:
        return "No previous conversation found."
    
    lines = []
    for msg in history:
        # Dynamic check: Is this message from the bot (me) or a user?
        # Note: The DB stores IDs as Integers.
        role = "hero 🗿" if msg['author_id'] == bot_id else "User"
        lines.append(f"{role}: {msg['content']}")
    
    return "\n".join(lines)
