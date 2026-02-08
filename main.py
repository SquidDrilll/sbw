import os, asyncio, random, discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
# Self-bot=True is required for user account tokens
bot = commands.Bot(command_prefix=os.getenv("PREFIX", "!"), self_bot=True)

async def harvest_history():
    """Builds initial lore memory on startup (last 100 msgs)"""
    await bot.wait_until_ready()
    from chatbot import store
    print("🗿 hero is learning the lore...")
    
    for channel in bot.private_channels:
        try:
            async for msg in channel.history(limit=100):
                role = "assistant" if msg.author.id == bot.user.id else "user"
                store.add(str(channel.id), str(msg.author.name), msg.content, role)
            await asyncio.sleep(0.5)
        except: continue
    print("✨ lore learned.")

@bot.event
async def on_ready():
    print(f"✅ hero online as {bot.user.name}")
    bot.loop.create_task(harvest_history())

@bot.event
async def on_message(message):
    # Ignore own AI responses to prevent loops
    if message.author.id == bot.user.id:
        if not message.content.startswith("!"): return

    if not message.content.startswith("!"): return

    content = message.content[1:].strip().lower()

    # Manual deep pull command
    if content == "pull":
        from chatbot import backfill_history
        await backfill_history(message, bot)
        return

    from chatbot import handle_chat
    await handle_chat(message, content)

bot.run(os.getenv("DISCORD_TOKEN"))
