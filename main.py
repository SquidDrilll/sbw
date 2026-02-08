# chatbot.py
import os
import sqlite3
import asyncio
import groq
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY)

class MessageStore:
    def __init__(self, db_path="chat_memory.db"):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        # We added author_name to make searching easier
        conn.execute('CREATE TABLE IF NOT EXISTS messages (channel_id TEXT, author_name TEXT, content TEXT, role TEXT, timestamp TEXT)')
        conn.close()

    def add(self, channel_id, author_name, content, role):
        conn = sqlite3.connect(self.db_path)
        # Use 'INSERT OR IGNORE' logic or just check if it exists to avoid duplicates
        conn.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)', 
                     (channel_id, author_name, content, role, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def search_history(self, channel_id, query_name):
        conn = sqlite3.connect(self.db_path)
        # Search specifically for what a certain person said
        cursor = conn.execute('SELECT author_name, content FROM messages WHERE channel_id = ? AND author_name LIKE ? LIMIT 10', 
                             (channel_id, f"%{query_name}%"))
        rows = cursor.fetchall()
        conn.close()
        return "\n".join([f"{r[0]}: {r[1]}" for r in rows])

    def get_recent(self, channel_id, limit=20):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT author_name, content, role FROM messages WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?', (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]

store = MessageStore()

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    
    # 1. Check if the user is asking about a specific person
    relevant_past = ""
    if "say" in content.lower() or "tell" in content.lower():
        # Try to guess who they are asking about (simple version)
        words = content.split()
        potential_name = words[-1] # Usually the last word in "What did Alex say"
        relevant_past = store.search_history(channel_id, potential_name)

    # 2. Get the standard recent context
    history = store.get_recent(channel_id)
    
    # 3. Build the prompt
    system_msg = f"You are a helpful assistant. Past info found: {relevant_past}"
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}] + history
        )
        ai_text = response.choices[0].message.content.lstrip("!")
        await message.reply(ai_text, mention_author=False)
        store.add(channel_id, "AI", ai_text, "assistant")
    except Exception as e:
        print(f"Error: {e}")
