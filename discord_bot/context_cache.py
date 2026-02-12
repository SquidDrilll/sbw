import logging
from core.database import db_manager
from core.config import MAX_HISTORY

logger = logging.getLogger("ContextCache")

async def build_history_string(channel_id: int, bot_id: int) -> str:
    """Builds a formatted history string from the DB using Real Names."""
    history = await db_manager.get_messages(channel_id, limit=MAX_HISTORY)
    if not history:
        return "No previous conversation found."
    
    lines = []
    for msg in reversed(history):
        # If it's the bot, call it "Hero". If it's the user, use their real name (e.g. Forbit)
        role = "Hero" if msg['author_id'] == bot_id else msg['author_name']
        lines.append(f"{role}: {msg['content']}")
    
    return "\n".join(lines)
