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
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant" 
DB_FILE = "chat_memory.db"

groq_client = groq.Groq(api_key=GROQ_API_KEY)

# --- HUMAN PERSONA CONFIG ---
# Replace [Your Name] with your actual name or nickname
MY_PERSONA = """
You are a real person named [Your Name] chatting in a Discord Group DM. 
Follow these 'Human Rules' strictly:
1. TALK IN LOWERCASE. it looks more natural.
2. BE CONCISE. real people don't write paragraphs. use less words , around 30 ( or more if asked or feels neccesary).
3. USE SLANG. use words like 'fr', 'ong', 'lol', 'idk', 'rn', and 'nah' naturally.
4. DON'T BE A TEACHER. if someone asks a question, give a short, snappy answer.
5. MATCH THE VIBE. if everyone is joking, join in. don't be a robot.
6. NO ROBOT TALK. never say 'as an ai' or 'i'm here to help'. 
"""

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

    def get_history(self, channel_id, limit=15): # Reduced limit for better vibe matching
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT author_name, content, role FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?', (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]

store = MessageStore(DB_FILE)

async def get_ai_response(history):
    # FIXED: Now uses the MY_PERSONA prompt
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": MY_PERSONA}] + history,
            max_tokens=500, # Lower tokens = faster response
            temperature=0.8 # Higher temperature = more "creative/human"
        )
        return response.choices[0].message.content
    except Exception as e:
        if OPENROUTER_KEY:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "system", "content": MY_PERSONA}] + history
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        return "idk man my brain is fried rn"

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    store.add(channel_id, message.author.name, content, "user")
    
    history = store.get_history(channel_id)
    response = await get_ai_response(history)
    
    # --- HUMAN BEHAVIOR: DYNAMIC DELAY ---
    # Calculates a "typing speed" so it feels real
    typing_speed = (len(response) * 0.06) + random.uniform(0.5, 1.5)
    await asyncio.sleep(min(typing_speed, 4)) # Don't wait longer than 4s
    
    clean_response = response.strip().lower().lstrip("!?. ")
    
    try:
        await message.reply(clean_response, mention_author=False)
        store.add(channel_id, "AI", clean_response, "assistant")
    except Exception as e:
        print(f"❌ Error: {e}")
