import os, discord, asyncio
from discord.ext import commands
from dotenv import load_dotenv
from database import msg_store
from chatbot import handle_chat


load_dotenv()
PREFIX = os.getenv("PREFIX", ".")
bot = commands.Bot(command_prefix=PREFIX, self_bot=True)

async def learn_lore():
    """Background task to index history efficiently."""
    await bot.wait_until_ready()
    print("🗿 hero is learning the lore in the background...")
    for channel in bot.private_channels:
        try:
            # Reduce limit from 1000 to 200 for the initial sync
            async for msg in channel.history(limit=200):
                await msg_store.store(msg)
                # Add a tiny jitter to stay under RPM limits
                await asyncio.sleep(0.2) 
            await asyncio.sleep(2) # Pause between channels
        except: continue
    print("✨ lore indexing complete.")

@bot.command()
async def tldr(ctx, count: int = 50):
    """Summarizes the last N messages."""
    await ctx.message.delete(delay=1.0)
    messages = [m async for m in ctx.channel.history(limit=count)]
    lines = [f"{m.author.display_name}: {m.clean_content}" for m in reversed(messages)]
    prompt = "Summarize this Discord chat in 4-6 bullet points:\n\n" + "\n".join(lines)
    
    # Quick call to the model for the summary
    from chatbot import get_hero_team
    team = get_hero_team(str(ctx.author.id))
    summary = await team.arun(prompt)
    await ctx.send(f"**TL;DR:**\n{summary.content}")

@bot.event
async def on_ready():
    await msg_store.init()
    bot.loop.create_task(learn_lore())
    print(f"✅ hero 🗿 online. Prefix: {PREFIX}")

@bot.event
async def on_message(message):
    # CRITICAL: Never respond to yourself, even if the message starts with "."
    if message.author.id == bot.user.id:
        return
        
    if message.content.startswith(PREFIX):
        await handle_chat(message) 

bot.run(TOKEN)
