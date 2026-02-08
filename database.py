import os
import asyncpg
from agno.db.async_postgres import AsyncPostgresDb

POSTGRES_URL = os.getenv("POSTGRES_URL")

def get_async_url(url):
    """Ensures the URL uses the asyncpg driver for SQLAlchemy/Agno."""
    if not url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

# Use the modified URL for Agno's memory management
async_db_url = get_async_url(POSTGRES_URL)

db = AsyncPostgresDb(
    db_url=async_db_url,
    session_table="hero_sessions",
    memory_table="hero_memories",
)

class RawMessageStore:
    def __init__(self):
        self.pool = None

    async def init(self):
        # Initialize the connection pool for raw logs
        # Note: asyncpg.create_pool uses the standard postgresql:// format
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

    async def get_history(self, channel_id, limit=30):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT author_name, author_id, content 
                FROM messages WHERE channel_id = $1 
                ORDER BY created_at DESC LIMIT $2
            """, channel_id, limit)
            return [{"role": "user", "content": f"{r[0]}({r[1]}): {r[2]}"} for r in reversed(rows)]

msg_store = RawMessageStore()
