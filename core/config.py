import os
from dotenv import load_dotenv

load_dotenv()

# Discord
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", ".")

# Database
POSTGRES_URL = os.getenv("POSTGRES_URL", "")

# Models (Controlled by Railway Variables)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MEMORY_MODEL = os.getenv("GROQ_MEMORY_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")
OPENROUTER_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "meta-llama/llama-3.3-70b-instruct")

# Tools Config
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
EXA_NUM_RESULTS = int(os.getenv("EXA_NUM_RESULTS", "3"))
SCRAPE_MAX_CHARS = int(os.getenv("SCRAPE_MAX_CHARS", "15000"))

# Bot Logic
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "15"))
KEY_COOLDOWN = int(os.getenv("KEY_COOLDOWN", "3600"))
TZ = os.getenv("TZ", "Asia/Kolkata")

# Persona (Can be set in Railway as a long string)
DEFAULT_PERSONA = """You are Hero Companion, and you were developed by "Jeffery Epstein." He is an AI enthusiast. You interact with users through text messages via Discord..."""
PERSONA_TEXT = os.getenv("PERSONA_TEXT", DEFAULT_PERSONA)
