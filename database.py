import os
import asyncpg
from agno.db.async_postgres import AsyncPostgresDb

POSTGRES_URL = os.getenv("POSTGRES_URL")

# Agno's persistent memory manager for sessions and memories
db = AsyncPostgresDb(
    db_url=POSTGRES_URL,
    session_table="hero_sessions",
    memory_table="hero_memories",
)

class RawMessageStore:
    def __init__(self):
        self.pool = None

    async def init(self):
        # Initialize connection pool for high-performance async operations
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
                CREATE INDEX IF NOT EXISTS idx_chan_date ON messages (channel_id, created_at DESC);
            """)

    async def store(self, msg):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (message_id, channel_id, author_id, author_name, content, created_at)
                VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (message_id) DO NOTHING
            """, msg.id, msg.channel.id, msg.author.id, msg.author.name, msg.content, msg.created_at)

    async def get_history(self, channel_id, limit=50):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT author_name, author_id, content 
                FROM messages WHERE channel_id = $1 
                ORDER BY created_at DESC LIMIT $2
            """, channel_id, limit)
            return [{"role": "user", "content": f"{r[0]}({r[1]}): {r[2]}"} for r in reversed(rows)]

msg_store = RawMessageStore()
