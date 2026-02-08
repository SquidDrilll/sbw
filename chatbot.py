import os
import sqlite3
import asyncio
import random
from datetime import datetime
from typing import List, Dict
import discord
import groq
import aiohttp

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") # Get a free one at openrouter.ai
GROQ_MODEL = "llama-3.1-8b-instant" # Using 8B to save tokens
MAX_HISTORY = 10000 
DB_FILE = "chat_memory.db"

groq_client = groq.Groq(api_key=GROQ_API_KEY)

class MessageStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, channel_id TEXT, author_name TEXT, content TEXT, role TEXT, timestamp TEXT)')
        conn.close()

    def add(self, channel_id, author_name, content, role):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO messages (channel_id, author_name, content, role, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (channel_id, author_name, content, role, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_history(self, channel_id, limit=20):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT author_name, content, role FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?', (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]

store = MessageStore(DB_FILE)

async def get_ai_response(history):
    system_prompt = "You are a helpful assistant. IMPORTANT: Never start your message with '!' or any command prefix."
    
    # Try Groq First
    try:
        print("🔄 Trying Groq...")
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system_prompt}] + history,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq Failed/Limited: {e}")
        
        # Fallback to OpenRouter (Free)
        if OPENROUTER_KEY:
            print("🔄 Swapping to OpenRouter Fallback...")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "system", "content": system_prompt}] + history
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        return "❌ I'm currently exhausted. Please try again in a minute!"

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    store.add(channel_id, message.author.name, content, "user")
    
    history = store.get_history(channel_id)
    response = await get_ai_response(history)
    
    # Double-check we aren't sending a prefix to avoid loops
    clean_response = response.lstrip("!?. ") 
    
    try:
        # Reply mode is safer for self-bots to avoid being flagged as spam
        await message.reply(clean_response, mention_author=False)
        store.add(channel_id, "AI", clean_response, "assistant")
    except discord.errors.Forbidden:
        print("❌ Permission Error: Discord blocked the send.")
