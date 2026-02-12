import os, discord, asyncio, logging, json
from discord.ext import commands

# Import from the new modular structure
from core.config import TOKEN, PREFIX
from core.database import db_manager
from discord_bot.chat_handler import handle_chat
from tools.bio_tools import BioTools

# --- Production JSON Logging Setup ---
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

logger = logging.getLogger("Main")

# Initialize Bot
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

# Global Tool Instance (Initialized on Ready)
bio_tools_instance = None

@bot.event
async def on_ready():
    """Called when the bot connects to Discord."""
    global bio_tools_instance
    logger.info(f"✅ Logged in as: {bot.user}")
    
    # Initialize Database Connection Pool
    await db_manager.init()
    
    # Initialize BioTools with Dependency Injection
    # We create it ONCE and reuse it, solving the "Expensive Re-init" critique.
    bio_tools_instance = BioTools(bot)
    
    logger.info("🚀 Hero Companion is online and ready.")

@bot.event
async def on_message(message):
    """Global message handler."""
    if message.author.id == bot.user.id:
        if message.content.startswith(f"**hero 🗿 :**"): 
            return
        
        if message.content.startswith(PREFIX):
             logger.info(f"👑 Owner command detected: {message.content}")
             # Pass bot and bio_tools_instance
             await handle_chat(message, bot, bio_tools_instance)
        return

    if message.content.startswith(PREFIX):
        # Pass bot and bio_tools_instance
        await handle_chat(message, bot, bio_tools_instance)

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ ERROR: DISCORD_TOKEN is missing in environment variables.")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fatal Error running bot: {e}")
