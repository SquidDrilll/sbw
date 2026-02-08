import os
import asyncio
import random
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def harvest_history():
    """Learns the 'lore' of your chats without blocking the bot"""
    await bot.wait_until_ready()
    from chatbot import store
    print("🗿 hero is reading the lore... please wait.")
    
    for channel in bot.private_channels:
        try:
            # Scans 100 messages per chat to build deep memory
            async for msg in channel.history(limit=100):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            await asyncio.sleep(0.5) # Prevents discord bans
        except:
            continue
    print("✨ lore learned. hero knows everything now.")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    # Start harvesting in the background
    bot.loop.create_task(harvest_history())

@bot.event
async def on_message(message):
    # Loop prevention: Don't reply to the bot's own automated messages
    if message.author.id == bot.user.id:
        if not message.content.startswith(PREFIX):
            return

    if not message.content.startswith(PREFIX):
        return

    content = message.content[len(PREFIX):].strip()
    if not content:
        return

    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(TOKEN)
