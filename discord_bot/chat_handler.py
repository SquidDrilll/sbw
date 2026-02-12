import os, asyncio, time, logging
from agno.media import Image
from core.config import *
from core.database import db_manager
from core.execution_context import set_current_channel
from agent.agent_factory import create_hero_agent
from discord_bot.discord_utils import resolve_mentions, restore_mentions
from discord_bot.context_cache import build_history_string

logger = logging.getLogger("ChatHandler")
FAILED_KEYS = {}

def is_blacklisted(key):
    if key in FAILED_KEYS and time.time() - FAILED_KEYS[key] < KEY_COOLDOWN:
        return True
    return False

async def handle_chat(message, bot_id):
    try:
        set_current_channel(message.channel)
        
        prompt = resolve_mentions(message)[len(PREFIX):].strip()
        if not prompt: return

        # 1. Fetch History FIRST (excluding current message) - Fixes "Echo Chamber"
        # We pass the bot's ID so it knows which messages are its own
        history_str = await build_history_string(message.channel.id, bot_id)

        # 2. Store Incoming Message (After fetching history)
        await db_manager.store_message(
            message.id, message.channel.id, message.author.id, 
            message.author.display_name, message.clean_content, message.created_at
        )

        # 3. Vision
        images = [Image(url=a.url) for a in message.attachments if a.content_type and "image" in a.content_type]

        # 4. Failover Execution
        keys = [
            (os.getenv("GROQ_API_KEY_1"), False, "Groq-1"),
            (os.getenv("GROQ_API_KEY_2"), False, "Groq-2"),
            (os.getenv("GROQ_API_KEY_3"), False, "Groq-3"),
            (os.getenv("OPENROUTER_API_KEY"), True, "OpenRouter")
        ]

        response = None
        for key, is_or, name in keys:
            if not key or is_blacklisted(key): continue
            
            # Model Selection
            models = [None] if not images else [GROQ_VISION_MODEL]
            if not is_or and not images: models.append(GROQ_MEMORY_MODEL)

            for m_id in models:
                try:
                    # Pass is_owner=True if you want owner-specific logic, but basic chat works for all
                    agent = create_hero_agent(key, history_str, model_id=m_id, is_openrouter=is_or)
                    response = await agent.arun(prompt, user_id=str(message.author.id), images=images if images else None)
                    
                    if response and response.content:
                        text = response.content.lower()
                        if any(x in text for x in ["rate limit", "429", "quota", "<function"]):
                            logger.warning(f"{name} soft failure. Switching...")
                            if "limit 100000" in text: FAILED_KEYS[key] = time.time()
                            continue
                        break
                except Exception as e:
                    logger.error(f"Error on {name}: {e}")
                    continue
            if response and response.content and "rate limit" not in response.content.lower(): break

        # 5. Reply & Store Response
        if response and response.content:
            final = restore_mentions(response.content)
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            await db_manager.store_message(
                sent.id, sent.channel.id, sent.author.id, 
                "hero 🗿", sent.clean_content, sent.created_at
            )

    except Exception as e:
        logger.exception("Critical fail in ChatHandler")
