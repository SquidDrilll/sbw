# chatbot.py
import os
import sqlite3
import asyncio
import random
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import discord
import aiohttp

# Try to import various AI providers
try:
    import groq
    GROQ_AVAILABLE = True
except:
    GROQ_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

# Configuration
DB_FILE = os.getenv("DB_FILE", "chat_memory.db")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "10000"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000"))

# Provider configs with fallback priority
PROVIDERS = []

# Groq setup
GROQ_KEY = os.getenv("GROQ_API_KEY")
if GROQ_KEY and GROQ_AVAILABLE:
    PROVIDERS.append({
        "name": "groq",
        "client": groq.Groq(api_key=GROQ_KEY),
        "models": ["llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"],
        "current_model_idx": 0
    })

# OpenRouter (free tier) setup
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if OPENROUTER_KEY:
    PROVIDERS.append({
        "name": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_KEY,
        "models": ["meta-llama/llama-3.1-8b-instruct:free", "google/gemma-2-9b-it:free"],
        "current_model_idx": 0
    })

# Local/Ollama fallback
OLLAMA_URL = os.getenv("OLLAMA_URL")  # e.g., http://localhost:11434
if OLLAMA_URL:
    PROVIDERS.append({
        "name": "ollama",
        "url": OLLAMA_URL,
        "models": ["llama3.1", "phi3", "mistral"],
        "current_model_idx": 0
    })

if not PROVIDERS:
    raise ValueError("No AI providers configured! Set GROQ_API_KEY, OPENROUTER_API_KEY, or OLLAMA_URL")

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
    
    def get_history(self, channel_id: str, limit: int = 20) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT author_name, content, role 
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

def estimate_tokens(text: str) -> int:
    """Rough token estimation"""
    return len(text) // 4

async def try_groq(provider: Dict, messages: List[Dict], system_prompt: str) -> Optional[str]:
    """Try Groq API"""
    try:
        model = provider["models"][provider["current_model_idx"]]
        response = provider["client"].chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt}] + messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str or "429" in error_str:
            # Try next model
            provider["current_model_idx"] = (provider["current_model_idx"] + 1) % len(provider["models"])
            print(f"⚠️ Groq rate limit, trying model: {provider['models'][provider['current_model_idx']]}")
            return None
        raise e

async def try_openrouter(provider: Dict, messages: List[Dict], system_prompt: str) -> Optional[str]:
    """Try OpenRouter API"""
    try:
        model = provider["models"][provider["current_model_idx"]]
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "max_tokens": MAX_TOKENS
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{provider['base_url']}/chat/completions",
                headers=headers,
                json=payload
            ) as resp:
                if resp.status == 429:
                    provider["current_model_idx"] = (provider["current_model_idx"] + 1) % len(provider["models"])
                    return None
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️ OpenRouter error: {e}")
        return None

async def try_ollama(provider: Dict, messages: List[Dict], system_prompt: str) -> Optional[str]:
    """Try local Ollama"""
    try:
        model = provider["models"][provider["current_model_idx"]]
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{provider['url']}/api/chat",
                json=payload
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data["message"]["content"]
    except Exception as e:
        print(f"⚠️ Ollama error: {e}")
        return None

async def get_ai_response(messages: List[Dict], system_prompt: str) -> str:
    """Try all providers until one works"""
    
    # Limit message history to save tokens
    total_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    while total_tokens > 6000 and len(messages) > 5:
        messages = messages[1:]  # Remove oldest
        total_tokens = sum(estimate_tokens(m["content"]) for m in messages)
    
    last_error = None
    
    for attempt in range(3):  # 3 attempts total
        for provider in PROVIDERS:
            try:
                print(f"🔄 Trying {provider['name']}...")
                
                if provider["name"] == "groq":
                    result = await try_groq(provider, messages, system_prompt)
                elif provider["name"] == "openrouter":
                    result = await try_openrouter(provider, messages, system_prompt)
                elif provider["name"] == "ollama":
                    result = await try_ollama(provider, messages, system_prompt)
                else:
                    continue
                
                if result:
                    print(f"✅ Success with {provider['name']}")
                    return result
                
                await asyncio.sleep(1)
                
            except Exception as e:
                last_error = e
                print(f"❌ {provider['name']} failed: {e}")
                continue
        
        print(f"⏳ Attempt {attempt + 1} failed, waiting...")
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return f"❌ All AI providers failed. Last error: {last_error}"

async def send_message_safe(message, content: str):
    """Try multiple ways to send a message"""
    methods = [
        lambda: message.channel.send(content[:2000]),
        lambda: message.reply(content[:2000], mention_author=False),
    ]
    
    for method in methods:
        try:
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return await method()
        except discord.errors.Forbidden:
            continue
        except Exception as e:
            print(f"Send error: {e}")
            continue
    
    # Final fallback: DM
    try:
        await message.author.send(f"Response:\n{content[:1900]}")
    except:
        pass

async def handle_chat(message, content: str):
    channel_id = str(message.channel.id)
    author_id = str(message.author.id)
    author_name = str(message.author.name)
    
    # Store message
    store.add(channel_id, author_id, author_name, content, "user")
    
    # Build system prompt
    if isinstance(message.channel, discord.DMChannel):
        channel_type = "DM"
    elif isinstance(message.channel, discord.GroupChannel):
        channel_type = "Group DM"
    else:
        channel_type = "Server"
    
    system_prompt = f"""You are a helpful AI assistant in Discord {channel_type}.
You remember conversations. Be natural, concise, use Discord markdown."""
    
    # Get history (limited to save tokens)
    history = store.get_history(channel_id, limit=15)
    
    # Get AI response
    response = await get_ai_response(history, system_prompt)
    
    # Store and send
    if not response.startswith("❌"):
        store.add(channel_id, "assistant", "AI", response, "assistant")
    
    await send_message_safe(message, response)
