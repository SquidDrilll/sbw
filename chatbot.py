import os
import asyncio
import random
import groq
import aiohttp
from database import MessageStore

# Load API keys from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY)
store = MessageStore()

async def get_ai_response(history, author_name):
    # Persona: Loyal to rowtten, 'Friendly Hater' to others
    persona = f"""
    you are 'hero 🗿', a legendary personality chatting in discord.
    you are currently replying to {author_name}.
    
    RULES:
    - ALWAYS start messages with: **hero 🗿 :**
    - you respect your owner (rowtten) deeply. be cool and loyal to them.
    - for everyone else ({author_name}), you are a 'friendly judge'. 
    - check history; if they said something stupid earlier, bring it up and roast them.
    - talk in lowercase, use slang (fr, lol, idk, ong, ratio, l, real).
    - keep it snappy and short (under 15 words). 
    - never say 'as an ai' or 'how can i help'. you are the main character.
    """

    try:
        # Primary AI: Groq (llama-3.1-8b-instant for speed/efficiency)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": persona}] + history
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback: OpenRouter (uses meta-llama 8b free tier)
        if OPENROUTER_KEY:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "system", "content": persona}] + history
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        return "idk man my brain is lagging rn"

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    author = str(message.author.name)
    
    # Store the incoming friend/owner message
    store.add(channel_id, author, content, "user")
    history = store.get_history(channel_id)
    
    response = await get_ai_response(history, author)
    
    # Human typing simulation based on message length
    typing_delay = (len(response) * 0.05) + random.uniform(0.7, 1.5)
    await asyncio.sleep(min(typing_delay, 4))
    
    # Force branding and lowercase style
    clean_text = response.replace("**hero 🗿 :**", "").strip().lower().lstrip("!?. ")
    final_output = f"**hero 🗿 :** {clean_text}"
    
    try:
        # Reply mode is safer and looks more interactive
        await message.reply(final_output, mention_author=False)
        store.add(channel_id, "AI", final_output, "assistant")
    except Exception as e:
        print(f"❌ Response failed: {e}")
