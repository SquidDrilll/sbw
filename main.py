import os, discord, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", ".")

# Initialize Bot
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def deep_sync():
    """Junkie-style background sync: Index history without AI tokens."""
    await bot.wait_until_ready()
    print("🗿 Starting deep lore sync...")
    
    if not bot.private_channels:
        print("ℹ️ No private channels loaded immediately. Waiting for cache...")
    
    # Iterate through visible channels (Note: Self-bots see many channels)
    # We limit strictly to private channels (DMs/Group DMs) to avoid spamming the DB
    count = 0
    for channel in bot.private_channels:
        try:
            async for msg in channel.history(limit=200):
                await msg_store.store(msg)
                count += 1
                if count % 50 == 0:
                    await asyncio.sleep(1) # Rate limit protection
            await asyncio.sleep(0.05)
        except Exception as e: 
            continue
            
    print(f"✨ Deep sync complete. Indexed messages.")

@bot.event
async def on_ready():
    print(f"✅ hero 🗿 online | Prefix: {PREFIX} | User: {bot.user}")
    await msg_store.init()
    bot.loop.create_task(deep_sync())

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
    print("❌ ERROR: No DISCORD_TOKEN found in environment variables.")
