"""AI Consultant - Gemini Integration"""
import os
import base64
from typing import Optional, List, Dict, Any
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.services.database import get_database
from src.ai.prompts import get_system_prompt, format_product_catalog
from src.ai.tools import TOOLS, execute_tool
from core.models import AIResponse as StructuredAIResponse, ActionType
from core.rag import ProductSearch


class AIConsultant:
    """AI Sales Consultant powered by Gemini 2.5 Flash"""
    
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.product_search = ProductSearch()  # RAG for semantic product search
        self._cached_contents = {}  # Cache for system prompts by language
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_response(
        self,
        user_id: str,
        user_message: str,
        language: str = "en"
    ) -> StructuredAIResponse:
        """
        Get AI response for a text message using Structured Outputs.
        
        Args:
            user_id: User's database ID
            user_message: User's message text
            language: User's language code
            
        Returns:
            StructuredAIResponse with structured fields
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
        
        # Get system prompt (base prompt without catalog - catalog added to messages)
        base_system_prompt = get_system_prompt(language, "")  # Empty catalog, will add to messages
        
        # Get or create cached content for this language
        cached_content_name = await self._get_or_create_cache(language, base_system_prompt)
        
        # Add product catalog as first message (after system instruction)
        if product_catalog:
            catalog_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Current product catalog:\n{product_catalog}")]
            )
            # Insert catalog at the beginning of messages
            messages.insert(0, catalog_message)
        
        # Convert tools to Gemini format
        gemini_tools = self._convert_tools_to_gemini_format()
        
        try:
            # Generate response with Structured Outputs + Function Calling + Context Caching
            config = types.GenerateContentConfig(
                tools=gemini_tools,
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=StructuredAIResponse.model_json_schema()
            )
            
            # Use cached content if available
            if cached_content_name:
                config.cached_content = cached_content_name
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config
            )
            
            # Process response (pass messages for function call continuation)
            return await self._process_response(response, user_id, db, language, messages)
            
        except Exception as e:
            print(f"Gemini API error: {e}")
            import traceback
            traceback.print_exc()
            # Return structured error response
            return StructuredAIResponse(
                thought=f"Error occurred: {str(e)}",
                reply_text=self._get_error_message(language),
                action=ActionType.NONE
            )
    
    async def get_response_from_voice(
        self,
        user_id: str,
        voice_data: bytes,
        language: str = "en"
    ) -> StructuredAIResponse:
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
            # Generate response with Structured Outputs
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=gemini_tools,
                    temperature=0.7,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                    response_schema=StructuredAIResponse.model_json_schema()
                )
            )
            
            # Process response with Structured Outputs
            result = await self._process_response(response, user_id, db, language, messages)
            
            # Note: Transcription is now handled by AI in reply_text
            # No need to extract separately
            
            return result
            
        except Exception as e:
            print(f"Gemini voice API error: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_response(language, str(e))
    
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
        language: str,
        original_messages: List[types.Content] = None
    ) -> StructuredAIResponse:
        """
        Process Gemini response with Structured Outputs.
        Handles function calls if present, otherwise parses structured JSON response.
        """
        import traceback
        import json
        
        try:
            # Check for function calls first
            if not response.candidates:
                return self._create_error_response(language, "No response candidates")
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content:
                return self._create_error_response(language, "No content in response")
            
            parts = getattr(candidate.content, 'parts', None)
            if not parts:
                # Try to parse as structured JSON (Structured Outputs)
                return self._parse_structured_response(response, language)
            
            # Check each part for function calls
            for part in parts:
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
                        return self._create_error_response(language, f"Tool execution failed: {str(e)}")
                    
                    # Continue conversation with tool result
                    if not original_messages:
                        history = await db.get_chat_history(user_id, limit=10)
                        original_messages = []
                        for msg in history:
                            role = "user" if msg["role"] == "user" else "model"
                            original_messages.append(types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=msg["content"])]
                            ))
                    
                    return await self._continue_with_tool_result(
                        original_messages,
                        response,
                        tool_name,
                        tool_result,
                        user_id,
                        db,
                        language
                    )
            
            # No function call - parse structured JSON response
            return self._parse_structured_response(response, language)
            
        except Exception as e:
            print(f"ERROR: _process_response failed: {e}\n{traceback.format_exc()}")
            return self._create_error_response(language, str(e))
    
    def _parse_structured_response(
        self,
        response,
        language: str
    ) -> StructuredAIResponse:
        """Parse structured JSON response from Gemini"""
        import json
        
        try:
            # Get text response (should be JSON)
            text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse JSON
            data = json.loads(text)
            
            # Convert action string to ActionType enum
            if "action" in data and isinstance(data["action"], str):
                try:
                    data["action"] = ActionType(data["action"])
                except ValueError:
                    data["action"] = ActionType.NONE
            
            # Validate and create StructuredAIResponse
            return StructuredAIResponse(**data)
            
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON response: {e}")
            print(f"Response text: {text[:500]}")
            # Fallback: create response from text
            return StructuredAIResponse(
                thought="Failed to parse structured response",
                reply_text=text if text else self._get_error_message(language),
                action=ActionType.NONE
            )
        except Exception as e:
            print(f"ERROR: Failed to create structured response: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_response(language, str(e))
    
    def _create_error_response(
        self,
        language: str,
        error_msg: str = None
    ) -> StructuredAIResponse:
        """Create error response"""
        return StructuredAIResponse(
            thought=f"Error: {error_msg or 'Unknown error'}",
            reply_text=self._get_error_message(language),
            action=ActionType.NONE
        )
    
    def _get_error_message(self, language: str) -> str:
        """Get localized error message"""
        from src.i18n import get_text
        return get_text("error_generic", language)
    
    async def _get_or_create_cache(self, language: str, system_prompt: str) -> Optional[str]:
        """
        Get or create cached content for system prompt.
        
        Args:
            language: Language code
            system_prompt: System prompt text
            
        Returns:
            Cached content name or None if caching fails
        """
        cache_key = f"system_prompt_{language}"
        
        # Check if we already have a cache for this language
        if cache_key in self._cached_contents:
            return self._cached_contents[cache_key]
        
        try:
            # Create cached content with system instruction
            # TTL: 24 hours (system prompt doesn't change often)
            import datetime
            ttl = datetime.timedelta(hours=24)
            
            cache = self.client.caches.create(
                model=f"models/{self.model}",
                config=types.CreateCachedContentConfig(
                    display_name=f"system_prompt_{language}",
                    system_instruction=system_prompt,
                    ttl=ttl
                )
            )
            
            # Store cache name
            self._cached_contents[cache_key] = cache.name
            return cache.name
            
        except Exception as e:
            print(f"WARNING: Failed to create context cache for {language}: {e}")
            # Continue without caching - not critical
            return None
    
    async def _continue_with_tool_result(
        self,
        original_messages: List[types.Content],
        original_response,
        tool_name: str,
        tool_result: Dict[str, Any],
        user_id: str,
        db,
        language: str
    ) -> StructuredAIResponse:
        """Continue conversation with tool result using Structured Outputs"""
        import traceback
        
        try:
            # Build messages with full conversation context
            messages = list(original_messages)
            
            # Add the model's response with function call
            if original_response.candidates and original_response.candidates[0].content:
                messages.append(original_response.candidates[0].content)
            
            # Add function response (must come immediately after function call)
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
            
            # Convert tools to Gemini format
            gemini_tools = self._convert_tools_to_gemini_format()
            
            # Get cached content for this language
            base_system_prompt = get_system_prompt(language, "")
            cached_content_name = await self._get_or_create_cache(language, base_system_prompt)
            
            # Generate follow-up response with Structured Outputs + Context Caching
            config = types.GenerateContentConfig(
                tools=gemini_tools,
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=StructuredAIResponse.model_json_schema()
            )
            
            # Use cached content if available
            if cached_content_name:
                config.cached_content = cached_content_name
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config
            )
            
            # Parse structured response
            return self._parse_structured_response(response, language)
            
        except Exception as e:
            print(f"Gemini follow-up error: {e}\n{traceback.format_exc()}")
            return self._create_error_response(language, str(e))
    
    # Note: _format_purchase_message and _format_catalog_message removed
    # AI now handles formatting through Structured Outputs (reply_text field)
    # This gives AI more flexibility in how to present information

