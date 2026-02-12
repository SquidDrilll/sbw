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

bot = commands.Bot(command_prefix=PREFIX, self_bot=True, help_command=None)

bio_tools_instance = None

async def index_historical_messages():
    """
    Scans all accessible channels and reads the last 500 messages 
    on startup to build 'Global Memory'.
    """
    await bot.wait_until_ready()
    logger.info("🧠 Hero is starting historical indexing...")
    total_indexed = 0
    
    # FIX: Convert SequenceProxy to a list before concatenating
    all_channels = list(bot.private_channels)
    for guild in bot.guilds:
        # Filter for text channels the bot can actually read
        all_channels.extend(guild.text_channels)

    for channel in all_channels:
        try:
            # Check permissions for guild channels
            if hasattr(channel, 'guild') and channel.guild:
                perms = channel.permissions_for(channel.guild.me)
                if not perms or not perms.read_message_history:
                    continue

            async for msg in channel.history(limit=500):
                # We only index messages with content to save DB space and tokens
                if msg.content:
                    await db_manager.store_message(
                        msg.id, msg.channel.id, msg.author.id,
                        msg.author.display_name, msg.content, msg.created_at
                    )
                    total_indexed += 1
        except Exception:
            continue
            
    logger.info(f"✅ Indexing complete. Memorized {total_indexed} messages.")

@bot.event
async def on_ready():
    global bio_tools_instance
    logger.info(f"✅ Logged in as: {bot.user}")
    await db_manager.init()
    
    bio_tools_instance = BioTools(bot)
    
    # Run indexing in background to avoid blocking the bot's availability
    asyncio.create_task(index_historical_messages())
    logger.info("🚀 Hero Companion initialized and thinking.")

@bot.event
async def on_message(message):
    # Log everything to keep memories fresh
    if message.content:
        await db_manager.store_message(
            message.id, message.channel.id, message.author.id, 
            message.author.display_name, message.content, message.created_at
        )

    if message.author.id == bot.user.id:
        if message.content.startswith(PREFIX):
            await handle_chat(message, bot, bio_tools_instance)
        return

    # Respond to prefix or direct mentions
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
