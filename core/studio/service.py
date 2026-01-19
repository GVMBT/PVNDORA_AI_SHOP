"""Studio Service - Business logic for AI generation.

Handles:
- Session management
- Generation lifecycle
- Balance operations
- Price calculation
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.logging import get_logger
from core.studio.adapters.base import AdapterError, GenerationType
from core.studio.dispatcher import calculate_price, generate

logger = get_logger(__name__)


class StudioService:
    """Service for managing Studio operations."""

    def __init__(self, db: Any) -> None:
        self.db = db

    # =========================================================================
    # Sessions
    # =========================================================================

    async def get_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Get user's studio sessions.

        Args:
            user_id: User database ID
            include_archived: Include archived sessions

        Returns:
            List of session dicts
        """
        query = (
            self.db.client.table("studio_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
        )

        if not include_archived:
            query = query.eq("is_archived", False)

        result = await query.execute()
        return result.data or []

    async def get_or_create_default_session(self, user_id: str) -> dict[str, Any]:
        """Get user's default session or create one.

        Args:
            user_id: User database ID

        Returns:
            Session dict
        """
        # Try to get existing default session
        result = (
            await self.db.client.table("studio_sessions")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_default", True)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Try to get any non-archived session
        result = (
            await self.db.client.table("studio_sessions")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_archived", False)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

        # Create new default session
        return await self.create_session(user_id, "Мой первый проект", is_default=True)

    async def create_session(
        self,
        user_id: str,
        name: str = "Новый проект",
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Create a new studio session.

        Args:
            user_id: User database ID
            name: Session name
            is_default: Mark as default session

        Returns:
            Created session dict
        """
        result = (
            await self.db.client.table("studio_sessions")
            .insert({
                "user_id": user_id,
                "name": name,
                "is_default": is_default,
            })
            .execute()
        )

        if not result.data:
            raise ValueError("Failed to create session")

        logger.info(f"Created studio session {result.data[0]['id']} for user {user_id}")
        return result.data[0]

    async def update_session(
        self,
        session_id: str,
        user_id: str,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update a studio session.

        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            **updates: Fields to update (name, is_archived, etc.)

        Returns:
            Updated session dict
        """
        allowed_fields = {"name", "is_archived"}
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        update_data["updated_at"] = datetime.now(UTC).isoformat()

        result = (
            await self.db.client.table("studio_sessions")
            .update(update_data)
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise ValueError("Session not found or not authorized")

        return result.data[0]

    async def delete_session(
        self,
        session_id: str,
        user_id: str,
        hard_delete: bool = False,
    ) -> bool:
        """Delete or archive a session.

        Args:
            session_id: Session ID
            user_id: User ID (for authorization)
            hard_delete: If True, delete permanently with all generations

        Returns:
            True if successful
        """
        # Check if session is default
        session_result = (
            await self.db.client.table("studio_sessions")
            .select("is_default")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not session_result.data:
            raise ValueError("Session not found")

        if session_result.data.get("is_default"):
            raise ValueError("Cannot delete default session")

        if hard_delete:
            # Delete all generations first (files are cleaned up by cron)
            await (
                self.db.client.table("studio_generations")
                .delete()
                .eq("session_id", session_id)
                .execute()
            )

            # Delete session
            await (
                self.db.client.table("studio_sessions")
                .delete()
                .eq("id", session_id)
                .eq("user_id", user_id)
                .execute()
            )
        else:
            # Soft delete (archive)
            await self.update_session(session_id, user_id, is_archived=True)

        return True

    # =========================================================================
    # Generations
    # =========================================================================

    async def get_generations(
        self,
        user_id: str,
        session_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get user's generations.

        Args:
            user_id: User database ID
            session_id: Optional filter by session
            limit: Max results
            offset: Pagination offset

        Returns:
            List of generation dicts
        """
        query = (
            self.db.client.table("studio_generations")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        if session_id:
            query = query.eq("session_id", session_id)

        result = await query.execute()
        return result.data or []

    async def get_generation(
        self,
        generation_id: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Get a single generation.

        Args:
            generation_id: Generation ID
            user_id: User ID (for authorization)

        Returns:
            Generation dict or None
        """
        result = (
            await self.db.client.table("studio_generations")
            .select("*")
            .eq("id", generation_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        return result.data

    async def start_generation(
        self,
        user_id: str,
        model_id: str,
        prompt: str,
        config: dict[str, Any],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Start a new AI generation.

        This method:
        1. Validates user balance
        2. Calculates price
        3. Deducts balance
        4. Creates generation record
        5. Calls AI provider

        Args:
            user_id: User database ID
            model_id: AI model to use
            prompt: Generation prompt
            config: Model-specific config
            session_id: Session to add generation to

        Returns:
            Generation dict with status

        Raises:
            ValueError: If insufficient balance or invalid params
            AdapterError: If AI provider fails
        """
        # Get or create session
        if not session_id:
            session = await self.get_or_create_default_session(user_id)
            session_id = session["id"]

        # Calculate price
        price = await calculate_price(model_id, config, self.db)

        # Check balance
        user_result = (
            await self.db.client.table("users")
            .select("balance")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not user_result.data:
            raise ValueError("User not found")

        balance = float(user_result.data.get("balance", 0))
        if balance < price:
            raise ValueError(f"Insufficient balance: {balance} < {price}")

        # Determine generation type from model
        model_result = (
            await self.db.client.table("studio_model_prices")
            .select("type")
            .eq("id", model_id)
            .single()
            .execute()
        )

        gen_type = model_result.data.get("type", "video") if model_result.data else "video"

        # Create generation record with 'queued' status
        generation_id = str(uuid4())
        generation_data = {
            "id": generation_id,
            "user_id": user_id,
            "session_id": session_id,
            "type": gen_type,
            "model": model_id,
            "prompt": prompt,
            "config": config,
            "status": "queued",
            "progress": 0,
            "cost_amount": price,
        }

        gen_result = (
            await self.db.client.table("studio_generations")
            .insert(generation_data)
            .execute()
        )

        if not gen_result.data:
            raise ValueError("Failed to create generation record")

        # Deduct balance
        await self.db.client.rpc(
            "add_to_user_balance",
            {"p_user_id": user_id, "p_amount": -price},
        ).execute()

        # Create balance transaction
        tx_result = (
            await self.db.client.table("balance_transactions")
            .insert({
                "user_id": user_id,
                "type": "studio_generation",
                "amount": -price,
                "currency": "RUB",
                "status": "completed",
                "description": f"Studio: {model_id} generation",
                "metadata": {
                    "generation_id": generation_id,
                    "model": model_id,
                },
            })
            .execute()
        )

        # Update generation with transaction ID
        if tx_result.data:
            await (
                self.db.client.table("studio_generations")
                .update({"balance_transaction_id": tx_result.data[0]["id"]})
                .eq("id", generation_id)
                .execute()
            )

        # Start AI generation (this will be async via QStash in production)
        try:
            from core.studio.adapters.base import GenerationRequest

            request = GenerationRequest(
                prompt=prompt,
                type=GenerationType(gen_type),
                aspect_ratio=config.get("aspect_ratio", "16:9"),
                duration_seconds=config.get("duration_seconds"),
                resolution=config.get("resolution"),
                custom_params=config.get("custom_params", {}),
                user_id=user_id,
                generation_id=generation_id,
            )

            result = await generate(model_id, request)

            # Update generation with job ID
            await (
                self.db.client.table("studio_generations")
                .update({
                    "status": result.status.value,
                    "external_job_id": result.job_id,
                    "has_audio": result.has_audio,
                })
                .eq("id", generation_id)
                .execute()
            )

            logger.info(f"Generation {generation_id} started: job_id={result.job_id}")

            # Schedule worker to poll status via QStash
            await self._schedule_generation_worker(
                generation_id=generation_id,
                model_id=model_id,
                external_job_id=result.job_id,
                user_id=user_id,
            )

        except AdapterError as e:
            # Generation failed to start - refund
            logger.exception(f"Generation {generation_id} failed to start")
            await self._refund_generation(generation_id, user_id, price, str(e))
            raise

        return gen_result.data[0]

    async def _schedule_generation_worker(
        self,
        generation_id: str,
        model_id: str,
        external_job_id: str,
        user_id: str,
    ) -> None:
        """Schedule worker to poll generation status via QStash."""
        import os

        qstash_token = os.environ.get("QSTASH_TOKEN", "")
        base_url = os.environ.get("BASE_URL", "")

        if not qstash_token or not base_url:
            logger.warning("QStash not configured, generation will not be polled")
            return

        try:
            from upstash_qstash import Client

            client = Client(qstash_token)

            await client.publish_json(
                url=f"{base_url}/api/workers/process_studio_generation",
                body={
                    "generation_id": generation_id,
                    "model_id": model_id,
                    "external_job_id": external_job_id,
                    "user_id": user_id,
                    "attempt": 1,
                },
                delay="5s",  # Wait 5 seconds before first poll
            )

            logger.info(f"Scheduled worker for generation {generation_id}")

        except Exception:
            logger.exception("Failed to schedule generation worker")
            # Don't fail the generation - it will just not be polled

    async def _refund_generation(
        self,
        generation_id: str,
        user_id: str,
        amount: int,
        error_message: str,
    ) -> None:
        """Refund a failed generation."""
        # Update generation status
        await (
            self.db.client.table("studio_generations")
            .update({
                "status": "failed",
                "error_message": error_message,
            })
            .eq("id", generation_id)
            .execute()
        )

        # Refund balance
        await self.db.client.rpc(
            "add_to_user_balance",
            {"p_user_id": user_id, "p_amount": amount},
        ).execute()

        # Create refund transaction
        await (
            self.db.client.table("balance_transactions")
            .insert({
                "user_id": user_id,
                "type": "studio_refund",
                "amount": amount,
                "currency": "RUB",
                "status": "completed",
                "description": "Studio: Refund for failed generation",
                "metadata": {
                    "generation_id": generation_id,
                    "reason": error_message,
                },
            })
            .execute()
        )

        logger.info(f"Refunded {amount}₽ for generation {generation_id}")

    async def update_generation_status(
        self,
        generation_id: str,
        status: str,
        progress: int | None = None,
        result_url: str | None = None,
        thumbnail_url: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update generation status (called by worker or webhook).

        Args:
            generation_id: Generation ID
            status: New status
            progress: Progress percentage (0-100)
            result_url: URL of generated file
            thumbnail_url: URL of thumbnail
            error_message: Error message if failed
        """
        update_data: dict[str, Any] = {"status": status}

        if progress is not None:
            update_data["progress"] = progress
        if result_url:
            update_data["result_url"] = result_url
        if thumbnail_url:
            update_data["thumbnail_url"] = thumbnail_url
        if error_message:
            update_data["error_message"] = error_message

        await (
            self.db.client.table("studio_generations")
            .update(update_data)
            .eq("id", generation_id)
            .execute()
        )

        # If failed, trigger refund
        if status == "failed":
            gen = await self.db.client.table("studio_generations") \
                .select("user_id, cost_amount") \
                .eq("id", generation_id) \
                .single() \
                .execute()

            if gen.data:
                await self._refund_generation(
                    generation_id,
                    gen.data["user_id"],
                    int(gen.data["cost_amount"]),
                    error_message or "Generation failed",
                )

    # =========================================================================
    # Models
    # =========================================================================

    async def get_models(self) -> list[dict[str, Any]]:
        """Get available models with pricing.

        Returns:
            List of model dicts with capabilities and prices
        """
        # Get models from database
        result = (
            await self.db.client.table("studio_model_prices")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )

        return result.data or []

    async def get_model_capabilities(self, model_id: str) -> dict[str, Any] | None:
        """Get capabilities for a specific model.

        Args:
            model_id: Model ID

        Returns:
            Capabilities dict or None if not found
        """
        result = (
            await self.db.client.table("studio_model_prices")
            .select("capabilities, supported_resolutions, max_duration_seconds")
            .eq("id", model_id)
            .eq("is_active", True)
            .single()
            .execute()
        )

        if not result.data:
            return None

        data = result.data
        capabilities = data.get("capabilities") or {}

        # Merge DB data with stored capabilities
        return {
            "resolutions": data.get("supported_resolutions") or ["720p"],
            "max_duration_seconds": data.get("max_duration_seconds"),
            **capabilities,
        }


def get_studio_service(db: Any | None = None) -> StudioService:
    """Get StudioService instance.

    Args:
        db: Database instance (optional, will get if not provided)

    Returns:
        StudioService instance
    """
    if db is None:
        from core.services.database import get_database
        db = get_database()

    return StudioService(db)
