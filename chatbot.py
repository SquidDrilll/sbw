import os, asyncio, random, groq, aiohttp
from database import MessageStore

client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
store = MessageStore()

async def get_ai_response(history, author_name):
    # IDENTITY LOCK: We explicitly tell the AI who the owner is and who it's talking to.
    persona = f"""
    you are 'hero 🗿', the legendary personality. 
    
    CURRENT CONTEXT:
    - you are replying to: {author_name}
    - your owner is: rowtten (also known as SquidDrill). 
    - if author is rowtten or SquidDrill, be loyal and cool.
    - everyone else is just a person you judge.
    
    RULES:
    - do not mix up people. check the name tag at the start of each history line.
    - talk like everyoneelse ,use the data you have to learn and become like them.
    - be chill, not a bot. keep it under short and concise.
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": persona}] + history,
            temperature=0.7 # Lowered temperature slightly to stop it from "hallucinating" names
        )
        return response.choices[0].message.content
    except Exception:
        # (Keep your OpenRouter fallback logic here)
        return "my bad, brain is lagging"

async def handle_chat(message, content):
    cid, author = str(message.channel.id), str(message.author.name)
    
    # Check for self-bot loop
    if message.author.id == message.channel.me.id:
        return

    store.add(cid, author, content, "user")
    
    # We increase the limit slightly so it has more "lore" to verify identities
    history = store.get_history(cid, limit=30) 
    
    response = await get_ai_response(history, author)
    
    # Human-like delay
    await asyncio.sleep((len(response) * 0.05) + 0.8)
    
    # CLEANUP: This stops the "hero: hero:" double-prefixing you saw in your logs
    clean_text = response.replace("**hero 🗿 :**", "").strip().lower().lstrip("!?. ")
    final_output = f"**hero 🗿 :** {clean_text}"
    
    try:
        await message.reply(final_output, mention_author=False)
        store.add(cid, "AI", final_output, "assistant")
    except Exception as e:
        print(f"❌ error: {e}")
