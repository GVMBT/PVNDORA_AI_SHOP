"""AI Consultant - Gemini Integration"""
import os
import base64
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from google import genai
from google.genai import types

from src.services.database import get_database
from src.ai.prompts import get_system_prompt, format_product_catalog
from src.ai.tools import TOOLS, execute_tool


@dataclass
class AIResponse:
    """AI consultant response"""
    text: str
    product_id: Optional[str] = None
    show_shop: bool = False
    transcription: Optional[str] = None  # For voice messages


class AIConsultant:
    """AI Sales Consultant powered by Gemini 2.5 Flash"""
    
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
    
    async def get_response(
        self,
        user_id: str,
        user_message: str,
        language: str = "en"
    ) -> AIResponse:
        """
        Get AI response for a text message.
        
        Args:
            user_id: User's database ID
            user_message: User's message text
            language: User's language code
            
        Returns:
            AIResponse with text and optional actions
        """
        db = get_database()
        
        # Get products for context
        products = await db.get_products(status="active")
        product_catalog = format_product_catalog(products)
        
        # Build conversation history
        history = await db.get_chat_history(user_id, limit=10)
        
        # Build messages
        messages = []
        
        # Add conversation history
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            messages.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        
        # Add current message
        messages.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        ))
        
        # Get system prompt
        system_prompt = get_system_prompt(language, product_catalog)
        
        # Convert tools to Gemini format
        gemini_tools = self._convert_tools_to_gemini_format()
        
        try:
            # Generate response with function calling
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    temperature=0.7,
                    max_output_tokens=1024
                )
            )
            
            # Process response
            return await self._process_response(response, user_id, db, language)
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            from src.i18n import get_text
            return AIResponse(text=get_text("error_generic", language))
    
    async def get_response_from_voice(
        self,
        user_id: str,
        voice_data: bytes,
        language: str = "en"
    ) -> AIResponse:
        """
        Get AI response for a voice message.
        
        Args:
            user_id: User's database ID
            voice_data: Voice file bytes (OGG format from Telegram)
            language: User's language code
            
        Returns:
            AIResponse with text, transcription, and optional actions
        """
        db = get_database()
        
        # Get products for context
        products = await db.get_products(status="active")
        product_catalog = format_product_catalog(products)
        
        # Get system prompt
        system_prompt = get_system_prompt(language, product_catalog)
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(voice_data).decode("utf-8")
        
        # Build message with audio
        messages = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        data=voice_data,
                        mime_type="audio/ogg"
                    ),
                    types.Part.from_text(
                        text="Please first transcribe this voice message, then respond to it as a sales consultant."
                    )
                ]
            )
        ]
        
        # Convert tools to Gemini format
        gemini_tools = self._convert_tools_to_gemini_format()
        
        try:
            # Generate response
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    temperature=0.7,
                    max_output_tokens=1024
                )
            )
            
            # Process response
            result = await self._process_response(response, user_id, db, language)
            
            # Try to extract transcription from response
            # Gemini typically includes it in the response text
            result.transcription = self._extract_transcription(result.text)
            
            return result
            
        except Exception as e:
            print(f"Gemini voice API error: {e}")
            from src.i18n import get_text
            return AIResponse(text=get_text("error_generic", language))
    
    def _convert_tools_to_gemini_format(self) -> List[types.Tool]:
        """Convert our tool definitions to Gemini format"""
        function_declarations = []
        
        for tool in TOOLS:
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters_json_schema=tool.get("parameters")
                )
            )
        
        return [types.Tool(function_declarations=function_declarations)]
    
    async def _process_response(
        self,
        response,
        user_id: str,
        db,
        language: str
    ) -> AIResponse:
        """Process Gemini response, handling function calls if present"""
        import traceback
        
        try:
            # Check for function calls
            if not response.candidates:
                # No candidates, return error
                from src.i18n import get_text
                return AIResponse(text=get_text("error_generic", language))
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                # No content, return error
                from src.i18n import get_text
                return AIResponse(text=get_text("error_generic", language))
            
            parts = getattr(candidate.content, 'parts', None)
            if not parts:
                # No parts, try to get text directly
                text = response.text if hasattr(response, 'text') else str(response)
                return AIResponse(text=text)
            
            # Check each part for function calls
            for part in parts:
                # Check if this part is a function call
                func_call = getattr(part, 'function_call', None)
                if func_call:
                    tool_name = getattr(func_call, 'name', None)
                    if not tool_name:
                        continue
                    
                    # Get arguments
                    args = getattr(func_call, 'args', None)
                    if args:
                        if hasattr(args, '__dict__'):
                            arguments = dict(args.__dict__)
                        elif isinstance(args, dict):
                            arguments = args
                        else:
                            arguments = dict(args) if args else {}
                    else:
                        arguments = {}
                    
                    print(f"DEBUG: Function call detected: {tool_name} with args: {arguments}")
                    
                    # Execute the tool
                    try:
                        tool_result = await execute_tool(
                            tool_name,
                            arguments,
                            user_id,
                            db
                        )
                    except Exception as e:
                        print(f"ERROR: Tool execution failed: {e}\n{traceback.format_exc()}")
                        from src.i18n import get_text
                        return AIResponse(text=get_text("error_generic", language))
                    
                    # Handle specific tool results
                    if tool_name == "create_purchase_intent" and tool_result.get("success"):
                        return AIResponse(
                            text=self._format_purchase_message(tool_result, language),
                            product_id=tool_result["product_id"]
                        )
                    
                    if tool_name == "get_catalog":
                        return AIResponse(
                            text=self._format_catalog_message(tool_result, language),
                            show_shop=True
                        )
                    
                    if tool_name == "add_to_waitlist" and tool_result.get("success"):
                        from src.i18n import get_text
                        return AIResponse(
                            text=get_text(
                                "waitlist_added", 
                                language,
                                product=tool_result["product_name"]
                            )
                        )
                    
                    # For other tools, make another call with the result
                    return await self._continue_with_tool_result(
                        response,
                        tool_name,
                        tool_result,
                        user_id,
                        db,
                        language
                    )
            
            # No function call, just return the text
            text = response.text if hasattr(response, 'text') else str(response)
            return AIResponse(text=text)
            
        except Exception as e:
            print(f"ERROR: _process_response failed: {e}\n{traceback.format_exc()}")
            from src.i18n import get_text
            return AIResponse(text=get_text("error_generic", language))
    
    async def _continue_with_tool_result(
        self,
        original_response,
        tool_name: str,
        tool_result: Dict[str, Any],
        user_id: str,
        db,
        language: str
    ) -> AIResponse:
        """Continue conversation with tool result"""
        import traceback
        
        try:
            # Get conversation history to maintain context
            history = await db.get_chat_history(user_id, limit=10)
            
            # Build messages with full conversation context
            messages = []
            
            # Add conversation history (excluding the last assistant message which had the function call)
            for msg in history[:-1]:  # Exclude last message as it's the one that triggered function call
                role = "user" if msg["role"] == "user" else "model"
                messages.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
            
            # Add the last user message (the one that triggered the function call)
            if history:
                last_user_msg = history[-1] if history[-1]["role"] == "user" else None
                if last_user_msg:
                    messages.append(types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=last_user_msg["content"])]
                    ))
            
            # Add the model's response with function call
            if original_response.candidates and original_response.candidates[0].content:
                messages.append(original_response.candidates[0].content)
            
            # Add function response
            messages.append(types.Content(
                role="function",
                parts=[
                    types.Part.from_function_response(
                        name=tool_name,
                        response=tool_result
                    )
                ]
            ))
            
            # Get products for context
            products = await db.get_products(status="active")
            product_catalog = format_product_catalog(products)
            system_prompt = get_system_prompt(language, product_catalog)
            
            # Convert tools to Gemini format (include tools for potential follow-up calls)
            gemini_tools = self._convert_tools_to_gemini_format()
            
            # Generate follow-up response
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    temperature=0.7,
                    max_output_tokens=1024
                )
            )
            
            text = response.text if hasattr(response, 'text') else str(response)
            
            # Check if response suggests a purchase
            product_id = None
            if tool_result.get("products") and len(tool_result["products"]) == 1:
                product_id = tool_result["products"][0].get("id")
            elif tool_result.get("product_id"):
                product_id = tool_result["product_id"]
            
            return AIResponse(text=text, product_id=product_id)
            
        except Exception as e:
            print(f"Gemini follow-up error: {e}\n{traceback.format_exc()}")
            from src.i18n import get_text
            return AIResponse(text=get_text("error_generic", language))
    
    def _format_purchase_message(
        self,
        tool_result: Dict[str, Any],
        language: str
    ) -> str:
        """Format purchase intent message"""
        from src.i18n import get_text
        
        return get_text(
            "order_created",
            language,
            order_id="...",  # Will be created when user clicks pay
            amount=tool_result["price"]
        )
    
    def _format_catalog_message(
        self,
        tool_result: Dict[str, Any],
        language: str
    ) -> str:
        """Format catalog display message"""
        from src.i18n import get_text
        
        products = tool_result.get("products", [])
        if not products:
            return get_text("ai_no_product", language)
        
        lines = []
        for p in products:
            status = "✅" if p["in_stock"] else "❌"
            lines.append(f"{status} {p['name']} — {p['price']}₽")
        
        return get_text(
            "ai_suggest",
            language,
            products="\n".join(lines)
        )
    
    def _extract_transcription(self, text: str) -> Optional[str]:
        """Try to extract voice transcription from AI response"""
        # Gemini often includes transcription in quotes or after certain phrases
        # This is a simple heuristic
        
        import re
        
        # Look for quoted text at the beginning
        match = re.search(r'^["\'](.+?)["\']', text)
        if match:
            return match.group(1)
        
        # Look for "User said:" pattern
        match = re.search(r'(?:said|сказал|wrote|написал)[:\s]+["\']?(.+?)["\']?(?:\.|$)', text, re.I)
        if match:
            return match.group(1)
        
        return None

