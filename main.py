import os, asyncio, random, discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

# Self-bot setup
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def harvest_lore():
    """Builds initial lore database on startup (last 100 msgs)"""
    await bot.wait_until_ready()
    from chatbot import store
    print("🗿 hero is learning the lore... please wait.")
    
    for channel in bot.private_channels:
        try:
            async for msg in channel.history(limit=10000):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            await asyncio.sleep(0.5)
        except: continue
    print("✨ lore learned. hero is ready to judge.")

@bot.event
async def on_ready():
    print(f"✅ hero online as {bot.user.name}")
    # Start background lore harvesting
    bot.loop.create_task(harvest_lore())

@bot.event
async def on_message(message):
    # Ignore own automated messages to prevent loops
    if message.author.id == bot.user.id:
        if not message.content.startswith(PREFIX):
            return

    # Trigger only on the prefix (e.g., !)
    if not message.content.startswith(PREFIX):
        return

    content = message.content[1:].strip().lower()

    # The manual deep pull command
    if content == "pull":
        from chatbot import backfill_history
        await backfill_history(message, bot)
        return

    # Send to the judging engine
    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(TOKEN)
