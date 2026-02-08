import os, discord, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

# 1. LOAD ENVIRONMENT VARIABLES
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", ".")

# 2. INITIALIZE BOT
# self_bot=True is required for user accounts
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def learn_lore():
    """Background task to index history without using AI tokens."""
    await bot.wait_until_ready()
    print("🗿 hero is background-harvesting lore...")
    for channel in bot.private_channels:
        try:
            # limit=100 is safe for startup
            async for msg in channel.history(limit=100):
                await msg_store.store(msg)
                await asyncio.sleep(0.1) 
        except: continue
    print("✨ lore sync complete.")

@bot.event
async def on_ready():
    await msg_store.init()
    # Run lore indexing in the background
    bot.loop.create_task(learn_lore())
    print(f"✅ hero 🗿 online. prefix: {PREFIX}")

@bot.event
async def on_message(message):
    # CRITICAL: Prevent the bot from replying to its own messages.
    # This stops the 'Startup Token Drain' loop.
    if message.author.id == bot.user.id:
        return
        
    # Process commands/chats if they start with your prefix
    if message.content.startswith(PREFIX):
        try:
            await handle_chat(message)
        except Exception as e:
            print(f"⚠️ Handler Error: {e}")

# 3. RUN THE BOT
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERROR: DISCORD_TOKEN not found in environment variables!")
