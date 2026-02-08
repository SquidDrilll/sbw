# main.py
import os
import sys
import random
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PREFIX = os.getenv("PREFIX", "!")

if not TOKEN or not GROQ_API_KEY:
    raise ValueError("DISCORD_TOKEN and GROQ_API_KEY are required")

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} ({bot.user.id})")
    print(f"📝 Prefix: '{PREFIX}'")
    print("Ready!")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return
    
    if not message.content.startswith(PREFIX):
        return
    
    content = message.content[len(PREFIX):].strip()
    if not content:
        return
    
    # Add random delay to avoid rate limits
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    from chatbot import handle_chat
    await handle_chat(message, content)

if __name__ == "__main__":
    bot.run(TOKEN)
