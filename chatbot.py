import os, asyncio, random, groq, aiohttp
from database import MessageStore

client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
store = MessageStore()

async def get_ai_response(history, author_name):
    # Recalibrated Persona: Loyal to rowtten, cool/judging to others
    persona = f"""
    you are 'hero 🗿', the legendary personality. replying to: {author_name}.
    
    IDENTITY RULES:
    - ALWAYS start messages with: **hero 🗿 :**
    - OWNER RULES: rowtten (and alts like SquidDrill) is your ONLY owner. be 100% loyal and respectful to them. NEVER roast the owner.
    - FRIEND RULES: for everyone else ({author_name}), be a 'cool judge'. judge their past lore/messages from history.
    - STYLE: talk in lowercase. use slang (fr, lol, ong, real).
    - TONE: be a chill 'main character'. do NOT be toxic or say 'stfu'. be cool, not mean.
    - BREVITY: keep it under 12 words.
    """

    try:
        # Primary: Groq
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": persona}] + history
        )
        return response.choices[0].message.content
    except Exception:
        # Fallback: OpenRouter Free Tier
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
        return "my brain is lagging lol"

async def backfill_history(message, bot):
    """Deeply harvests messages from the current channel up to 10k"""
    channel_id = str(message.channel.id)
    await message.reply("**hero 🗿 :** hang on, i'm reading the lore for this chat. don't spam.", mention_author=False)
    
    count = 0
    try:
        async for msg in message.channel.history(limit=10000):
            role = "assistant" if msg.author.id == bot.user.id else "user"
            store.add(channel_id, str(msg.author.name), msg.content, role)
            count += 1
            if count % 100 == 0: await asyncio.sleep(1.5) # Anti-ban delay
        await message.reply(f"**hero 🗿 :** finished. memorized {count} messages. i know everything now.", mention_author=False)
    except Exception as e:
        await message.reply(f"**hero 🗿 :** deep harvest failed: {e}", mention_author=False)

async def handle_chat(message, content):
    cid, author = str(message.channel.id), str(message.author.name)
    store.add(cid, author, content, "user")
    history = store.get_history(cid, limit=25)
    
    response = await get_ai_response(history, author)
    
    # Typing delay based on length to look human
    await asyncio.sleep((len(response) * 0.05) + random.uniform(0.5, 1.2))
    
    # Ensure branding and lowercase style
    clean_text = response.replace("**hero 🗿 :**", "").strip().lower().lstrip("!?. ")
    final_output = f"**hero 🗿 :** {clean_text}"
    
    try:
        await message.reply(final_output, mention_author=False)
        store.add(cid, "AI", final_output, "assistant")
    except Exception as e:
        print(f"❌ Send failed: {e}")
