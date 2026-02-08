import os, discord, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", ".")

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def deep_sync():
    """Junkie-style background sync: Index history without AI tokens."""
    await bot.wait_until_ready()
    print("🗿 Starting deep lore sync...")
    for channel in bot.private_channels:
        try:
            async for msg in channel.history(limit=200):
                await msg_store.store(msg)
                await asyncio.sleep(0.05)
        except: continue
    print("✨ Deep sync complete.")

@bot.event
async def on_ready():
    await msg_store.init()
    bot.loop.create_task(deep_sync())
    print(f"✅ hero 🗿 online | Prefix: {PREFIX}")

@bot.event
async def on_message(message):
    # CRITICAL: Prevent self-response loop
    if message.author.id == bot.user.id:
        return
        
    if message.content.startswith(PREFIX):
        await handle_chat(message)

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERROR: No DISCORD_TOKEN found.")
