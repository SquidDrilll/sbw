import os
import random
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

# Use the 'self_bot=True' for discord.py-self
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    print(f"📝 Use '{PREFIX}' to chat. Friends and you are both allowed!")

@bot.event
async def on_message(message):
    # 🛑 CRITICAL: Check if the message is from the bot itself
    # We only want to respond if the message starts with our PREFIX.
    # If the AI sends a message that happens to start with '!', we stop it here.
    if message.author.id == bot.user.id:
        if not message.content.startswith(PREFIX):
            return # Ignore my own AI responses
    
    # Only process if it starts with the prefix
    if not message.content.startswith(PREFIX):
        return

    content = message.content[len(PREFIX):].strip()
    if not content:
        return

    # ⏳ Random jitter to prevent Discord "Self-Bot" detection
    await asyncio.sleep(random.uniform(0.7, 1.5))
    
    from chatbot import handle_chat
    await handle_chat(message, content)

if __name__ == "__main__":
    bot.run(TOKEN)
