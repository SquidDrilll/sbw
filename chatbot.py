# chatbot.py
import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import groq

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "50"))

# Simple JSON file storage for messages
STORAGE_FILE = "gdm_memory.json"

class GDMMemory:
    def __init__(self):
        self.messages: Dict[str, List[Dict]] = {}  # channel_id -> messages
        self.load()
    
    def load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
            except:
                self.messages = {}
    
    def save(self):
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)
    
    def add_message(self, channel_id: str, author: str, content: str, timestamp: str):
        if channel_id not in self.messages:
            self.messages[channel_id] = []
        
        self.messages[channel_id].append({
            "author": author,
            "content": content,
            "timestamp": timestamp,
            "role": "user" if author != "Assistant" else "assistant"
        })
        
        # Keep only last N messages per channel
        self.messages[channel_id] = self.messages[channel_id][-MAX_HISTORY:]
        self.save()
    
    def get_context(self, channel_id: str, limit: int = 20) -> List[Dict]:
        msgs = self.messages.get(channel_id, [])
        return msgs[-limit:]
    
    def get_all_recent(self, hours: int = 24) -> List[Dict]:
        """Get recent messages from all GDMs for general knowledge"""
        all_msgs = []
        for channel_id, msgs in self.messages.items():
            all_msgs.extend(msgs[-10:])  # Last 10 from each
        return all_msgs[-50:]  # Max 50 total

memory = GDMMemory()
groq_client = groq.Groq(api_key=GROQ_API_KEY)

async def get_groq_response(messages: List[Dict], system_prompt: str = None) -> str:
    """Get response from Groq API"""
    
    formatted_msgs = []
    if system_prompt:
        formatted_msgs.append({"role": "system", "content": system_prompt})
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:  # Skip empty messages
            formatted_msgs.append({"role": role, "content": content})
    
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=formatted_msgs,
            max_tokens=4096,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

async def setup_chatbot(bot):
    """Initialize the chatbot"""
    print(f"Chatbot initialized with model: {GROQ_MODEL}")
    
    # Index existing Group DMs on startup
    gdm_count = 0
    for channel in bot.private_channels:
        if isinstance(channel, discord.GroupChannel):
            gdm_count += 1
            print(f"Found GDM: {channel.name or 'Unnamed'} ({channel.id})")
            # Load recent history
            async for msg in channel.history(limit=20):
                if msg.author.id != bot.user.id:
                    memory.add_message(
                        str(channel.id),
                        str(msg.author.name),
                        msg.content,
                        msg.created_at.isoformat()
                    )
    print(f"Indexed {gdm_count} Group DMs")
    
    # Setup commands
    await setup_commands(bot)

async def handle_gdm_message(message):
    """Handle incoming Group DM message"""
    
    channel_id = str(message.channel.id)
    author_name = str(message.author.name)
    content = message.content
    timestamp = message.created_at.isoformat()
    
    # Store the message
    memory.add_message(channel_id, author_name, content, timestamp)
    
    # Check if bot is mentioned or replied to
    bot_mentioned = bot.user in message.mentions
    is_reply = message.reference and message.reference.resolved
    replied_to_bot = False
    
    if is_reply and isinstance(message.reference.resolved, discord.Message):
        replied_to_bot = message.reference.resolved.author.id == bot.user.id
    
    # Auto-respond if mentioned or replied to
    if bot_mentioned or replied_to_bot:
        await generate_response(message)

async def generate_response(message):
    """Generate and send LLM response"""
    
    channel_id = str(message.channel.id)
    
    # Build context from this GDM history
    context = memory.get_context(channel_id, limit=15)
    
    # Add current message if not already there
    current_msg = {
        "role": "user",
        "content": f"{message.author.name}: {message.content}"
    }
    
    # System prompt with personality
    system_prompt = """You are a helpful AI assistant in a Discord Group DM. You have access to the conversation history.
    
Rules:
- Be conversational and natural
- Reference previous context when relevant
- Keep responses concise but informative
- If you don't know something, say so
- Use Discord markdown formatting
- You can see all messages in this group"""

    messages = context + [current_msg]
    
    # Show typing indicator
    async with message.channel.typing():
        response = await get_groq_response(messages, system_prompt)
    
    # Store assistant response
    memory.add_message(channel_id, "Assistant", response, datetime.now().isoformat())
    
    # Send reply (as reply if it was a reply to us)
    if message.reference:
        await message.reply(response, mention_author=False)
    else:
        await message.channel.send(response)

async def setup_commands(bot):
    
    @bot.command(name="ask")
    async def ask(ctx, *, question: str):
        """Ask the AI anything using all GDM knowledge"""
        
        # Get recent context from all GDMs
        recent_context = memory.get_all_recent(hours=48)
        
        system_prompt = """You are a personal AI assistant with access to the user's recent Discord Group DM conversations across all groups.
        
You can:
- Answer questions about recent conversations
- Summarize what people have been talking about
- Provide insights or advice based on context
- Answer general knowledge questions
        
Be helpful, concise, and reference specific conversations when relevant."""
        
        messages = recent_context + [{"role": "user", "content": f"User asks: {question}"}]
        
        async with ctx.typing():
            response = await get_groq_response(messages, system_prompt)
        
        await ctx.send(f"**🤖:** {response}")
    
    @bot.command(name="summary")
    async def summary(ctx, hours: int = 24):
        """Summarize recent GDM activity"""
        
        recent = memory.get_all_recent(hours=hours)
        
        if not recent:
            await ctx.send("No recent messages found.")
            return
        
        system_prompt = f"Summarize the following Discord Group DM conversations from the last {hours} hours. Highlight key topics, decisions, and important messages."
        
        context_str = "\n".join([f"{m['author']}: {m['content']}" for m in recent[-30:]])
        
        async with ctx.typing():
            response = await get_groq_response(
                [{"role": "user", "content": f"Recent messages:\n{context_str}\n\nProvide a summary:"}],
                system_prompt
            )
        
        await ctx.send(f"**📊 Summary (last {hours}h):**\n{response}")
    
    @bot.command(name="remember")
    async def remember(ctx, *, info: str):
        """Store a specific fact/memory"""
        memory.add_message(
            "personal_notes",
            "User",
            f"Remember: {info}",
            datetime.now().isoformat()
        )
        await ctx.send("✅ Got it, I'll remember that.")
    
    @bot.command(name="recall")
    async def recall(ctx, *, topic: str = None):
        """Recall stored memories or search context"""
        
        notes = memory.messages.get("personal_notes", [])
        
        if topic:
            # Search for relevant memories
            relevant = [n for n in notes if topic.lower() in n['content'].lower()]
            if relevant:
                content = "\n".join([f"• {n['content']}" for n in relevant[-5:]])
                await ctx.send(f"**📝 Memories about '{topic}':**\n{content}")
            else:
                await ctx.send(f"No memories found about '{topic}'")
        else:
            # Show recent memories
            if notes:
                content = "\n".join([f"• {n['content']}" for n in notes[-5:]])
                await ctx.send(f"**📝 Recent memories:**\n{content}")
            else:
                await ctx.send("No memories stored yet.")
    
    print("Commands registered: !ask, !summary, !remember, !recall")
