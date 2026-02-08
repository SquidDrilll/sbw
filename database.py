import sqlite3
from datetime import datetime

class MessageStore:
    def __init__(self, db_path="chat_memory.db"):
        self.db_path = db_path
        conn = sqlite3.connect(self.db_path)
        # Table stores metadata to differentiate users and judge their 'lore'
        conn.execute('''CREATE TABLE IF NOT EXISTS messages 
                     (channel_id TEXT, author_name TEXT, content TEXT, role TEXT, timestamp TEXT)''')
        conn.close()

    def add(self, channel_id, author_name, content, role):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)',
                     (channel_id, author_name, content, role, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_history(self, channel_id, limit=30):
        conn = sqlite3.connect(self.db_path)
        # Fetch lore to verify identities and provide context
        cursor = conn.execute('''SELECT author_name, content, role FROM messages 
                                 WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?''', 
                              (channel_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r[2], "content": f"{r[0]}: {r[1]}" if r[2] == "user" else r[1]} for r in reversed(rows)]
