import os, discord, asyncio, logging
from discord.ext import commands

# Import from the new modular structure
from core.config import TOKEN, PREFIX
from core.database import db_manager
from discord_bot.chat_handler import handle_chat

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Main")

# Initialize Bot
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

@bot.event
async def on_ready():
    """Called when the bot connects to Discord."""
    logger.info(f"✅ Logged in as: {bot.user}")
    
    # Initialize Database Connection Pool
    await db_manager.init()
    
    # Optional: Print stats or perform startup tasks here
    logger.info("🚀 Hero Companion is online and ready.")

@bot.event
async def on_message(message):
    """Global message handler."""
    # Logic:
    # 1. Self-Bot Mode: We usually want to ignore ourselves to prevent loops.
    # 2. BUT: If the owner types a command explicitly (e.g. ".help"), we might want to run it.
    # 3. SAFETY: We must ensure we don't reply to our OWN AI RESPONSES.
    
    # Check if message starts with prefix
    if message.content.startswith(PREFIX):
        # Case A: Message is from the account owner (YOU)
        if message.author.id == bot.user.id:
            # Prevent infinite loops: Don't reply if it looks like an AI response (e.g. bold name prefix)
            # Adjust this check if your bot output format changes
            if message.content.startswith(f"**hero 🗿 :**"): 
                return
            
            logger.info(f"👑 Owner command detected: {message.content}")
            await handle_chat(message)
            return

        # Case B: Message is from another user
        await handle_chat(message)

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ ERROR: DISCORD_TOKEN is missing in environment variables.")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fatal Error running bot: {e}")
