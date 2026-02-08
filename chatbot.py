# chatbot.py
import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import discord
import groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10000"))  # 10k messages
DB_FILE = os.getenv("DB_FILE", "chat_memory.db")

groq_client = groq.Groq(api_key=GROQ_API_KEY)

class MessageStore:
    """SQLite storage for up to 10k+ messages"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                author_id TEXT,
                author_name TEXT,
                content TEXT,
                role TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel_id)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)
        ''')
        conn.commit()
        conn.close()
    
    def add(self, channel_id: str, author_id: str, author_name: str, content: str, role: str = "user"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Insert new message
        c.execute('''
            INSERT INTO messages (channel_id, author_id, author_name, content, role, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (channel_id, author_id, author_name, content, role, datetime.now().isoformat()))
        
        # Keep only last MAX_HISTORY per channel
        c.execute('''
            DELETE FROM messages WHERE id NOT IN (
                SELECT id FROM messages 
                WHERE channel_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ) AND channel_id = ?
        ''', (channel_id, MAX_HISTORY, channel_id))
        
        conn.commit()
        conn.close()
    
    def get_history(self, channel_id: str, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT author_name, content, role, timestamp 
            FROM messages 
            WHERE channel_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (channel_id, limit))
        
        rows = c.fetchall()
        conn.close()
        
        # Reverse to get chronological order
        return [{"role": row[2], "content": f"{row[0]}: {row[1]}" if row[2] == "user" else row[1]} 
                for row in reversed(rows)]
    
    def search_by_author(self, channel_id: str, author_name: str, hours: int = 24) -> List[Dict]:
        """Search messages by specific author in timeframe"""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT author_name, content, timestamp 
            FROM messages 
            WHERE channel_id = ? AND author_name LIKE ? AND timestamp > ?
            ORDER BY timestamp DESC
        ''', (channel_id, f"%{author_name}%", since))
        
        rows = c.fetchall()
        conn.close()
        return [{"author": row[0], "content": row[1], "time": row[2]} for row in rows]
    
    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*), COUNT(DISTINCT channel_id) FROM messages')
        total, channels = c.fetchone()
        conn.close()
        return {"total_messages": total, "channels": channels}

store = MessageStore(DB_FILE)

async def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
    formatted = [{"role": "system", "content": system_prompt}]
    formatted.extend(messages)
    
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=formatted,
            max_tokens=4096,
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error: {str(e)}"

async def handle_chat(message, content: str):
    channel_id = str(message.channel.id)
    author_id = str(message.author.id)
    author_name = str(message.author.name)
    
    # Store incoming message
    store.add(channel_id, author_id, author_name, content, "user")
    
    # Determine context
    if isinstance(message.channel, discord.DMChannel):
        channel_type = "DM"
    elif isinstance(message.channel, discord.GroupChannel):
        channel_type = "Group DM"
    else:
        channel_type = "Server"
    
    # Smart system prompt
    system_prompt = f"""You are {message.channel.me.name if hasattr(message.channel, 'me') else 'AI Assistant'}, chatting in Discord {channel_type}.
You remember past conversations. Be helpful, natural, and concise.
Use Discord markdown. Reference previous messages when relevant."""

    # Get history
    history = store.get_history(channel_id, limit=30)
    
    # Generate response
    response = await get_ai_response(history, system_prompt)
    
    # Try to send with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Split long messages
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
                    await asyncio.sleep(0.5)
            else:
                await message.channel.send(response)
            
            # Store AI response
            store.add(channel_id, "assistant", "AI", response, "assistant")
            break
            
        except discord.errors.Forbidden as e:
            print(f"❌ Forbidden (attempt {attempt+1}): {e}")
            if attempt == max_retries - 1:
                # Last resort: try to reply instead of send
                try:
                    await message.reply(response[:2000], mention_author=False)
                    store.add(channel_id, "assistant", "AI", response, "assistant")
                except Exception as e2:
                    print(f"❌ Reply also failed: {e2}")
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Error sending (attempt {attempt+1}): {e}")
            await asyncio.sleep(1)
