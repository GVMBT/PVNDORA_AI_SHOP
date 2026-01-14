"""
LangGraph Shop Agent — Full-Featured & Fault-Tolerant

Complete agent covering all shop functionality with:
- Persistent chat history from database
- Auto-injected user context for all tools
- Redis-based state caching
- Full error recovery
- OpenRouter API (gemini-3-flash-preview via OpenAI-compatible endpoint)
"""

import os
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from core.agent.prompts import format_product_catalog, get_system_prompt
from core.agent.tools import get_all_tools, set_db, set_user_context
from core.logging import get_logger

logger = get_logger(__name__)

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Available models: google/gemini-3-flash-preview, google/gemini-2.5-flash, anthropic/claude-3-haiku, etc.
DEFAULT_MODEL = "google/gemini-3-flash-preview"


@dataclass
class AgentResponse:
    """Response from the agent."""

    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    action: str = "none"
    product_id: str | None = None
    total_amount: float | None = None
    payment_url: str | None = None


@dataclass
class UserContext:
    """User context for tool calls."""

    user_id: str
    telegram_id: int
    language: str
    currency: str
    exchange_rate: float = 1.0
    preferred_currency: str | None = None


class ShopAgent:
    """
    LangGraph-based shop agent with full functionality.

    Features:
    - ReAct pattern for reasoning + acting
    - OpenRouter API (Google Gemini 3 Flash Preview via OpenAI-compatible endpoint)
    - Auto-injected user context for all tools
    - Persistent chat history from database
    - Fault-tolerant with retries
    """

    def __init__(
        self,
        db,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
    ):
        """
        Initialize the agent.

        Args:
            db: Database instance
            model: OpenRouter model name (e.g., google/gemini-3-flash-preview)
            temperature: LLM temperature (0.7 = balanced)
        """
        self.db = db
        self.model_name = model
        self.temperature = temperature

        # Set DB for tools
        set_db(db)

        # Initialize LLM via OpenRouter
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            # Fallback to legacy GEMINI_API_KEY for backward compatibility
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                logger.warning("Using legacy GEMINI_API_KEY. Please migrate to OPENROUTER_API_KEY.")
            else:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,  # type: ignore[arg-type]  # langchain_openai accepts str, not just SecretStr
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": os.environ.get("WEBAPP_URL", "https://pvndora.com"),
                "X-Title": "PVNDORA Shop Agent",
            },
        )

        # Get tools
        self.tools = get_all_tools()

        # Create agent (no memory - we use DB history)
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )

        logger.info(f"ShopAgent initialized with {len(self.tools)} tools")

    async def _load_chat_history(self, user_id: str, limit: int = 10) -> list[dict[str, str]]:
        """Load recent chat history from database."""
        try:
            history = await self.db.get_chat_history(user_id, limit=limit)
            return history or []
        except Exception as e:
            logger.warning(f"Failed to load chat history: {e}")
            return []

    def _format_history_for_prompt(self, history: list[dict[str, str]]) -> str:
        """Format chat history for injection into system prompt."""
        if not history:
            return ""

        lines = ["\n## Recent Conversation History"]
        # Expanded to 12 messages (6 exchanges) for better context
        for msg in history[-12:]:
            role = msg.get("role", "user")
            content = msg.get("message", "")[:300]  # Allow longer context
            if role == "user":
                lines.append(f"User: {content}")
            else:
                lines.append(f"You: {content}")

        lines.append(
            "\nUse this context to maintain conversation flow and avoid redundant questions.\n"
        )
        return "\n".join(lines)

    async def _get_user_context(self, user_id: str, telegram_id: int, language: str) -> UserContext:
        """Build user context with currency info from DB."""
        from core.db import get_redis
        from core.services.currency import get_currency_service

        # After RUB-only migration: all currencies are RUB
        currency = "RUB"
        exchange_rate = 1.0
        preferred_currency = None  # Deprecated after RUB-only migration, kept for backward compatibility

        try:
            # Get user's language from DB for context
            result = (
                await self.db.client.table("users")
                .select("language_code")
                .eq("id", user_id)
                .single()
                .execute()
            )

            db_language = language
            if result.data:
                db_language = result.data.get("language_code") or language

            # Use CurrencyService which always returns RUB after migration
            redis = get_redis()
            currency_service = get_currency_service(redis)
            currency = currency_service.get_user_currency(db_language, None)

            # After RUB-only migration: exchange_rate is always 1.0
            exchange_rate = await currency_service.get_exchange_rate(currency)

            logger.info(
                f"User context: user_id={user_id}, currency={currency} (RUB-only), rate={exchange_rate}"
            )

        except Exception as e:
            logger.warning(f"Failed to get user context: {e}")
            # Fallback: After RUB-only migration, always RUB
            currency = "RUB"
            exchange_rate = 1.0

        return UserContext(
            user_id=user_id,
            telegram_id=telegram_id,
            language=language,
            currency=currency,
            exchange_rate=exchange_rate,
            preferred_currency=preferred_currency,
        )

    async def chat(
        self,
        message: str,
        user_id: str,
        language: str = "en",
        telegram_id: int | None = None,
    ) -> AgentResponse:
        """
        Send message to agent.

        Args:
            message: User message
            user_id: User database ID
            language: User's language code
            telegram_id: User's Telegram ID (for cart/notifications)

        Returns:
            AgentResponse with content and metadata
        """
        # Build user context with currency info
        user_ctx = await self._get_user_context(user_id, telegram_id or 0, language)

        # Set global user context for tools (auto-injection)
        set_user_context(
            user_ctx.user_id, user_ctx.telegram_id, user_ctx.language, user_ctx.currency
        )

        # Load product catalog with proper currency conversion
        product_catalog = ""
        try:
            products = await self.db.get_products(status="active")
            product_catalog = await format_product_catalog(products, language)
        except Exception as e:
            logger.warning(f"Failed to load catalog: {e}")

        # Load chat history for context (expanded to 20 messages)
        history = await self._load_chat_history(user_id, limit=20)
        history_context = self._format_history_for_prompt(history)

        # Build system prompt with user context
        system_prompt = get_system_prompt(
            language=language,
            product_catalog=product_catalog,
            user_id=user_id,
            telegram_id=telegram_id or 0,
            currency=user_ctx.currency,
        )

        # Add history context
        full_system = system_prompt + history_context

        # Build messages with history
        messages = [{"role": "system", "content": full_system}]

        # Add recent history as conversation turns (expanded to 12 messages)
        for msg in history[-12:]:
            role = msg.get("role", "user")
            content = msg.get("message", "")
            if role == "user":
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "assistant", "content": content})

        # Add current message
        messages.append({"role": "user", "content": message})

        # Invoke with retry
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await self.agent.ainvoke({"messages": messages})
                return self._parse_result(result)
            except Exception as e:
                last_error = e
                logger.warning(f"Agent attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    continue

        # All retries failed
        logger.error(f"Agent failed after {max_retries + 1} attempts: {last_error}")

        error_messages = {
            "ru": "Произошла ошибка. Попробуй переформулировать вопрос.",
            "en": "An error occurred. Please try rephrasing your question.",
        }
        return AgentResponse(
            content=error_messages.get(language, error_messages["en"]),
            action="error",
        )

    def _extract_content_from_ai_message(self, last_ai) -> str:
        """Extract content from AI message (reduces cognitive complexity)."""
        raw_content = last_ai.content or ""
        if isinstance(raw_content, list):
            parts = []
            for part in raw_content:
                if isinstance(part, dict):
                    parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    parts.append(part)
            return " ".join(parts).strip()
        return str(raw_content).strip()

    def _detect_action_from_tool_calls(self, tool_calls: list) -> tuple[str, str | None]:
        """Detect action and extract product_id from tool calls (reduces cognitive complexity)."""
        action = "none"
        product_id = None

        for tc in tool_calls:
            tool_name = tc.get("name", "")
            tool_args = tc.get("args", {})

            if tool_name == "add_to_cart":
                action = "add_to_cart"
                product_id = tool_args.get("product_id")
            elif tool_name in ("get_order_credentials", "resend_order_credentials"):
                action = "show_credentials"
            elif tool_name == "create_support_ticket":
                action = "create_ticket"
            elif tool_name == "request_refund":
                action = "refund_request"
            elif tool_name == "pay_from_balance":
                action = "offer_payment"

        return action, product_id

    def _parse_result(self, result: dict[str, Any]) -> AgentResponse:
        """Parse agent result into AgentResponse."""
        messages = result.get("messages", [])

        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        last_ai = ai_messages[-1] if ai_messages else None

        content = ""
        tool_calls: list[dict[str, Any]] = []
        action = "none"
        product_id = None
        total_amount = None
        payment_url = None

        if last_ai:
            content = self._extract_content_from_ai_message(last_ai)
            tool_calls = getattr(last_ai, "tool_calls", []) or []
            action, product_id = self._detect_action_from_tool_calls(tool_calls)

        # Ensure we have some content
        if not content:
            content = "Готово!"

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            action=action,
            product_id=product_id,
            total_amount=total_amount,
            payment_url=payment_url,
        )


# =============================================================================
# SINGLETON
# =============================================================================

_agent: ShopAgent | None = None


def get_shop_agent(db=None) -> ShopAgent:
    """
    Get or create agent singleton.

    Args:
        db: Database instance (required on first call)

    Returns:
        ShopAgent instance
    """
    global _agent

    if _agent is None:
        if db is None:
            from core.services.database import get_database

            db = get_database()
        _agent = ShopAgent(db)

    return _agent


def reset_agent():
    """Reset agent singleton (for testing)."""
    global _agent
    _agent = None
