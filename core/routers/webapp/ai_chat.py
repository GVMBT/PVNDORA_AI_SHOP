"""
WebApp AI Chat Router

AI-powered chat endpoint using AIConsultant (Gemini).
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.services.database import get_database
from src.ai.consultant import AIConsultant
from core.auth import verify_telegram_auth

router = APIRouter(prefix="/ai", tags=["webapp-ai"])

# Lazy singleton for AIConsultant
_ai_consultant: Optional[AIConsultant] = None


def get_ai_consultant() -> AIConsultant:
    """Get or create AIConsultant singleton."""
    global _ai_consultant
    if _ai_consultant is None:
        _ai_consultant = AIConsultant()
    return _ai_consultant


# --- Request/Response Models ---

class ChatMessageRequest(BaseModel):
    """Chat message from user."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message text")


class ChatMessageResponse(BaseModel):
    """AI chat response."""
    reply_text: str = Field(description="AI response text (HTML formatted)")
    action: str = Field(default="none", description="Action type if any")
    thought: Optional[str] = Field(default=None, description="AI reasoning (debug)")
    ticket_id: Optional[str] = Field(default=None, description="Created ticket ID if any")
    product_id: Optional[str] = Field(default=None, description="Related product ID if any")
    total_amount: Optional[float] = Field(default=None, description="Total amount for payment")


class ChatHistoryItem(BaseModel):
    """Single chat history item."""
    role: str = Field(description="Message role: user or assistant")
    content: str = Field(description="Message content")
    timestamp: Optional[str] = Field(default=None, description="Message timestamp")


class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    messages: list[ChatHistoryItem]
    count: int


# --- Endpoints ---

@router.post("/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    user=Depends(verify_telegram_auth)
):
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
    
    # Get user language
    language = getattr(db_user, 'language_code', 'en') or 'en'
    
    try:
        # Save user message to history
        await db.chat_domain.save_message(db_user.id, "user", request.message)
        
        # Get AI response
        ai = get_ai_consultant()
        response = await ai.get_response(
            user_id=db_user.id,
            user_message=request.message,
            language=language
        )
        
        # Save AI response to history
        await db.chat_domain.save_message(db_user.id, "assistant", response.reply_text)
        
        # Extract ticket_id if ticket was created (check thought for clues)
        ticket_id = None
        if response.action and response.action.value == "create_ticket":
            # Try to extract from thought or ticket_type
            ticket_id = getattr(response, 'ticket_type', None)
        
        return ChatMessageResponse(
            reply_text=response.reply_text,
            action=response.action.value if response.action else "none",
            thought=response.thought if response.thought else None,
            ticket_id=ticket_id,
            product_id=response.product_id,
            total_amount=response.total_amount,
        )
        
    except Exception as e:
        print(f"ERROR: AI chat failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return graceful error
        error_messages = {
            "ru": "Произошла временная ошибка. Попробуйте ещё раз.",
            "en": "A temporary error occurred. Please try again.",
        }
        error_text = error_messages.get(language, error_messages["en"])
        
        return ChatMessageResponse(
            reply_text=error_text,
            action="none",
            thought=f"Error: {str(e)}",
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    limit: int = Query(20, ge=1, le=100, description="Number of messages to return"),
    user=Depends(verify_telegram_auth)
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
    
    return ChatHistoryResponse(
        messages=messages,
        count=len(messages)
    )


@router.delete("/history")
async def clear_chat_history(user=Depends(verify_telegram_auth)):
    """Clear user's chat history (start fresh conversation)."""
    db = get_database()
    
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Delete chat history for user
        await asyncio.to_thread(
            lambda: db.client.table("chat_history").delete().eq("user_id", db_user.id).execute()
        )
        return {"success": True, "message": "Chat history cleared"}
    except Exception as e:
        print(f"ERROR: Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear history")

