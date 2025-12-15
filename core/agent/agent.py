"""
LangGraph Shop Agent

ReAct agent powered by Gemini 2.5 Flash with tools for:
- Product catalog and search
- Shopping cart management
- Wishlist operations
- Support and refunds
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
    LangGraph-based shop agent.
    
    Features:
    - ReAct pattern for reasoning + acting
    - Gemini 2.5 Flash as LLM
    - Async tools for shop operations
    - Memory for conversation history
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
            temperature: LLM temperature
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
        Send a message to the agent.
        
        Args:
            message: User message
            user_id: User database ID
            language: User's language code
            thread_id: Conversation thread ID (for memory)
            telegram_id: User's Telegram ID (for cart operations)
            
        Returns:
            AgentResponse with content and metadata
        """
        # Load product catalog for context
        try:
            products = await self.db.get_products(status="active")
            product_catalog = format_product_catalog(products)
        except Exception as e:
            logger.warning(f"Failed to load catalog: {e}")
            product_catalog = ""
        
        # Build system prompt with user context
        system_prompt = get_system_prompt(language, product_catalog)
        
        # Add user context for tools
        context = f"""

Current context:
- user_id: {user_id}
- telegram_id: {telegram_id or 'unknown'}
- language: {language}

When using tools that require user_id, use: {user_id}
When using cart tools that require user_telegram_id, use: {telegram_id}
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
        
        # Invoke agent
        try:
            result = await self.agent.ainvoke({"messages": messages}, config)
            
            # Extract response from messages
            return self._parse_result(result)
            
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            # Fallback response
            error_messages = {
                "ru": "Произошла временная ошибка. Попробуйте ещё раз.",
                "en": "A temporary error occurred. Please try again.",
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
        last_ai_message = ai_messages[-1] if ai_messages else None
        
        content = ""
        tool_calls = []
        action = "none"
        product_id = None
        total_amount = None
        
        if last_ai_message:
            raw_content = last_ai_message.content or ""
            # Handle multimodal content (list) - extract text parts
            if isinstance(raw_content, list):
                content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in raw_content
                )
            else:
                content = str(raw_content)
            tool_calls = getattr(last_ai_message, "tool_calls", []) or []
            
            # Detect action from tool calls
            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                
                if tool_name == "add_to_cart":
                    action = "add_to_cart"
                    product_id = tool_args.get("product_id")
                elif tool_name == "create_purchase_intent":
                    action = "offer_payment"
                    product_id = tool_args.get("product_id")
                elif tool_name == "create_support_ticket":
                    action = "create_ticket"
                elif tool_name == "request_refund":
                    action = "refund_request"
        
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            action=action,
            product_id=product_id,
            total_amount=total_amount,
        )
    
    async def stream(
        self,
        message: str,
        user_id: str,
        language: str = "en",
        thread_id: Optional[str] = None,
        telegram_id: Optional[int] = None,
    ):
        """
        Stream agent response.
        
        Yields chunks as they're generated.
        """
        system_prompt = get_system_prompt(language)
        context = f"\n\nCurrent user_id: {user_id}, telegram_id: {telegram_id}"
        full_system = system_prompt + context
        
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": message},
        ]
        
        config = {}
        if thread_id and self.memory:
            config["configurable"] = {"thread_id": thread_id}
        
        async for chunk in self.agent.astream(
            {"messages": messages}, 
            config, 
            stream_mode="values"
        ):
            yield chunk


# Singleton instance
_shop_agent: Optional[ShopAgent] = None


def create_shop_agent(db, **kwargs) -> ShopAgent:
    """
    Factory function to create ShopAgent.
    
    Args:
        db: Database instance
        **kwargs: Additional arguments for ShopAgent
        
    Returns:
        Configured ShopAgent instance
    """
    return ShopAgent(db, **kwargs)


def get_shop_agent(db) -> ShopAgent:
    """
    Get or create singleton ShopAgent.
    
    Args:
        db: Database instance
        
    Returns:
        ShopAgent singleton
    """
    global _shop_agent
    if _shop_agent is None:
        _shop_agent = create_shop_agent(db)
    return _shop_agent
