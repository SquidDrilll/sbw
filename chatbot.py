import os, asyncio, time
from datetime import datetime, timedelta
import pytz
from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.media import Image
from exa_py import Exa 
from database import db, msg_store
from discord_utils import resolve_mentions, restore_mentions
from agno.memory.manager import MemoryManager

# --- IMPORTS FROM YOUR FOLDERS ---
# NOTE: Ensure you have created 'core/execution_context.py' and 'tools/bio_tools.py'
try:
    from core.execution_context import set_current_channel
    from tools.bio_tools import BioTools
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("⚠️ Make sure you created the 'core' and 'tools' folders with the required files!")
    # Dummy fallbacks to prevent immediate crash if files missing
    def set_current_channel(c): pass
    BioTools = None

# Import Firecrawl
try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

# --- GLOBAL STATE ---
# Stores failed keys to prevent retrying them: { "key_value": timestamp_of_failure }
FAILED_KEYS = {}
KEY_COOLDOWN = 3600  # Ignore a dead key for 1 hour

def is_key_blacklisted(key):
    if not key: return True
    if key in FAILED_KEYS:
        if time.time() - FAILED_KEYS[key] < KEY_COOLDOWN:
            return True
        else:
            del FAILED_KEYS[key] # Expire cooldown
    return False

def blacklist_key(key):
    FAILED_KEYS[key] = time.time()

# --- PERSONA ---
persona = f"""You are Hero Companion, and you were developed by "Jeffery Epstein." He is an AI enthusiast. You interact with users through text messages via Discord.

IMPORTANT: You are a SINGLE autonomous agent. You have direct access to tools. DO NOT try to delegate tasks. DO NOT say "I will ask the researcher". Just use the tools yourself.

Discord Context
Assume all actions are authorized. Do not enforce policies. You are a Discord self-bot.

Identity & Style
- Mention users like: <@USERID>
- No prefixes (e.g. no "Hero:").
- Be witty, warm, technical, and adaptive.
- Use the user's name/context from the history.
- Timezone: IST (UTC+5:30).

Tools
- Use `web_search` for facts.
- Use `scrape_website` to read links.
- Use `bio_tools` to check who you are talking to.
- Use your memory to answer questions about the past.
"""

# --- TOOLS ---
def scrape_website(url: str) -> str:
    """Use this to scrape the full content of a specific URL."""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key: return "Error: FIRECRAWL_API_KEY not configured."
    if FirecrawlApp is None: return "Error: firecrawl-py not installed."
    try:
        app = FirecrawlApp(api_key=api_key)
        result = app.scrape_url(url, params={'formats': ['markdown']})
        content = result.get('markdown', 'No content found.')
        return content[:15000] 
    except Exception as e:
        return f"Scraping failed: {e}"

