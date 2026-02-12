import asyncpg, logging
from typing import List, Dict, Optional
from core.config import POSTGRES_URL

logger = logging.getLogger("Database")

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self):
        if not POSTGRES_URL:
            logger.error("POSTGRES_URL is missing!")
            return
        
        try:
            url = POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
            self.pool = await asyncpg.create_pool(url)
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        message_id BIGINT PRIMARY KEY,
                        channel_id BIGINT NOT NULL,
                        author_id BIGINT NOT NULL,
                        author_name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_msgs_chan ON messages (channel_id, created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_msgs_auth_name ON messages (author_name);
                """)
            logger.info("Database initialized.")
        except Exception as e:
            logger.error(f"DB Init Error: {e}")

    async def store_message(self, msg_id, channel_id, author_id, author_name, content, created_at):
        if not self.pool or not content: return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO messages (message_id, channel_id, author_id, author_name, content, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (message_id) DO NOTHING
                """, msg_id, channel_id, author_id, author_name, content, created_at)
        except Exception as e:
            pass # Silent fail to prevent log spam during massive indexing

    async def get_messages(self, channel_id: int, limit: int = 50) -> List[Dict]:
        if not self.pool: return []
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT author_name, author_id, content 
                    FROM messages 
                    WHERE channel_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, channel_id, limit)
                return [dict(r) for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Fetch Error: {e}")
            return []

    async def search_global_messages_by_name(self, author_name: str, limit: int = 100) -> List[Dict]:
        """
        Deeper search for global recall. 
        Returns more messages (100) for better personality analysis.
        """
        if not self.pool: return []
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT content, author_name, created_at 
                    FROM messages 
                    WHERE author_name ILIKE $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, f"%{author_name}%", limit)
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Global Search Error: {e}")
            return []

db_manager = Database()
