import os, asyncio, time, logging, discord
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

async def handle_chat(message: discord.Message, bot: discord.Client, bio_tools):
    try:
        set_current_channel(message)
        
        # Human-like 'Thinking' status
        async with message.channel.typing():
            prompt = resolve_mentions(message)
            if prompt.startswith(PREFIX):
                prompt = prompt[len(PREFIX):].strip()

            if not prompt: return

            # 1. Build context from recent logs
            history_str = await build_history_string(message.channel.id, bot.user.id)

            images = [Image(url=a.url) for a in message.attachments if a.content_type and "image" in a.content_type]

            keys = [
                (os.getenv("GROQ_API_KEY_1"), False, "Groq-1"),
                (os.getenv("GROQ_API_KEY_2"), False, "Groq-2"),
                (os.getenv("OPENROUTER_API_KEY"), True, "OpenRouter")
            ]

            response = None
            for key, is_or, name in keys:
                if not key or is_blacklisted(key): continue
                
                # FIX: Explicitly determine model IDs to avoid undefined variable errors
                if images:
                    m_id = GROQ_VISION_MODEL
                else:
                    m_id = OPENROUTER_MODEL if is_or else GROQ_MODEL

                try:
                    agent = create_hero_agent(
                        key, history_str, 
                        model_id=m_id, 
                        is_openrouter=is_or, 
                        bio_tools=bio_tools
                    )
                    
                    response = await agent.arun(prompt, user_id=str(message.author.id), images=images if images else None)
                    
                    if response and response.content:
                        text = response.content.lower()
                        # Handle specific API rate limit strings
                        if any(x in text for x in ["rate limit", "429", "quota exceeded"]):
                            logger.warning(f"Key {name} rate limited.")
                            FAILED_KEYS[key] = time.time()
                            continue
                        break
                except Exception as e:
                    logger.error(f"Error on {name}: {e}")
                    continue
            
            if response and response.content:
                final = restore_mentions(response.content)
                
                # Human typing simulation delay
                await asyncio.sleep(min(len(final) * 0.02, 2.0)) 
                
                sent = await message.reply(final, mention_author=False)
                
                # Save Hero's own thoughts to memory
                await db_manager.store_message(
                    sent.id, sent.channel.id, sent.author.id, 
                    "Hero", sent.content, sent.created_at
                )

    except Exception as e:
        logger.exception("Critical fail in ChatHandler")
