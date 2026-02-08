import os, discord
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat

load_dotenv()
bot = commands.Bot(command_prefix="!", self_bot=True)

@bot.event
async def on_ready():
    await msg_store.init()
    print(f"✅ hero 🗿 online. Memory synced for {bot.user.name}.")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id or not message.content.startswith("!"):
        return
    await handle_chat(message)

bot.run(os.getenv("DISCORD_TOKEN"))
