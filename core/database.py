import os, asyncpg, asyncio, logging
from datetime import datetime
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
            self.pool = await asyncpg.create_pool(POSTGRES_URL)
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
                    CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages (channel_id, created_at DESC);
                """)
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def store_message(self, msg_id, channel_id, author_id, author_name, content, created_at):
        if not self.pool: return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO messages (message_id, channel_id, author_id, author_name, content, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (message_id) DO NOTHING
                """, msg_id, channel_id, author_id, author_name, content, created_at)
        except Exception as e:
            logger.warning(f"Failed to store message: {e}")

    async def get_messages(self, channel_id: int, limit: int = 50) -> List[Dict]:
        if not self.pool: return []
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT author_name, author_id, content, created_at 
                    FROM messages 
                    WHERE channel_id = $1 
                    ORDER BY created_at DESC 
                    LIMIT $2
                """, channel_id, limit)
                return [dict(r) for r in reversed(rows)]
        except Exception as e:
            logger.error(f"Failed to fetch history: {e}")
            return []

db_manager = Database()
