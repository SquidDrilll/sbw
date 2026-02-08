# chatbot.py
import discord 
import os
import json
from datetime import datetime
from typing import List, Dict
import groq

# Load config from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "100"))
MEMORY_FILE = os.getenv("MEMORY_FILE", "chat_memory.json")

# Initialize Groq client
groq_client = groq.Groq(api_key=GROQ_API_KEY)

class SimpleMemory:
    """Simple JSON-based memory storage"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.conversations: Dict[str, List[Dict]] = {}  # channel_id -> messages
        self.load()
    
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load memory: {e}")
                self.conversations = {}
    
    def save(self):
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save memory: {e}")
    
    def add(self, channel_id: str, role: str, content: str):
        if channel_id not in self.conversations:
            self.conversations[channel_id] = []
        
        self.conversations[channel_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim to max history
        if len(self.conversations[channel_id]) > MAX_HISTORY:
            self.conversations[channel_id] = self.conversations[channel_id][-MAX_HISTORY:]
        
        self.save()
    
    def get_history(self, channel_id: str, limit: int = 20) -> List[Dict]:
        msgs = self.conversations.get(channel_id, [])
        return [{"role": m["role"], "content": m["content"]} for m in msgs[-limit:]]

# Initialize memory
memory = SimpleMemory(MEMORY_FILE)

async def get_ai_response(messages: List[Dict], system_prompt: str = None) -> str:
    """Get response from Groq"""
    
    formatted = []
    if system_prompt:
        formatted.append({"role": "system", "content": system_prompt})
    
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
    """Handle any message that starts with the prefix"""
    
    channel_id = str(message.channel.id)
    
    # Determine system prompt based on channel type
    if isinstance(message.channel, discord.DMChannel):
        channel_type = "DM"
    elif isinstance(message.channel, discord.GroupChannel):
        channel_type = "Group DM"
    else:
        channel_type = "Server"
    
    system_prompt = f"""You are a helpful AI assistant chatting in a Discord {channel_type}.
You have access to conversation history in this channel.
Be natural, helpful, and concise. Use Discord markdown."""

    # Add user message to memory
    memory.add(channel_id, "user", content)
    
    # Get conversation history
    history = memory.get_history(channel_id)
    
    # Generate response with typing indicator
    async with message.channel.typing():
        response = await get_ai_response(history, system_prompt)
    
    # Store AI response
    memory.add(channel_id, "assistant", response)
    
    # Send response
    await message.channel.send(response)

