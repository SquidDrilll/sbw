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
    # Reverse history to show oldest first (standard chat flow)
    for msg in reversed(history):
        # Dynamic Identity: Use the actual Display Name from the DB
        role = "hero 🗿" if msg['author_id'] == bot_id else msg['author_name']
        
        # Format: "Squiddrill: Hello" instead of "User: Hello"
        lines.append(f"{role}: {msg['content']}")
    
    return "\n".join(lines)
