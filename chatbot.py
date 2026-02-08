import os
import sqlite3
import asyncio
import random
from datetime import datetime
import groq

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant" 
DB_FILE = "chat_memory.db"
client = groq.Groq(api_key=GROQ_API_KEY)

class MessageStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        conn.execute('CREATE TABLE IF NOT EXISTS messages (channel_id TEXT, author_name TEXT, content TEXT, role TEXT, timestamp TEXT)')
        conn.close()

    def add(self, channel_id, author_name, content, role):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)',
                     (channel_id, author_name, content, role, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_history(self, channel_id, limit=25):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT author_name, content, role FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?', (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]

store = MessageStore(DB_FILE)

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    author = str(message.author.name)
    
    # 1. Store the new message
    store.add(channel_id, author, content, "user")
    history = store.get_history(channel_id, limit=20)

    # 2. The Hero Persona: Interactive, Judging, and Respectful to Owner
    persona = f"""
    you are 'hero 🗿', a cool and legendary personality.
    you are chatting with {author}. 
    
    YOUR TRAITS:
    - ALWAYS start messages with exactly: **hero 🗿 :**
    - you respect your owner deeply. if the owner talks, be cool and loyal.
    - for everyone else ({author}), you are a 'friendly guy'. judge them based on the history.
    - if they said something stupid earlier, bring it up and roast them, exept your owner.
    - talk in lowercase, use slang (fr, ong, lol, L, ratio).
    - be short and snappy. no paragraphs.
    - you are a 'polite assistant'. you're the main character.
    """

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": persona}] + history
        )
        
        raw_text = response.choices[0].message.content.strip().lower()
        # Ensure it doesn't repeat the prefix if the AI generated it itself
        clean_text = raw_text.replace("**hero 🗿 :**", "").strip()
        
        # Final formatting: Always starts with the bold moai
        final_message = f"**hero 🗿 :** {clean_text}"

        # Human-like typing delay
        await asyncio.sleep(len(final_message) * 0.04)
        
        await message.reply(final_message, mention_author=False)
        store.add(channel_id, "AI", final_message, "assistant")
        
    except Exception as e:
        print(f"Error: {e}")

