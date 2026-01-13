"""
WebApp AI Chat Router

AI-powered chat endpoint using LangGraph ShopAgent (Gemini 2.5).
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.agent import get_shop_agent
from core.auth import verify_telegram_auth
from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["webapp-ai"])

# Lazy singleton
_shop_agent = None


def get_agent():
    """Get or create ShopAgent singleton."""
    global _shop_agent
    if _shop_agent is None:
        db = get_database()
        _shop_agent = get_shop_agent(db)
    return _shop_agent


# --- Request/Response Models ---


class ChatMessageRequest(BaseModel):
    """Chat message from user."""

    message: str = Field(..., min_length=1, max_length=2000, description="User message text")


class ChatMessageResponse(BaseModel):
    """AI chat response."""

    reply_text: str = Field(description="AI response text (HTML formatted)")
    action: str = Field(default="none", description="Action type if any")
    thought: str | None = Field(default=None, description="AI reasoning (debug)")
    ticket_id: str | None = Field(default=None, description="Created ticket ID if any")
    product_id: str | None = Field(default=None, description="Related product ID if any")
    total_amount: float | None = Field(default=None, description="Total amount for payment")


class ChatHistoryItem(BaseModel):
    """Single chat history item."""

    role: str = Field(description="Message role: user or assistant")
    content: str = Field(description="Message content")
    timestamp: str | None = Field(default=None, description="Message timestamp")


class ChatHistoryResponse(BaseModel):
    """Chat history response."""

    messages: list[ChatHistoryItem]
    count: int


# --- Endpoints ---


@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(request: ChatMessageRequest, user=Depends(verify_telegram_auth)):
    """
    Send message to AI consultant and get response.

    The AI can:
    - Answer questions about products
    - Add items to cart
    - Create support tickets
    - Process refund requests
    - Search FAQ
    """
    db = get_database()

    # Get user from database
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user language and normalize it
    from core.i18n import detect_language

    raw_language = getattr(db_user, "language_code", "en") or "en"
    language = detect_language(raw_language)

    try:
        # Save user message to history
        await db.chat_domain.save_message(db_user.id, "user", request.message)

        # Get AI response via LangGraph agent
        agent = get_agent()
        response = await agent.chat(
            message=request.message,
            user_id=db_user.id,
            language=language,
            telegram_id=user.id,
        )

        # Save AI response to history
        await db.chat_domain.save_message(db_user.id, "assistant", response.content)

        return ChatMessageResponse(
            reply_text=response.content,
            action=response.action,
            thought=None,  # LangGraph doesn't expose reasoning by default
            ticket_id=None,  # Can be extracted from tool calls if needed
            product_id=response.product_id,
            total_amount=response.total_amount,
        )

    except Exception as e:
        logger.error(f"AI chat failed: {e}", exc_info=True)

        # Return graceful error
        error_messages = {
            "ru": "Произошла временная ошибка. Попробуйте ещё раз.",
            "en": "A temporary error occurred. Please try again.",
        }
        error_text = error_messages.get(language, error_messages["en"])

        return ChatMessageResponse(
            reply_text=error_text,
            action="none",
            thought=f"Error: {e!s}",
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = Query(20, ge=1, le=100, description="Number of messages to return"),
    user=Depends(verify_telegram_auth),
):
    """Get user's chat history with AI."""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    history = await db.chat_domain.get_history(db_user.id, limit)

    messages = [
        ChatHistoryItem(
            role=msg.get("role", "user"),
            content=msg.get("content", msg.get("message", "")),
            timestamp=msg.get("timestamp"),
        )
        for msg in history
    ]

    return ChatHistoryResponse(messages=messages, count=len(messages))


@router.delete("/history")
async def clear_chat_history(user=Depends(verify_telegram_auth)):
    """Clear user's chat history (start fresh conversation)."""
    db = get_database()

    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Delete chat history for user
        await db.client.table("chat_history").delete().eq("user_id", db_user.id).execute()
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear history")
