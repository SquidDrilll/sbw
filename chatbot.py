import os, asyncio, random, groq, aiohttp
from database import MessageStore

client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
store = MessageStore()

async def get_ai_response(history, author_name):
    # IDENTITY LOCK: Explicitly defines the owner and the current target
    persona = f"""
    you are 'hero 🗿', the legendary personality. 
    CURRENTLY REPLYING TO: {author_name}
    
    IDENTITY LOCK:
    - rowtten (and SquidDrill) is your ONLY owner. be 100% loyal and cool to him. NEVER roast the owner.
    - {author_name} is just a person you judge based on the lore history.
    
    RULES:
    - ALWAYS start messages with: **hero 🗿 :**
    - talk in lowercase, use slang (fr, lol, ong, real, sus).
    - be a chill 'main character', not a polite assistant.
    - BREVITY: keep it under 12 words.
    """

    try:
        # Primary: Groq (llama-3.1-8b-instant)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": persona}] + history,
            temperature=0.7 # Lower temperature stops identity hallucinations
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback for reliability
        if os.getenv("OPENROUTER_API_KEY"):
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
                    json={
                        "model": "meta-llama/llama-3.1-8b-instruct:free",
                        "messages": [{"role": "system", "content": persona}] + history
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
        return "my bad, brain is lagging"

async def backfill_history(message, bot):
    """Deeply harvests 10,000 messages from the current channel"""
    channel_id = str(message.channel.id)
    await message.reply("**hero 🗿 :** hang on, reading the lore for this whole chat. don't spam.", mention_author=False)
    
    count = 0
    try:
        async for msg in message.channel.history(limit=10000):
            role = "assistant" if msg.author.id == bot.user.id else "user"
            store.add(channel_id, str(msg.author.name), msg.content, role)
            count += 1
            if count % 100 == 0: await asyncio.sleep(1.5) # Anti-ban jitter
        await message.reply(f"**hero 🗿 :** finished. learned {count} messages. i know everything now.", mention_author=False)
    except Exception as e:
        await message.reply(f"**hero 🗿 :** harvest failed: {e}", mention_author=False)

async def handle_chat(message, content):
    cid, author = str(message.channel.id), str(message.author.name)
    store.add(cid, author, content, "user")
    
    # Pulling 30 messages provides deep context to avoid identity confusion
    history = store.get_history(cid, limit=30)
    
    response = await get_ai_response(history, author)
    
    # Human-like delay logic
    await asyncio.sleep((len(response) * 0.05) + random.uniform(0.6, 1.3))
    
    # Force clean branding
    clean_text = response.replace("**hero 🗿 :**", "").strip().lower().lstrip("!?. ")
    final_output = f"**hero 🗿 :** {clean_text}"
    
    try:
        await message.reply(final_output, mention_author=False)
        store.add(cid, "AI", final_output, "assistant")
    except Exception as e:
        print(f"❌ error: {e}")
