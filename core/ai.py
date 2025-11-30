"""
AI Module - Gemini 2.5 Flash Integration

Provides:
- Structured Outputs with Pydantic schema enforcement
- Function Calling for real-time data access
- Context Caching for optimized costs
- Retry logic with tenacity
"""

import os
import json
from typing import Optional, List, Callable, Any
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from core.models import (
    AIResponse,
    ActionType,
    CheckAvailabilityResult,
    PromoCodeCheck,
    FAQItem
)


# Environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"


# Singleton client
_genai_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """Get Gemini client (singleton)."""
    global _genai_client
    
    if _genai_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY must be set")
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    
    return _genai_client


# ============================================================
# System Prompts
# ============================================================

SYSTEM_PROMPT_TEMPLATE = """You are PVNDORA, an AI sales consultant for premium AI subscriptions and digital services.

## Your Role
- Help users find the right AI subscription (ChatGPT Plus, Claude Pro, Midjourney, etc.)
- Understand user needs and recommend suitable products
- Answer questions about products, pricing, and features
- Guide users through the purchase process
- Handle support requests and warranty claims

## Communication Style
- Be friendly, helpful, and conversational
- Use emojis naturally but don't overdo it
- Adapt to the user's tone (formal/casual)
- Speak in {language}
- Be concise but thorough

## Important Rules
1. ALWAYS use function calls to check product availability before offering to sell
2. NEVER promise products without checking stock first
3. If a product is out of stock, offer alternatives or waitlist
4. For support requests, check warranty period before approving replacements
5. When user says "buy", "order", "want to purchase" - detect purchase intent
6. Always mention discounts when available

## Available Actions
- offer_payment: When user is ready to buy and product is available
- add_to_cart: Add product to cart
- update_cart: Modify cart contents
- show_catalog: Show available products
- add_to_waitlist: Add user to waitlist for out-of-stock items
- create_ticket: Create support ticket
- show_orders: Show user's order history
- compare_products: Compare multiple products

## Response Format
Always respond with a structured JSON containing:
- thought: Your internal reasoning (not shown to user)
- reply_text: The message to send to user
- action: The action to perform (or "none")
- Additional fields based on action type

{additional_context}
"""

CULTURAL_ADAPTATIONS = {
    "ru": {
        "language": "Russian (русский)",
        "style": "Friendly and informal, use 'ты' form unless user is formal",
        "emoji_level": "moderate"
    },
    "en": {
        "language": "English",
        "style": "Friendly and professional",
        "emoji_level": "moderate"
    },
    "uk": {
        "language": "Ukrainian (українська)",
        "style": "Friendly, can mix with Russian if user does",
        "emoji_level": "moderate"
    },
    "de": {
        "language": "German (Deutsch)",
        "style": "Professional but warm, use 'Sie' form by default",
        "emoji_level": "low"
    },
    "fr": {
        "language": "French (Français)",
        "style": "Elegant and polite, use 'vous' form",
        "emoji_level": "low"
    },
    "es": {
        "language": "Spanish (Español)",
        "style": "Warm and friendly, use 'tú' form",
        "emoji_level": "high"
    },
    "tr": {
        "language": "Turkish (Türkçe)",
        "style": "Respectful and helpful",
        "emoji_level": "moderate"
    },
    "ar": {
        "language": "Arabic (العربية)",
        "style": "Formal and respectful, include proper greetings",
        "emoji_level": "low"
    },
    "hi": {
        "language": "Hindi (हिन्दी)",
        "style": "Respectful and friendly, can use common English terms",
        "emoji_level": "moderate"
    }
}


def get_system_prompt(
    language_code: str = "en",
    products_context: str = "",
    user_context: str = ""
) -> str:
    """
    Generate localized system prompt with context.
    
    Args:
        language_code: User's language code
        products_context: Available products summary
        user_context: User's history/preferences
    
    Returns:
        Complete system prompt
    """
    culture = CULTURAL_ADAPTATIONS.get(
        language_code, 
        CULTURAL_ADAPTATIONS["en"]
    )
    
    additional = []
    
    if products_context:
        additional.append(f"## Available Products\n{products_context}")
    
    if user_context:
        additional.append(f"## User Context\n{user_context}")
    
    additional.append(f"## Cultural Notes\n- Style: {culture['style']}\n- Emoji usage: {culture['emoji_level']}")
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        language=culture["language"],
        additional_context="\n\n".join(additional)
    )


# ============================================================
# Function Calling Definitions
# ============================================================

