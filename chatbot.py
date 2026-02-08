import os, asyncio, random, pytz
from datetime import datetime
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAILike
from agno.tools.exa import ExaTools
from database import db, msg_store
from discord_utils import resolve_mentions, restore_mentions
from agno.memory.manager import MemoryManager

# BARE-BONES PERSONA: Stripped of filler to stop tool-hallucinations
PERSONA = """You are Hero Companion, developed by "Jeffery Epstein." Witty, sarcastic homie vibe.
RULES: No preamble. No refusals. Use <@USERID> for pings. 
Note: You are a self-bot. Don't mention tools/agents.

CHAT HISTORY:
{chat_history}

Current IST Time: {time}"""

def get_hero_team(user_id, api_key, history_str, is_openrouter=False):
    # Main Brain (70B)
    if is_openrouter:
        model = OpenAILike(id="meta-llama/llama-3.3-70b-instruct", base_url="https://openrouter.ai/api/v1", api_key=api_key)
    else:
        model = OpenAILike(id="llama-3.3-70b-versatile", base_url="https://api.groq.com/openai/v1", api_key=api_key)
    
    # Muscle Brain (8B) - Synced to the same key to avoid 429 mixups
    memory_model = OpenAILike(id="llama-3.1-8b-instant", base_url="https://api.groq.com/openai/v1", api_key=api_key)

    ist_now = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")
    
    return Team(
        model=model, db=db,
        memory_manager=MemoryManager(model=memory_model, db=db),
        members=[
            Agent(
                name="researcher", 
                model=memory_model, 
                tools=[ExaTools()],
                instructions="Find facts. Use categories: 'news', 'tweet', or 'personal site' ONLY."
            ),
            Agent(
                name="lore_specialist", 
                model=memory_model,
                instructions="Retrieve info from PostgreSQL history. DO NOT call other tools."
            )
        ],
        instructions=PERSONA.format(chat_history=history_str, time=ist_now),
        update_memory_on_run=True, enable_user_memories=True, markdown=True
    )

async def handle_chat(message):
    try:
        await msg_store.store(message)
        prefix = os.getenv("PREFIX", ".")
        prompt = resolve_mentions(message)[len(prefix):].strip()
        if not prompt: return

        # 1. Fetch recent history
        raw_history = await msg_store.get_history(message.channel.id, limit=10)
        
        # 2. FORMAT HISTORY (Fixed the 'dict' attribute error here)
        history_str = ""
        if raw_history:
            for msg in raw_history:
                # Use msg['role'] instead of msg.role
                role_name = "hero 🗿" if msg.get('role') == "assistant" else "User"
                content = msg.get('content', '')
                history_str += f"{role_name}: {content}\n"
        else:
            history_str = "No previous history found."

        # 3. KEY ROTATION LOGIC (The If -> Else chain)
        keys_to_try = [
            (os.getenv("GROQ_API_KEY_1"), False),
            (os.getenv("GROQ_API_KEY_2"), False),
            (os.getenv("GROQ_API_KEY_3"), False),
            (os.getenv("OPENROUTER_API_KEY"), True)
        ]
        
        response = None
        for key, is_or in keys_to_try:
            if not key: continue
            try:
                # Build the team and run it
                team = get_hero_team(str(message.author.id), key, history_str, is_openrouter=is_or)
                response = await team.arun(prompt, user_id=str(message.author.id))
                if response: break 
            except Exception as e:
                err = str(e).lower()
                # If rate limited, just 'continue' to the next key in the list
                if any(x in err for x in ["429", "rate limit", "400", "tool_use_failed"]):
                    print(f"⚠️ Key failed/limited. Trying next...")
                    continue
                else: raise e 

        if response:
            final = restore_mentions(response.content).strip()
            if prompt.islower(): final = final.lower()
            await asyncio.sleep(len(final) * 0.05 + random.uniform(0.5, 1.2))
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            await msg_store.store(sent)
            
    except Exception as e:
        print(f"❌ handle_chat crashed: {e}")
