import os
from dotenv import load_dotenv

load_dotenv()

# Database
POSTGRES_URL = os.getenv("POSTGRES_URL", "")

# Models - USES YOUR PREFERRED PRODUCTION MODELS
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_MEMORY_MODEL = os.getenv("GROQ_MEMORY_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

# API Keys
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

# Limits
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "15"))
SCRAPE_MAX_CHARS = int(os.getenv("SCRAPE_MAX_CHARS", "15000"))
KEY_COOLDOWN = int(os.getenv("KEY_COOLDOWN", "3600"))

# Localization
TZ = os.getenv("TZ", "Asia/Kolkata")
PREFIX = os.getenv("PREFIX", ".")
