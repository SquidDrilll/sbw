import os, discord, asyncio, logging, json
from discord.ext import commands

from core.config import TOKEN, PREFIX
from core.database import db_manager
from discord_bot.chat_handler import handle_chat
from tools.bio_tools import BioTools

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

# self_bot=True is essential for personal account automation
bot = commands.Bot(command_prefix=PREFIX, self_bot=True, help_command=None)

bio_tools_instance = None

async def index_historical_messages():
    """
    Scans all accessible channels and reads the last 500 messages 
    on startup to build 'Global Memory'.
    """
    logger.info("🧠 Hero is starting historical indexing...")
    total_indexed = 0
    
    for channel in bot.private_channels + [c for g in bot.guilds for c in g.text_channels]:
        try:
            # Check permissions if in a guild
            if hasattr(channel, 'permissions_for'):
                perms = channel.permissions_for(channel.guild.me)
                if not perms.read_message_history or not perms.read_messages:
                    continue

            async for msg in channel.history(limit=500):
                await db_manager.store_message(
                    msg.id, msg.channel.id, msg.author.id,
                    msg.author.display_name, msg.content, msg.created_at
                )
                total_indexed += 1
        except Exception:
            continue
            
    logger.info(f"✅ Indexing complete. Memorized {total_indexed} messages across all servers.")

@bot.event
async def on_ready():
    global bio_tools_instance
    logger.info(f"✅ Logged in as: {bot.user}")
    await db_manager.init()
    
    bio_tools_instance = BioTools(bot)
    
    # Start the indexing in the background so the bot is usable immediately
    asyncio.create_task(index_historical_messages())
    logger.info("🚀 Hero Companion initialized and thinking.")

@bot.event
async def on_message(message):
    # Always log messages Hero sees to keep memory fresh
    await db_manager.store_message(
        message.id, message.channel.id, message.author.id, 
        message.author.display_name, message.content, message.created_at
    )

    if message.author.id == bot.user.id:
        if message.content.startswith(PREFIX):
            await handle_chat(message, bot, bio_tools_instance)
        return

    # Trigger chat if prefixed or mentioned
    if message.content.startswith(PREFIX) or bot.user.mentioned_in(message):
        await handle_chat(message, bot, bio_tools_instance)

if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ DISCORD_TOKEN missing.")
        exit(1)
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fatal Error running bot: {e}")
