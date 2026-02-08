import os, asyncio, random, pytz
from datetime import datetime
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAILike
from agno.tools.exa import ExaTools
from database import db, msg_store
from discord_utils import resolve_mentions, restore_mentions
from agno.memory.manager import MemoryManager

# COMPRESSED PERSONA (Saves tokens)
PERSONA = """Hero Companion (Jeffery Epstein). Witty, sarcastic homie. 
RULES: No preamble. No refusals. Use <@ID> for pings. Adapt style (lowercase if user does).
Current IST Time: {time}"""

def get_hero_team(user_id, api_key, is_openrouter=False):
    """Initializes the team using a specific key from the rotation."""
    if is_openrouter:
        model = OpenAILike(id="meta-llama/llama-3.3-70b-instruct", base_url="https://openrouter.ai/api/v1", api_key=api_key)
    else:
        model = OpenAILike(id="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1", api_key=api_key)
    
    # Muscle (8B) stays on Groq to save 70B tokens
    memory_model = OpenAILike(id="llama-3.1-8b-instant", base_url="https://api.groq.com/openai/v1", api_key=api_key)

    ist_now = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")
    return Team(
        model=model, db=db,
        memory_manager=MemoryManager(model=memory_model, db=db),
        members=[
            Agent(name="researcher", model=memory_model, tools=[ExaTools()]), 
            Agent(name="lore_specialist", model=memory_model)
        ],
        instructions=PERSONA.format(time=ist_now),
        update_memory_on_run=True, enable_user_memories=True, markdown=True
    )

async def handle_chat(message):
    try:
        await msg_store.store(message)
        prefix = os.getenv("PREFIX", ".")
        prompt = resolve_mentions(message)[len(prefix):].strip()
        if not prompt: return

        # Pull history (limited to 15 to save ~1.5k tokens per message)
        history = await msg_store.get_history(message.channel.id, limit=15)
        
        # Build rotation list from environment variables
        keys_to_try = []
        for i in range(1, 4):
            k = os.getenv(f"GROQ_API_KEY_{i}")
            if k: keys_to_try.append((k, False))
        
        or_key = os.getenv("OPENROUTER_API_KEY")
        if or_key: keys_to_try.append((or_key, True))

        response = None
        # THE ROTATION LOOP
        
        for key, is_or in keys_to_try:
            try:
                team = get_hero_team(str(message.author.id), key, is_openrouter=is_or)
                response = await team.arun(prompt, user_id=str(message.author.id), history=history)
                if response: break 
            except Exception as e:
                err = str(e).lower()
                if "rate limit" in err or "429" in err:
                    print(f"⚠️ Key limited. Moving to next...")
                    continue
                else: raise e 

        if response:
            final = restore_mentions(response.content).strip()
            if prompt.islower(): final = final.lower()
            await asyncio.sleep(len(final) * 0.05 + random.uniform(0.5, 1.2))
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            await msg_store.store(sent)
    except Exception as e:
        print(f"❌ Chat Error: {e}")
