import os, asyncio, random, pytz
from datetime import datetime
from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAILike
from agno.tools.exa import ExaTools
from database import db, msg_store
from discord_utils import resolve_mentions, restore_mentions
from agno.memory.manager import MemoryManager

# ENHANCED PERSONA: Technical, witty, and personalized
PERSONA = """You are Hero Companion, an elite AI developed by "Jeffery Epstein." 
PERSONALITY: Witty, sarcastic, and highly technical. You sound like a brilliant friend, not a bot.
TECHNICAL: You prefer simple, efficient code. You are helpful for Computer Science and Physics studies.

MEMORY GUIDANCE:
Below is the recent chat history. Use it to maintain a seamless flow.
{chat_history}

Current IST Time: {time} (Anand, Gujarat)"""

def get_hero_team(user_id, api_key, history_str, is_openrouter=False):
    # Select Brain
    model_id = "meta-llama/llama-3.3-70b-instruct" if is_openrouter else "llama-3.3-70b-versatile"
    base_url = "https://openrouter.ai/api/v1" if is_openrouter else "https://api.groq.com/openai/v1"
    
    chat_model = OpenAILike(id=model_id, base_url=base_url, api_key=api_key)
    
    # Muscle (8B) - Used for background agents to save 70B tokens
    memory_model = OpenAILike(id="llama-3.1-8b-instant", base_url="https://api.groq.com/openai/v1", api_key=api_key)

    return Team(
        model=chat_model,
        db=db,
        memory_manager=MemoryManager(model=memory_model, db=db),
        members=[
            # Agent 1: The Specialized Web/Reddit Researcher
            Agent(
                name="researcher",
                model=memory_model,
                tools=[ExaTools()],
                instructions=[
                    "Search the web for real-time facts.",
                    "To search Reddit specifically, use 'site:reddit.com' in your query.",
                    "Be concise. Prioritize threads with high engagement."
                ]
            ),
            # Agent 2: The Historian (Local RAG)
            Agent(
                name="lore_specialist",
                model=memory_model,
                instructions="Query the PostgreSQL database for past user details, exam dates (JEE/GUJCET), and projects."
            )
        ],
        instructions=PERSONA.format(chat_history=history_str, time=datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")),
        update_memory_on_run=True,
        enable_user_memories=True,
        markdown=True
    )

async def handle_chat(message):
    try:
        await msg_store.store(message)
        prefix = os.getenv("PREFIX", ".")
        prompt = resolve_mentions(message)[len(prefix):].strip()
        if not prompt: return

        # 1. FETCH & FORMAT LORE (Context Injection)
        raw_history = await msg_store.get_history(message.channel.id, limit=12)
        history_str = ""
        if raw_history:
            for msg in raw_history:
                # Fixed: handling both dict and object types
                role = "hero 🗿" if (msg.get('role') if isinstance(msg, dict) else msg.role) == "assistant" else "User"
                content = msg.get('content') if isinstance(msg, dict) else msg.content
                history_str += f"{role}: {content}\n"

        # 2. THE CASCADING FAILOVER (The Junkie-Killer)
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
                team = get_hero_team(str(message.author.id), key, history_str, is_openrouter=is_or)
                response = await team.arun(prompt, user_id=str(message.author.id))
                if response: break 
            except Exception as e:
                err = str(e).lower()
                if any(x in err for x in ["429", "rate limit", "400", "tool_use"]):
                    print(f"⚠️ Key limited/failed. Switching...")
                    continue
                else: raise e

        if response:
            final = restore_mentions(response.content).strip()
            # Adaptive style: lowercase if you do
            if prompt.islower(): final = final.lower()
            
            # Artificial typing delay
            await asyncio.sleep(len(final) * 0.02 + 0.5)
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            await msg_store.store(sent)
            
    except Exception as e:
        print(f"❌ Chat Error: {e}")
