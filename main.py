import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

load_dotenv()
# Using self_bot=True is required for your discord.py-self setup
bot = commands.Bot(command_prefix="!", self_bot=True)

@bot.event
async def on_ready():
    # Properly initialize the store pool on startup
    await msg_store.init()
    print(f"✅ hero 🗿 online. Memory synced for {bot.user.name}.")

@bot.event
async def on_message(message):
    # Ignore your own bot's responses but process your own manual commands
    if message.author.id == bot.user.id and not message.content.startswith("!"):
        return
        
    if message.content.startswith("!"):
        await handle_chat(message)

bot.run(os.getenv("DISCORD_TOKEN"))
