import os
import asyncio
import random
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!") # Default trigger is !

# self_bot=True is required for user account tokens
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def harvest_history():
    """Learns the 'lore' of your chats without blocking the bot's startup"""
    await bot.wait_until_ready()
    from chatbot import store
    print("🗿 hero is loading lore... indexing channels.")
    
    for channel in bot.private_channels:
        try:
            # Scans 100 messages per channel to populate judging memory
            async for msg in channel.history(limit=100):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            # Brief sleep to avoid Discord's automation detection
            await asyncio.sleep(0.5) 
        except:
            continue
    print("✨ lore learned. hero knows everything now.")

@bot.event
async def on_ready():
    print(f"✅ hero is online: {bot.user.name}")
    # Start the history harvester in the background
    bot.loop.create_task(harvest_history())

@bot.event
async def on_message(message):
    # STOP THE LOOP: Never reply to the bot's own AI messages
    if message.author.id == bot.user.id:
        if not message.content.startswith(PREFIX):
            return

    # Trigger only on the prefix
    if not message.content.startswith(PREFIX):
        return

    content = message.content[len(PREFIX):].strip()
    if not content:
        return

    # Pass to the judging engine
    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(TOKEN)
