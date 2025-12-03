"""Bot handlers package - exports combined router with all handlers."""
from aiogram import Router

from src.bot.handlers.commands import router as commands_router
from src.bot.handlers.callbacks import router as callbacks_router
from src.bot.handlers.inline import router as inline_router
from src.bot.handlers.messages import router as messages_router

router = Router()

# Include in correct order: commands/callbacks first, messages last (catch-all)
router.include_router(commands_router)
router.include_router(callbacks_router)
router.include_router(inline_router)
router.include_router(messages_router)

__all__ = ["router"]

