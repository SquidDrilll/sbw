import sqlite3
from datetime import datetime

class MessageStore:
    def __init__(self, db_path="chat_memory.db"):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        # Table stores channel ID, author, content, role, and time
        conn.execute('''CREATE TABLE IF NOT EXISTS messages 
                     (channel_id TEXT, author_name TEXT, content TEXT, role TEXT, timestamp TEXT)''')
        conn.close()

    def add(self, channel_id, author_name, content, role):
        conn = sqlite3.connect(self.db_path)
        # Standardizes role as 'user' or 'assistant' for AI context
        conn.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)',
                     (channel_id, author_name, content, role, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_history(self, channel_id, limit=25):
        conn = sqlite3.connect(self.db_path)
        # Pulls recent messages to give the AI context
        cursor = conn.execute('''SELECT author_name, content, role FROM messages 
                                 WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?''', 
                              (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        # Returns in chronological order so the AI understands the flow
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]
