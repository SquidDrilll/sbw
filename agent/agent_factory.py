import os, logging, pytz
from datetime import datetime
from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.memory.manager import MemoryManager
from exa_py import Exa
from core.config import *
from tools.bio_tools import BioTools

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
        return f"Search failed: {e}"

def scrape_website(url: str, **kwargs) -> str:
    """Scrape website using the global client."""
    if not firecrawl_client: return "Error: Firecrawl Client not initialized."
    try:
        result = firecrawl_client.scrape_url(url, params={'formats': ['markdown']})
        return result.get('markdown', 'No content.')[:SCRAPE_MAX_CHARS]
    except Exception as e:
        return f"Scraping failed: {e}"

def create_hero_agent(api_key: str, history_str: str, model_id: str = None, is_openrouter: bool = False):
    """Creates the production-grade Hero Agent."""
    
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
    
    return Agent(
        model=chat_model,
        memory_manager=MemoryManager(model=memory_model),
        tools=[web_search, scrape_website, BioTools()],
        instructions=f"{persona}\n\nTime: {datetime.now(pytz.timezone(TZ)).strftime('%H:%M:%S')}\n\nContext:\n{history_str}",
        markdown=True
    )
