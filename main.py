# main.py
import os
import sys
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configuration from environment only - no hardcoding
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PREFIX = os.getenv("PREFIX", "!")  # Default to ! if not set
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Validate required variables
if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable is required")
    sys.exit(1)
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY environment variable is required")
    sys.exit(1)

# Initialize bot with only the prefix from env
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name} ({bot.user.id})")
    print(f"📝 Using prefix: '{PREFIX}'")
    print(f"🤖 Model: {GROQ_MODEL}")
    print("Ready for commands!")

@bot.event
async def on_message(message):
    # Ignore own messages
    if message.author.id == bot.user.id:
        return
    
    # Only process messages starting with the prefix
    if not message.content.startswith(PREFIX):
        return
    
    # Remove prefix and get the actual content
    content = message.content[len(PREFIX):].strip()
    
    # Skip empty messages
    if not content:
        return
    
    # Route to chatbot handler
    from chatbot import handle_chat
    await handle_chat(message, content)

if __name__ == "__main__":
    bot.run(TOKEN)
