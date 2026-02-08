# main.py
import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
PREFIX = os.getenv("PREFIX", "!")
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN or not GROQ_API_KEY:
    raise ValueError("DISCORD_TOKEN and GROQ_API_KEY are required")

# Discord selfbot setup (user account, not bot account)
intents = discord.Intents.all()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.dm_channels = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, self_bot=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Monitoring all Group DMs...")
    
    # Load chatbot module after bot is ready
    from chatbot import setup_chatbot
    await setup_chatbot(bot)

@bot.event
async def on_message(message):
    # Ignore own messages to prevent loops
    if message.author.id == bot.user.id:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Handle Group DM messages
    if isinstance(message.channel, discord.GroupChannel):
        from chatbot import handle_gdm_message
        await handle_gdm_message(message)

if __name__ == "__main__":
    bot.run(TOKEN)
