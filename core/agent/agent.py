"""
LangGraph Shop Agent — Full-Featured & Fault-Tolerant

Complete agent covering all shop functionality:
- Catalog, Cart, Orders, Credentials
- User Profile, Referrals
- Wishlist, Waitlist
- Support, FAQ, Refunds
"""
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from core.agent.tools import get_all_tools, set_db
from core.agent.prompts import get_system_prompt, format_product_catalog
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AgentResponse:
    """Response from the agent."""
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    action: str = "none"
    product_id: Optional[str] = None
    total_amount: Optional[float] = None


class ShopAgent:
    """
    LangGraph-based shop agent with full functionality.
    
    Features:
    - ReAct pattern for reasoning + acting
    - Gemini 2.5 Flash as LLM
    - 20 tools covering all shop features
    - Fault-tolerant with retries
    - Per-user conversation memory
    """
    
    def __init__(
        self,
        db,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        use_memory: bool = True,
    ):
        """
        Initialize the agent.
        
        Args:
            db: Database instance
            model: Gemini model name
            temperature: LLM temperature (0.7 = balanced)
            use_memory: Whether to use conversation memory
        """
        self.db = db
        self.model_name = model
        self.temperature = temperature
        
        # Set DB for tools
        set_db(db)
        
        # Initialize LLM
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,  # Better Gemini compatibility
        )
        
        # Get tools
        self.tools = get_all_tools()
        
        # Memory (optional)
        self.memory = MemorySaver() if use_memory else None
        
        # Create agent
        self.agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=self.memory,
        )
        
        logger.info(f"ShopAgent initialized with {len(self.tools)} tools")
    
    async def chat(
        self,
        message: str,
        user_id: str,
        language: str = "en",
        thread_id: Optional[str] = None,
        telegram_id: Optional[int] = None,
    ) -> AgentResponse:
        """
        Send message to agent.
        
        Args:
            message: User message
            user_id: User database ID
            language: User's language code
            thread_id: Conversation thread ID (for memory)
            telegram_id: User's Telegram ID (for cart/notifications)
            
        Returns:
            AgentResponse with content and metadata
        """
        # Load product catalog
        product_catalog = ""
        try:
            products = await self.db.get_products(status="active")
            product_catalog = format_product_catalog(products)
        except Exception as e:
            logger.warning(f"Failed to load catalog: {e}")
        
        # Build system prompt
        system_prompt = get_system_prompt(language, product_catalog)
        
        # Add user context
        context = f"""

## Current User Context
- user_id: {user_id}
- telegram_id: {telegram_id or 'unknown'}
- language: {language}

Use these values when calling tools:
- For user operations: user_id="{user_id}"
- For cart operations: user_telegram_id={telegram_id}
- For notifications: telegram_id={telegram_id}
"""
        full_system = system_prompt + context
        
        # Build messages
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": message},
        ]
        
        # Config for memory
        config = {}
        if thread_id and self.memory:
            config["configurable"] = {"thread_id": thread_id}
        
        # Invoke with retry
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.agent.ainvoke({"messages": messages}, config)
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
    
    def _parse_result(self, result: Dict[str, Any]) -> AgentResponse:
        """Parse agent result into AgentResponse."""
        messages = result.get("messages", [])
        
        # Find last AI message
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        last_ai = ai_messages[-1] if ai_messages else None
        
        content = ""
        tool_calls = []
        action = "none"
        product_id = None
        total_amount = None
        
        if last_ai:
            # Handle multimodal content (can be list)
            raw_content = last_ai.content or ""
            if isinstance(raw_content, list):
                # Extract text from list of content parts
                parts = []
                for part in raw_content:
                    if isinstance(part, dict):
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                content = " ".join(parts).strip()
            else:
                content = str(raw_content).strip()
            
            # Get tool calls
            tool_calls = getattr(last_ai, "tool_calls", []) or []
            
            # Detect action from tool calls
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
                elif tool_name == "get_user_cart":
                    # Check if cart has items
                    pass
        
        # Ensure we have some content
        if not content:
            content = "Готово!"
        
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            action=action,
            product_id=product_id,
            total_amount=total_amount,
        )


# =============================================================================
# SINGLETON
# =============================================================================

_agent: Optional[ShopAgent] = None


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
