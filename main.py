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
    # 1. Ignore messages sent by the bot itself
    if message.author.id == bot.user.id:
        return

    # 2. Check for prefix (e.g., ".")
    if message.content.startswith(PREFIX):
        # Pass control to the specialized chat handler
        await handle_chat(message)

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ ERROR: DISCORD_TOKEN is missing in environment variables.")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fatal Error running bot: {e}")
