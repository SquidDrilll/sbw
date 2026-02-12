import os, asyncio, time, logging
from agno.media import Image
from core.config import *
from core.database import db_manager
from core.execution_context import set_current_channel
from agent.agent_factory import create_hero_agent
from discord_utils import resolve_mentions, restore_mentions

logger = logging.getLogger("ChatHandler")
FAILED_KEYS = {}

async def build_history_string(channel_id: int) -> str:
    history = await db_manager.get_messages(channel_id, limit=MAX_HISTORY)
    if not history: return "No history."
    return "\n".join([f"{m['author_name']}: {m['content']}" for m in history])

async def handle_chat(message):
    try:
        # Store incoming message
        await db_manager.store_message(
            message.id, message.channel.id, message.author.id, 
            message.author.name, message.clean_content, message.created_at
        )
        set_current_channel(message.channel)
        
        prompt = resolve_mentions(message)[len(PREFIX):].strip()
        if not prompt: return

        # Prep context
        images = [Image(url=a.url) for a in message.attachments if a.content_type and "image" in a.content_type]
        history_str = await build_history_string(message.channel.id)

        # Failover Strategy
        keys = [
            (os.getenv("GROQ_API_KEY_1"), False, "Groq-1"),
            (os.getenv("GROQ_API_KEY_2"), False, "Groq-2"),
            (os.getenv("GROQ_API_KEY_3"), False, "Groq-3"),
            (os.getenv("OPENROUTER_API_KEY"), True, "OpenRouter")
        ]

        response = None
        for key, is_or, name in keys:
            if not key or (key in FAILED_KEYS and time.time() - FAILED_KEYS[key] < KEY_COOLDOWN):
                continue
            
            # Decide models: Vision override or standard primary -> secondary
            models = [None] if not images else [GROQ_VISION_MODEL]
            if not is_or and not images: models.append(GROQ_MEMORY_MODEL)

            for m_id in models:
                try:
                    agent = create_hero_agent(key, history_str, model_id=m_id, is_openrouter=is_or)
                    response = await agent.arun(prompt, user_id=str(message.author.id), images=images if images else None)
                    
                    if response and response.content:
                        text = response.content.lower()
                        # Detect leaked API errors in text
                        if any(x in text for x in ["rate limit", "429", "quota", "<function"]):
                            logger.warning(f"{name} leaked error text. Switching...")
                            if "limit 100000" in text: FAILED_KEYS[key] = time.time()
                            continue
                        break
                except Exception as e:
                    logger.error(f"Error on {name}: {e}")
                    continue
            if response and response.content and "rate limit" not in response.content.lower():
                break

        if response and response.content:
            final = restore_mentions(response.content)
            sent = await message.reply(f"**hero 🗿 :** {final}", mention_author=False)
            # Store bot response
            await db_manager.store_message(sent.id, sent.channel.id, sent.author.id, "hero 🗿", sent.clean_content, sent.created_at)

    except Exception as e:
        logger.exception("Critical fail in ChatHandler")
