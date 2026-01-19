"""Studio Router - API endpoints for AI generation studio.

Endpoints:
- Sessions CRUD
- Generation management
- Model info
"""

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import verify_telegram_auth
from core.logging import get_logger

if TYPE_CHECKING:
    from core.utils.validators import TelegramUser

logger = get_logger(__name__)

studio_router = APIRouter(prefix="/studio", tags=["studio"])


# ============================================================
# Pydantic Models
# ============================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    name: str = Field(default="Новый проект", max_length=100)


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""
    name: str | None = Field(default=None, max_length=100)
    is_archived: bool | None = None


class GenerateRequest(BaseModel):
    """Request to start a generation."""
    model_id: str = Field(..., description="Model ID (e.g., 'veo-3.1')")
    prompt: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, description="Session to add generation to")
    config: dict[str, Any] = Field(default_factory=dict, description="Model-specific config")


class MoveGenerationRequest(BaseModel):
    """Request to move generation between sessions."""
    target_session_id: str
    copy: bool = False


# ============================================================
# Sessions Endpoints
# ============================================================

@studio_router.get("/sessions")
async def get_sessions(
    include_archived: bool = False,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Get user's studio sessions."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    sessions = await service.get_sessions(str(db_user.id), include_archived)
    
    # Find default session
    default_session_id = None
    for s in sessions:
        if s.get("is_default"):
            default_session_id = s["id"]
            break
    
    return {
        "sessions": sessions,
        "default_session_id": default_session_id,
    }


@studio_router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Create a new studio session."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    session = await service.create_session(str(db_user.id), request.name)
    
    return {"success": True, "session": session}


@studio_router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Update a studio session."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.is_archived is not None:
        updates["is_archived"] = request.is_archived
    
    try:
        session = await service.update_session(session_id, str(db_user.id), **updates)
        return {"success": True, "session": session}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@studio_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    hard_delete: bool = False,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Delete or archive a studio session."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    
    try:
        await service.delete_session(session_id, str(db_user.id), hard_delete)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Generations Endpoints
# ============================================================

@studio_router.get("/generations")
async def get_generations(
    session_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Get user's generations."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    generations = await service.get_generations(
        str(db_user.id),
        session_id=session_id,
        limit=min(limit, 100),
        offset=offset,
    )
    
    return {"generations": generations}


@studio_router.get("/generations/{generation_id}")
async def get_generation(
    generation_id: str,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Get a single generation."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    generation = await service.get_generation(generation_id, str(db_user.id))
    
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return {"generation": generation}


@studio_router.post("/generate")
async def start_generation(
    request: GenerateRequest,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Start a new AI generation.
    
    This endpoint:
    1. Validates balance
    2. Deducts cost
    3. Creates generation record
    4. Starts AI provider job
    
    Returns generation ID for tracking via SSE.
    """
    from core.services.database import get_database
    from core.studio.adapters.base import AdapterError
    from core.studio.service import get_studio_service
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service = get_studio_service(db)
    
    try:
        generation = await service.start_generation(
            user_id=str(db_user.id),
            model_id=request.model_id,
            prompt=request.prompt,
            config=request.config,
            session_id=request.session_id,
        )
        
        return {
            "success": True,
            "generation_id": generation["id"],
            "status": generation["status"],
            "cost": generation["cost_amount"],
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AdapterError as e:
        logger.error(f"Adapter error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503 if e.retryable else 500,
            detail=str(e),
        )


@studio_router.post("/generations/{generation_id}/move")
async def move_generation(
    generation_id: str,
    request: MoveGenerationRequest,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Move or copy generation to another session."""
    from core.services.database import get_database
    
    db = get_database()
    db_user = await db.get_user_by_telegram_id(user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = str(db_user.id)
    
    # Verify generation belongs to user
    gen_result = (
        await db.client.table("studio_generations")
        .select("id, session_id, cost_amount")
        .eq("id", generation_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    
    if not gen_result.data:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Verify target session belongs to user
    session_result = (
        await db.client.table("studio_sessions")
        .select("id")
        .eq("id", request.target_session_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Target session not found")
    
    if request.copy:
        # Copy generation
        # TODO: Implement file copying in storage
        raise HTTPException(status_code=501, detail="Copy not implemented yet")
    else:
        # Move generation
        old_session_id = gen_result.data["session_id"]
        cost = gen_result.data["cost_amount"]
        
        # Update generation
        await (
            db.client.table("studio_generations")
            .update({"session_id": request.target_session_id})
            .eq("id", generation_id)
            .execute()
        )
        
        # Update old session stats
        await (
            db.client.table("studio_sessions")
            .update({
                "total_generations": db.client.literal("total_generations - 1"),
                "total_spent": db.client.literal(f"total_spent - {cost}"),
            })
            .eq("id", old_session_id)
            .execute()
        )
        
        # Update new session stats
        await (
            db.client.table("studio_sessions")
            .update({
                "total_generations": db.client.literal("total_generations + 1"),
                "total_spent": db.client.literal(f"total_spent + {cost}"),
            })
            .eq("id", request.target_session_id)
            .execute()
        )
    
    return {
        "success": True,
        "generation_id": generation_id,
        "new_session_id": request.target_session_id,
    }


# ============================================================
# Models Endpoints
# ============================================================

@studio_router.get("/models")
async def get_models(
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Get available AI models with pricing."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    service = get_studio_service(db)
    models = await service.get_models()
    
    return {"models": models}


@studio_router.get("/models/{model_id}/capabilities")
async def get_model_capabilities(
    model_id: str,
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Get capabilities for a specific model (for Dynamic UI)."""
    from core.services.database import get_database
    from core.studio.service import get_studio_service
    
    db = get_database()
    service = get_studio_service(db)
    capabilities = await service.get_model_capabilities(model_id)
    
    if not capabilities:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {"capabilities": capabilities}


@studio_router.post("/models/{model_id}/calculate-price")
async def calculate_model_price(
    model_id: str,
    config: dict[str, Any],
    user: "TelegramUser" = Depends(verify_telegram_auth),
) -> dict[str, Any]:
    """Calculate price for generation with given config."""
    from core.services.database import get_database
    from core.studio.dispatcher import calculate_price
    
    db = get_database()
    
    try:
        price = await calculate_price(model_id, config, db)
        return {"price": price, "currency": "RUB"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
