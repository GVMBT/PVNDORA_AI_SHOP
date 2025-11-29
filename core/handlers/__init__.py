"""
Bot Handlers Package

Contains aiogram handlers for:
- messages: Text message handlers
- callbacks: Callback query handlers
- inline: Inline query handlers for viral sharing
"""

from core.handlers.messages import router as messages_router
from core.handlers.callbacks import router as callbacks_router
from core.handlers.inline import router as inline_router

__all__ = [
    "messages_router",
    "callbacks_router", 
    "inline_router"
]

