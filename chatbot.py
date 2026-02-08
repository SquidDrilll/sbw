import os
import asyncio
import random
import groq
import aiohttp
from database import MessageStore

# Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
client = groq.Groq(api_key=GROQ_API_KEY)
store = MessageStore()

async def get_ai_response(history, author_name):
    # The 'Hero' persona: Cool, judging, loyal to owner
    persona = f"""
    you are 'hero 🗿', a legendary personality chatting in discord.
    you are currently talking to {author_name}.
    
    RULES:
    - ALWAYS start messages with: **hero 🗿 :**
    - you respect your owner (rowtten) deeply. be cool and loyal to them.
    - for {author_name}, be a 'friendly judge'. if they said something weird in history, roast them.
    - talk in lowercase, use slang (fr, lol, idk, ong, ratio).
    - keep it snappy and short (under 15 words). 
    - you aren't a robot assistant; you are the main character.
    """

    try:
        # Primary: Groq
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": persona}] + history
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback: OpenRouter
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
        return "idk man my brain is fried rn"

async def handle_chat(message, content):
    channel_id = str(message.channel.id)
    author = str(message.author.name)
    
    store.add(channel_id, author, content, "user")
    history = store.get_history(channel_id)
    
    response = await get_ai_response(history, author)
    
    # Human typing simulation
    typing_delay = (len(response) * 0.05) + random.uniform(0.7, 1.5)
    await asyncio.sleep(min(typing_delay, 4))
    
    # Ensure branding is correct
    clean_text = response.replace("**hero 🗿 :**", "").strip().lower()
    final_output = f"**hero 🗿 :** {clean_text}"
    
    try:
        await message.reply(final_output, mention_author=False)
        store.add(channel_id, "AI", final_output, "assistant")
    except Exception as e:
        print(f"❌ Send failed: {e}")
