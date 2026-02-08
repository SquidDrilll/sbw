import os, asyncio, random, discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
# Using the self-bot wrapper library
bot = commands.Bot(command_prefix=os.getenv("PREFIX", "!"), self_bot=True)

async def harvest_lore():
    """Builds initial 100-message lore database on startup"""
    await bot.wait_until_ready()
    from chatbot import store
    print("🗿 hero is learning the lore... please wait.")
    
    for channel in bot.private_channels:
        try:
            async for msg in channel.history(limit=100):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            await asyncio.sleep(0.5)
        except: continue
    print("✨ lore learned. hero is ready to judge.")

@bot.event
async def on_ready():
    print(f"✅ hero online: {bot.user.name}")
    # Start background lore harvesting
    bot.loop.create_task(harvest_lore())

@bot.event
async def on_message(message):
    # Identity protection: ignore self-bot responses
    if message.author.id == bot.user.id:
        if not message.content.startswith("!"): return

    if not message.content.startswith("!"): return

    content = message.content[1:].strip().lower()

    # Deep Harvest command
    if content == "pull":
        from chatbot import backfill_history
        await backfill_history(message, bot)
        return

    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(os.getenv("DISCORD_TOKEN"))
