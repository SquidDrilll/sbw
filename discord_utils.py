import re

def resolve_mentions(message):
    content = message.content
    for user in message.mentions:
        content = content.replace(f"<@{user.id}>", f"@{user.display_name}({user.id})")
    return content

def restore_mentions(response):
    pattern = r"@([^\(\)<>]+?)\s*\((\d+)\)"
    return re.sub(pattern, lambda m: f"<@{m.group(2)}>", response)