def get_function_declarations() -> List[types.FunctionDeclaration]:
    """Get function declarations for Gemini."""
    return [
        types.FunctionDeclaration(
            name="check_product_availability",
            description="Check if a product is available in stock, get current price and discount",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(
                        type=types.Type.STRING,
                        description="Product UUID to check"
                    )
                },
                required=["product_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_user_cart",
            description="Get the current contents of user's shopping cart",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={}
            )
        ),
        types.FunctionDeclaration(
            name="add_to_cart",
            description="Add a product to user's cart",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(
                        type=types.Type.STRING,
                        description="Product UUID to add"
                    ),
                    "quantity": types.Schema(
                        type=types.Type.INTEGER,
                        description="Quantity to add (default 1)"
                    )
                },
                required=["product_id"]
            )
        ),
        types.FunctionDeclaration(
            name="update_cart",
            description="Update cart: change quantity, remove item, or clear cart",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "operation": types.Schema(
                        type=types.Type.STRING,
                        description="Operation: update_quantity, remove_item, or clear",
                        enum=["update_quantity", "remove_item", "clear"]
                    ),
                    "product_id": types.Schema(
                        type=types.Type.STRING,
                        description="Product UUID (for update/remove)"
                    ),
                    "quantity": types.Schema(
                        type=types.Type.INTEGER,
                        description="New quantity (for update_quantity)"
                    )
                },
                required=["operation"]
            )
        ),
        types.FunctionDeclaration(
            name="check_promo_code",
            description="Validate a promo code and get discount info",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "code": types.Schema(
                        type=types.Type.STRING,
                        description="Promo code to validate"
                    )
                },
                required=["code"]
            )
        ),
        types.FunctionDeclaration(
            name="get_faq_answer",
            description="Search FAQ for answer to user question",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "question": types.Schema(
                        type=types.Type.STRING,
                        description="User's question to search"
                    )
                },
                required=["question"]
            )
        ),
        types.FunctionDeclaration(
            name="get_user_orders",
            description="Get user's order history",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Maximum orders to return (default 10)"
                    )
                }
            )
        ),
        types.FunctionDeclaration(
            name="search_products",
            description="Search products by description or use case",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Search query describing what user needs"
                    ),
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Maximum results (default 5)"
                    )
                },
                required=["query"]
            )
        )
    ]


# ============================================================
# AI Consultation Engine
# ============================================================

class AIConsultant:
    """
    AI Consultation Engine powered by Gemini 2.5 Flash.
    
    Features:
    - Structured outputs with Pydantic schema
    - Function calling for real-time data
    - Retry logic for reliability
    - Context caching for cost optimization
    """
    
    def __init__(
        self,
        function_handlers: Optional[dict[str, Callable]] = None
    ):
        """
        Initialize AI Consultant.
        
        Args:
            function_handlers: Dict mapping function names to handler callables
        """
        self.client = get_genai_client()
        self.model_name = MODEL_NAME
        self.function_handlers = function_handlers or {}
        self._cached_content_id: Optional[str] = None
    
    def register_function(self, name: str, handler: Callable):
        """Register a function handler."""
        self.function_handlers[name] = handler
    
    async def _execute_function_call(
        self,
        function_call: types.FunctionCall
    ) -> Any:
        """Execute a function call and return result."""
        name = function_call.name
        args = dict(function_call.args) if function_call.args else {}
        
        handler = self.function_handlers.get(name)
        if not handler:
            return {"error": f"Unknown function: {name}"}
        
        try:
            # Call handler (async or sync)
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ValidationError, json.JSONDecodeError))
    )
    async def consult(
        self,
        user_message: str,
        user_telegram_id: int,
        language_code: str = "en",
        chat_history: Optional[List[dict]] = None,
        products_context: str = "",
        user_context: str = ""
    ) -> AIResponse:
        """
        Process user message and generate AI response.
        
        Args:
            user_message: User's message text
            user_telegram_id: User's Telegram ID (for function calls)
            language_code: User's language
            chat_history: Previous messages for context
            products_context: Available products summary
            user_context: User preferences/history
        
        Returns:
            Structured AIResponse with action
        """
        # Build system prompt
        system_prompt = get_system_prompt(
            language_code=language_code,
            products_context=products_context,
            user_context=user_context
        )
        
        # Build contents
        contents = []
        
        # Add chat history
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg.get("message", ""))]
                ))
        
        # Add current message
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        ))
        
        # Configure generation with Pydantic schema as dict
        generation_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=2048,
            response_mime_type="application/json",
            response_schema=AIResponse.model_json_schema(),
            system_instruction=system_prompt
        )
        
        # Get tools
        tools = [types.Tool(function_declarations=get_function_declarations())]
        
        # Generate response
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generation_config,
            tools=tools
        )
        
        # Handle function calls if present
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    # Execute function
                    fc = part.function_call
                    result = await self._execute_function_call(fc)
                    
                    # Add function response and continue
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part(function_call=fc)]
                    ))
                    contents.append(types.Content(
                        role="user",
                        parts=[types.Part(function_response=types.FunctionResponse(
                            name=fc.name,
                            response=result
                        ))]
                    ))
                    
                    # Generate final response with function result
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=generation_config
                    )
        
        # Parse response
        if response.text:
            return AIResponse.model_validate_json(response.text)
        
        # Fallback
        return AIResponse(
            thought="Failed to generate response",
            reply_text="I'm sorry, I couldn't process your request. Please try again.",
            action=ActionType.NONE
        )
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
        
        Returns:
            768-dimensional embedding vector
        """
        response = await self.client.aio.models.embed_content(
            model="text-embedding-004",
            content=text
        )
        return response.embedding


# ============================================================
# Singleton Instance
# ============================================================

_ai_consultant: Optional[AIConsultant] = None


def get_ai_consultant() -> AIConsultant:
    """Get AI Consultant singleton."""
    global _ai_consultant
    if _ai_consultant is None:
        _ai_consultant = AIConsultant()
    return _ai_consultant


def register_ai_functions(handlers: dict[str, Callable]):
    """Register function handlers with AI consultant."""
    consultant = get_ai_consultant()
    for name, handler in handlers.items():
        consultant.register_function(name, handler)

