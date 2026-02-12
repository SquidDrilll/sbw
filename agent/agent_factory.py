import os, logging, pytz
from datetime import datetime
from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.memory.manager import MemoryManager
from agno.tools import Toolkit
from exa_py import Exa
from core.config import *
from typing import Optional

# --- SAFE IMPORT FOR STORAGE ---
# This prevents the bot from crashing if 'agno.storage' is missing or updated.
try:
    from agno.storage.agent.postgres import PgAgentStorage
except ImportError:
    PgAgentStorage = None
    print("⚠️ WARNING: agno.storage module not found. Persistent memory will be disabled.")

# Import Firecrawl
try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

logger = logging.getLogger("AgentFactory")

# --- GLOBAL TOOL CLIENTS (Initialize Once) ---
exa_client = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None
firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY) if FIRECRAWL_API_KEY and FirecrawlApp else None

def web_search(query: str, entity: str = None, **kwargs) -> str:
    """Search the web using the global client."""
    if not exa_client: return "Error: Exa Client not initialized."
    try:
        response = exa_client.search_and_contents(query, num_results=EXA_NUM_RESULTS, use_autoprompt=True, text=True)
        return str(response)
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return "Error: Web search failed."

def scrape_website(url: str, **kwargs) -> str:
    """Scrape website using the global client."""
    if not firecrawl_client: return "Error: Firecrawl Client not initialized."
    try:
        result = firecrawl_client.scrape_url(url, params={'formats': ['markdown']})
        return result.get('markdown', 'No content.')[:SCRAPE_MAX_CHARS]
    except Exception as e:
        logger.error(f"Firecrawl scrape failed: {e}")
        return "Error: Website scraping failed."

def create_hero_agent(api_key: str, history_str: str, model_id: str = None, is_openrouter: bool = False, bio_tools: Optional[Toolkit] = None):
    """
    Creates the production-grade Hero Agent with Failover Memory.
    """
    
    if is_openrouter:
        base_url = "https://openrouter.ai/api/v1"
        chat_model_id = model_id or OPENROUTER_MODEL
        memory_model_id = os.getenv("OPENROUTER_MEMORY_MODEL", "meta-llama/llama-3.1-8b-instruct")
    else:
        base_url = "https://api.groq.com/openai/v1"
        chat_model_id = model_id or GROQ_MODEL
        memory_model_id = GROQ_MEMORY_MODEL

    chat_model = OpenAILike(id=chat_model_id, base_url=base_url, api_key=api_key)
    memory_model = OpenAILike(id=memory_model_id, base_url=base_url, api_key=api_key)

    # Use persona from config
    persona = PERSONA_TEXT
    
    # Compile tools list
    tools = [web_search, scrape_website]
    if bio_tools:
        tools.append(bio_tools)

    # --- STORAGE SETUP WITH FALLBACK ---
    storage = None
    if PgAgentStorage and POSTGRES_URL:
        try:
            # Convert asyncpg URL (used by bot DB) to standard postgres URL (used by SQLAlchemy/Agno)
            db_url = POSTGRES_URL
            if "postgresql+asyncpg" in db_url:
                db_url = db_url.replace("postgresql+asyncpg", "postgresql")
            
            # Initialize persistent storage for the Agent's brain
            storage = PgAgentStorage(table_name="hero_memories", db_url=db_url)
        except Exception as e:
            logger.error(f"Failed to init Postgres Storage: {e}")
            storage = None

    # Define Agent arguments
    agent_kwargs = {
        "model": chat_model,
        "add_history_to_messages": False, # Manual history injection
        "memory_manager": MemoryManager(model=memory_model),
        "tools": tools,
        "instructions": f"{persona}\n\nTime: {datetime.now(pytz.timezone(TZ)).strftime('%H:%M:%S')}\n\nContext:\n{history_str}",
        "markdown": True
    }

    # Only attach storage if it initialized correctly
    if storage:
        agent_kwargs["storage"] = storage
    else:
        # Fallback for debugging or if module is missing
        pass 

    return Agent(**agent_kwargs)
