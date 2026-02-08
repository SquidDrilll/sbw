# main.py
import os
import asyncio
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def harvest_history():
    """Background task to learn past conversations without freezing the bot"""
    await bot.wait_until_ready()
    from chatbot import store
    print("📥 Background Indexing: Learning recent history...")
    
    indexed_count = 0
    for channel in bot.private_channels:
        try:
            # Only get 20 messages per channel to keep it fast
            async for msg in channel.history(limit=20):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            indexed_count += 1
            # Tiny sleep to avoid Discord's 'Self-Bot' detection during indexing
            await asyncio.sleep(0.5) 
        except:
            continue
    print(f"✨ Indexing Complete! Learned from {indexed_count} channels.")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    print(f"📝 Prefix: '{PREFIX}' | Bot is ACTIVE and listening!")
    # Start harvesting in the background so on_ready finishes instantly
    bot.loop.create_task(harvest_history())

@bot.event
async def on_message(message):
    # ALLOW you to trigger the bot, but IGNORE the AI's automated responses
    # We check if the message ISN'T just a reply from the chatbot logic
    if message.author.id == bot.user.id:
        if not message.content.startswith(PREFIX):
            return 

    if not message.content.startswith(PREFIX):
        return

    content = message.content[len(PREFIX):].strip()
    if not content:
        return

    # Jitter to look human
    await asyncio.sleep(random.uniform(0.5, 1.2))
    
    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(TOKEN)