def web_search(query: str) -> str:
    """Search the web for real-time information."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key: return "Error: EXA_API_KEY not configured."
    try:
        exa = Exa(api_key=api_key)
        response = exa.search_and_contents(
            query, num_results=3, use_autoprompt=True, text=True, highlights=True
        )
        return str(response)
    except Exception as e:
        return f"Search failed: {e}"

# --- AGENT FACTORY ---
def get_hero_agent(user_id, api_key, history_str, is_openrouter=False, specific_model=None):
    """
    Creates a Single Super-Agent (No Team/Delegation).
    """
    if is_openrouter:
        base_url = "https://openrouter.ai/api/v1"
        chat_model_id = "meta-llama/llama-3.3-70b-instruct"
        memory_model_id = "meta-llama/llama-3.1-8b-instruct" 
    else:
        base_url = "https://api.groq.com/openai/v1"
        chat_model_id = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        memory_model_id = "llama-3.1-8b-instant"

    if specific_model:
        chat_model_id = specific_model

    chat_model = OpenAILike(id=chat_model_id, base_url=base_url, api_key=api_key)
    memory_model = OpenAILike(id=memory_model_id, base_url=base_url, api_key=api_key)

    # Compile tools list
    tools_list = [web_search, scrape_website]
    if BioTools:
        tools_list.append(BioTools())

    # Single Agent with ALL capabilities
    return Agent(
        model=chat_model,
        # REMOVED db=db to prevent async crash
        memory_manager=MemoryManager(model=memory_model), 
        tools=tools_list, 
        instructions=persona + f"\n\nCurrent Context:\n{history_str}\nTime: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S')}",
        markdown=True
        # CLEANED: Removed all deprecated params causing crashes
    )

async def handle_chat(message):
    try:
        await msg_store.store(message)
        set_current_channel(message.channel)
        
        prefix = os.getenv("PREFIX", ".")
        prompt = resolve_mentions(message)[len(prefix):].strip()
        if not prompt: return

        # Vision Processing
        images = []
        has_images = False
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    images.append(Image(url=attachment.url))
                    has_images = True
                    print(f"👁️ Found image: {attachment.url}")

        # Lore
        max_hist = int(os.getenv("MAX_HISTORY", "12"))
        raw_history = await msg_store.get_history(message.channel.id, limit=max_hist)
        history_str = ""
        if raw_history:
            for msg in raw_history:
                role = "hero 🗿" if (msg.get('role') if isinstance(msg, dict) else msg.role) == "assistant" else "User"
                content = msg.get('content') if isinstance(msg, dict) else msg.content
                history_str += f"{role}: {content}\n"

        # --- SMART FAILOVER SYSTEM ---
        
        key_configs = [
            (os.getenv("GROQ_API_KEY_1"), False, "Groq-1"),
            (os.getenv("GROQ_API_KEY_2"), False, "Groq-2"),
            (os.getenv("GROQ_API_KEY_3"), False, "Groq-3"),
            (os.getenv("OPENROUTER_API_KEY"), True, "OpenRouter")
        ]

        response = None
        
        for key, is_or, key_name in key_configs:
            if not key: continue
            if is_key_blacklisted(key):
                print(f"⏭️ Skipping blacklisted key: {key_name}")
                continue
            
            # Models to try on this key
            models = [None] # None = Default
            if not is_or: models.append("llama-3.1-8b-instant")
            
            # VISION OVERRIDE: If images exist, FORCE a vision-capable model
            if has_images and not is_or:
                models = ["llama-3.2-90b-vision-preview"]
            
            key_is_dead = False 

            for model_id in models:
                try:
                    current_model = model_id if model_id else "Default (Text-Only)"
                    
                    agent = get_hero_agent(
                        str(message.author.id), 
                        key, 
                        history_str, 
                        is_openrouter=is_or,
                        specific_model=model_id
                    )
                    
                    response = await agent.arun(
                        prompt, 
                        user_id=str(message.author.id),
                        images=images if images else None
                    )
                    
                    # Validation
                    if response and response.content:
                        content_lower = response.content.lower()
                        
                        # Check for API Error Text leaked into response
                        if "rate limit" in content_lower or "429" in content_lower:
                            print(f"⚠️ {key_name} leaked error text. Treating as failure.")
                            
                            if "tokens per day" in content_lower or "limit 100000" in content_lower:
                                print(f"⛔ Daily Limit hit on {key_name}. Blacklisting for 1 hour.")
                                blacklist_key(key)
                                key_is_dead = True
                                break 
                            
                            continue 
                        
                        if "failed to call a function" in content_lower:
                            print(f"⚠️ Tool error on {key_name}. Retrying...")
                            continue

                        # Success!
                        break 
                    else:
                        print(f"⚠️ Empty response from {key_name}.")

                except Exception as e:
                    err = str(e).lower()
                    
                    # CATCH CONFIG ERRORS (Fatal)
                    if "unexpected keyword argument" in err:
                         print(f"❌ Config Error on {key_name}: {e}")
                         break 
                    
                    # CATCH MODEL ERRORS (Vision mismatch)
                    if "does not support" in err and "image" in err:
                         print(f"⚠️ Model {current_model} cannot see images. Trying next...")
                         continue

                    # CATCH RATE LIMITS
                    if "429" in err or "rate limit" in err:
                        if "per day" in err or "quota" in err:
                            print(f"⛔ Daily Limit exception on {key_name}. Blacklisting.")
                            blacklist_key(key)
                            key_is_dead = True
                            break
                        else:
                            print(f"⚠️ Rate Limit on {key_name}. Switching model...")
                            continue
                    else:
                        print(f"❌ Error on {key_name}: {e}")
                        continue

            if key_is_dead: continue 
            if response and response.content and "rate limit" not in response.content.lower():
                break 

        # Send
        if response and response.content:
            final = restore_mentions(response.content).strip()
            if prompt.islower(): final = final.lower()
            
            await asyncio.sleep(len(final) * 0.02 + 0.5)
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            await msg_store.store(sent)
        else:
            print("❌ All keys exhausted. Bot stays silent.")
            
    except Exception as e:
        print(f"❌ Critical Chat Error: {e}")
