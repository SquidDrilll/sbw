import re

def resolve_mentions(message):
    """
    Replaces <@id> mentions with @Name(ID) for the LLM to understand context.
    """
    content = message.content
    if not hasattr(message, 'mentions'):
        return content
        
    for user in message.mentions:
        # Use display_name (nickname) if available, else name
        name = user.display_name if hasattr(user, 'display_name') else user.name
        content = content.replace(f"<@{user.id}>", f"@{name}({user.id})")
        content = content.replace(f"<@!{user.id}>", f"@{name}({user.id})") # Handle nickname mentions
        
    return content

def restore_mentions(response):
    """
    Converts @Name(ID) back to <@ID> for Discord rendering.
    """
    if not response: 
        return ""
    pattern = r"@([^\(\)<>]+?)\s*\((\d+)\)"
    return re.sub(pattern, lambda m: f"<@{m.group(2)}>", response)
