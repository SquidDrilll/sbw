# chatbot.py
import os
import sqlite3
import asyncio  # ADD THIS IMPORT
import random
from datetime import datetime, timedelta
from typing import List, Dict
import discord
import groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10000"))
DB_FILE = os.getenv("DB_FILE", "chat_memory.db")

groq_client = groq.Groq(api_key=GROQ_API_KEY)

class MessageStore:
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
                timestamp TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_channel ON messages(channel_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)')
        conn.commit()
        conn.close()
    
    def add(self, channel_id: str, author_id: str, author_name: str, content: str, role: str = "user"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
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
        
        return [{"role": row[2], "content": f"{row[0]}: {row[1]}" if row[2] == "user" else row[1]} 
                for row in reversed(rows)]

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
    
    system_prompt = f"""You are an AI assistant in Discord {channel_type}.
You remember past conversations. Be helpful, natural, and concise.
Use Discord markdown."""

    # Get history
    history = store.get_history(channel_id, limit=30)
    
    # Generate response
    response = await get_ai_response(history, system_prompt)
    
    # Try multiple methods to send
    methods = [
        # Method 1: Direct send
        lambda: message.channel.send(response[:2000]),
        # Method 2: Reply to message
        lambda: message.reply(response[:2000], mention_author=False),
        # Method 3: Reply with delay
        lambda: asyncio.sleep(1) or message.reply(response[:2000], mention_author=False),
    ]
    
    for i, method in enumerate(methods):
        try:
            await asyncio.sleep(random.uniform(0.5, 1.0))  # Random delay
            await method()
            store.add(channel_id, "assistant", "AI", response, "assistant")
            print(f"✅ Sent via method {i+1}")
            return
        except discord.errors.Forbidden:
            print(f"❌ Method {i+1} forbidden, trying next...")
            continue
        except Exception as e:
            print(f"❌ Method {i+1} error: {e}")
            continue
    
    print("❌ All methods failed")
