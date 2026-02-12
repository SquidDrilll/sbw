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
        
        # Simulate 'Thinking' - Trigger typing indicator
        async with message.channel.typing():
            prompt = resolve_mentions(message)
            # Remove prefix if present
            if prompt.startswith(PREFIX):
                prompt = prompt[len(PREFIX):].strip()

            # 1. Fetch Local Context
            history_str = await build_history_string(message.channel.id, bot.user.id)

            # 2. Add 'Inner Monologue' to instructions to force memory usage
            # If the prompt mentions a name, we nudge the agent to recall them.
            images = [Image(url=a.url) for a in message.attachments if a.content_type and "image" in a.content_type]

            keys = [
                (os.getenv("GROQ_API_KEY_1"), False, "Groq-1"),
                (os.getenv("GROQ_API_KEY_2"), False, "Groq-2"),
                (os.getenv("OPENROUTER_API_KEY"), True, "OpenRouter")
            ]

            response = None
            for key, is_or, name in keys:
                if not key or is_blacklisted(key): continue
                
                m_id = GROQ_VISION_MODEL if images else (model_id if not is_or else None)

                try:
                    agent = create_hero_agent(
                        key, history_str, 
                        model_id=m_id, 
                        is_openrouter=is_or, 
                        bio_tools=bio_tools
                    )
                    
                    # Run the agent
                    response = await agent.arun(prompt, user_id=str(message.author.id), images=images if images else None)
                    
                    if response and response.content:
                        text = response.content.lower()
                        if any(x in text for x in ["rate limit", "429", "quota"]):
                            FAILED_KEYS[key] = time.time()
                            continue
                        break
                except Exception as e:
                    logger.error(f"Error on {name}: {e}")
                    continue
            
            if response and response.content:
                # 3. Final Humanization
                final = restore_mentions(response.content)
                
                # Small delay to make 'typing' feel real
                await asyncio.sleep(len(final) * 0.01) 
                
                sent = await message.reply(final, mention_author=False)
                
                await db_manager.store_message(
                    sent.id, sent.channel.id, sent.author.id, 
                    "Hero", sent.content, sent.created_at
                )

    except Exception as e:
        logger.exception("Critical fail in ChatHandler")
