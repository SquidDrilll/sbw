import os, discord, asyncio, logging, json
from discord.ext import commands

from core.config import TOKEN, PREFIX
from core.database import db_manager
from discord_bot.chat_handler import handle_chat
from tools.bio_tools import BioTools

# Production Structured Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage()
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("Main")

bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

# Global BioTools to prevent re-initialization overhead
bio_tools_instance = None

@bot.event
async def on_ready():
    global bio_tools_instance
    logger.info(f"✅ Logged in as: {bot.user}")
    await db_manager.init()
    
    # Inject bot instance directly into BioTools (No more private _state hacks)
    bio_tools_instance = BioTools(bot)
    logger.info("🚀 Hero Companion initialized.")

@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        if message.content.startswith(f"**hero 🗿 :**"): return
        if message.content.startswith(PREFIX):
            logger.info(f"👑 Owner command detected: {message.content}")
            await handle_chat(message, bot, bio_tools_instance)
        return

    if message.content.startswith(PREFIX):
        await handle_chat(message, bot, bio_tools_instance)

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ DISCORD_TOKEN missing.")
        exit(1)
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fatal Error running bot: {e}")
        
