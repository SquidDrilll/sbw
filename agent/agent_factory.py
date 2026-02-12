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

def web_search(query: str, entity: str = None, **kwargs) -> str:
    """Search the web for real-time information."""
    if not EXA_API_KEY: return "Error: EXA_API_KEY missing."
    try:
        exa = Exa(api_key=EXA_API_KEY)
        response = exa.search_and_contents(query, num_results=EXA_NUM_RESULTS, use_autoprompt=True, text=True)
        return str(response)
    except Exception as e:
        return f"Search failed: {e}"

def scrape_website(url: str, **kwargs) -> str:
    """Scrape full content of a URL."""
    if not FIRECRAWL_API_KEY: return "Error: FIRECRAWL_API_KEY missing."
    if not FirecrawlApp: return "Error: firecrawl-py not installed."
    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        result = app.scrape_url(url, params={'formats': ['markdown']})
        return result.get('markdown', 'No content.')[:SCRAPE_MAX_CHARS]
    except Exception as e:
        return f"Scraping failed: {e}"

def create_hero_agent(api_key: str, history_str: str, model_id: str = None, is_openrouter: bool = False):
    """Creates the production Hero Agent with failover model support."""
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

    return Agent(
        model=chat_model,
        # Manual history injection is used instead of direct DB to avoid async crashes
        memory_manager=MemoryManager(model=memory_model),
        tools=[web_search, scrape_website, BioTools()],
        instructions=f"{PERSONA_TEXT}\n\nTime: {datetime.now(pytz.timezone(TZ)).strftime('%H:%M:%S')}\n\nContext:\n{history_str}",
        markdown=True
    )
