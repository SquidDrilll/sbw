import contextvars
from typing import Optional

# Context variable to store the current Discord channel object
# This allows tools (like BioTools) to access the Discord client 
# without passing it through every function call.
_current_channel: contextvars.ContextVar[Optional[object]] = contextvars.ContextVar("current_channel", default=None)

def set_current_channel(channel: object):
    """Sets the current Discord channel object in the execution context."""
    _current_channel.set(channel)

def get_current_channel() -> Optional[object]:
    """Gets the current Discord channel object from the execution context."""
    return _current_channel.get()
