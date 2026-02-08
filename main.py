import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
# This pulls the "." from your variables; defaults to "!" if not found
PREFIX = os.getenv("PREFIX", "!") 

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

@bot.event
async def on_ready():
    await msg_store.init()
    print(f"✅ hero 🗿 online. prefix is set to: {PREFIX}")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id and not message.content.startswith(PREFIX):
        return
        
    if message.content.startswith(PREFIX):
        # Pass the message to the handler
        await handle_chat(message) 

bot.run(TOKEN)
