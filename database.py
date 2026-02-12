import os
import asyncpg
from agno.db.async_postgres import AsyncPostgresDb

POSTGRES_URL = os.getenv("POSTGRES_URL")

def get_async_url(url):
    """
    Converts a standard Postgres URL to an asyncpg-compatible URL.
    Handles 'postgres://' and 'postgresql://' prefixes.
    """
    if not url:
        return ""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

# Initialize Agno DB (for MemoryManager)
db = AsyncPostgresDb(
    db_url=get_async_url(POSTGRES_URL),
    session_table="hero_sessions",
    memory_table="hero_memories",
)

class RawMessageStore:
    def __init__(self):
        self.pool = None

    async def init(self):
        if not POSTGRES_URL:
            print("❌ Error: POSTGRES_URL is missing.")
            return

        try:
            # We use the raw URL for asyncpg.create_pool, NOT the sqlalchemy/asyncpg format
            raw_url = POSTGRES_URL.replace("postgresql+asyncpg://", "postgresql://")
            self.pool = await asyncpg.create_pool(raw_url)
            
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
                    CREATE TABLE IF NOT EXISTS channel_status (
                        channel_id BIGINT PRIMARY KEY,
                        is_fully_backfilled BOOLEAN DEFAULT FALSE
                    );
                    CREATE INDEX IF NOT EXISTS idx_chan_date ON messages (channel_id, created_at DESC);
                """)
        except Exception as e:
            print(f"❌ Database Init Failed: {e}")

    async def store(self, msg):
        if not self.pool: return
        try:
            async with self.pool.acquire() as conn:
                # Use msg.created_at if available, otherwise default will handle it (but better to be explicit)
                created_at = msg.created_at if hasattr(msg, 'created_at') else datetime.now(pytz.utc)
                
                await conn.execute("""
                    INSERT INTO messages (message_id, channel_id, author_id, author_name, content, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (message_id) DO NOTHING
                """, msg.id, msg.channel.id, msg.author.id, msg.author.name, msg.content, created_at)
        except Exception as e:
            print(f"⚠️ Store Error: {e}")

    async def get_history(self, channel_id, limit=50):
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
                # Return in chronological order (oldest -> newest) for the LLM
                return [{"role": "user", "content": f"{r[0]}({r[1]}): {r[2]}"} for r in reversed(rows)]
        except Exception as e:
            print(f"⚠️ History Fetch Error: {e}")
            return []

msg_store = RawMessageStore()
