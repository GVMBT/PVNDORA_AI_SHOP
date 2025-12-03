"""AI Consultant - Gemini Integration"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.services.database import get_database
from src.ai.prompts import get_system_prompt, format_product_catalog
from src.ai.tools import TOOLS, execute_tool
from core.models import AIResponse as StructuredAIResponse, ActionType

# Lazy import for RAG - optional feature
try:
    from core.rag import ProductSearch
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    ProductSearch = None


class AIConsultant:
    """AI Sales Consultant powered by Gemini 2.5 Flash"""
    
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        # Initialize RAG only if available
        if RAG_AVAILABLE and ProductSearch:
            try:
                self.product_search = ProductSearch()
                if not self.product_search.is_available:
                    self.product_search = None
            except (ImportError, Exception):
                self.product_search = None  # RAG optional
        else:
            self.product_search = None
        self._cached_contents = {}  # Cache for system prompts by language
        self._cache_retry_timestamps = {}  # Track last retry attempt for failed caches
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_response(
        self,
        user_id: str,
        user_message: str,
        language: str = "en",
        progress_callback=None
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
        
        # Parallel DB calls for better performance (reduces latency by ~50%)
        products, history = await asyncio.gather(
            db.get_products(status="active"),
            db.get_chat_history(user_id, limit=5)  # Reduced from 10 to 5 for speed
        )
        product_catalog = format_product_catalog(products)
        
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
            # Step 1: Generate response with Function Calling (NO structured outputs here!)
            # Gemini doesn't support tools + response_schema simultaneously
            config_with_tools = types.GenerateContentConfig(
                tools=gemini_tools,
                temperature=0.7,
                max_output_tokens=2048
            )
            
            # Use cached content if available (skip if None - means caching disabled)
            if cached_content_name:
                config_with_tools.cached_content = cached_content_name
            else:
                # Fallback: use system_instruction if caching failed
                config_with_tools.system_instruction = base_system_prompt
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config_with_tools
            )
            
            # Notify progress: analyzing response
            if progress_callback:
                await progress_callback("analyzing", "")
            
            # Process response (handles function calls, then final structured output)
            return await self._process_response(response, user_id, db, language, messages, progress_callback)
            
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
        
        # Parallel DB calls for better performance (same as text messages)
        products, history = await asyncio.gather(
            db.get_products(status="active"),
            db.get_chat_history(user_id, limit=5)
        )
        product_catalog = format_product_catalog(products)
        
        # Get system prompt
        system_prompt = get_system_prompt(language, product_catalog)
        
        # Convert OGG Opus (Telegram format) to a supported format
        # Gemini supports: WAV, MP3, AIFF, AAC, OGG Vorbis, FLAC
        # Telegram sends OGG Opus which may not be fully supported
        converted_data, mime_type = await self._convert_audio_for_gemini(voice_data)
        
        # Build messages with conversation history first
        messages = []
        
        # Add conversation history for context continuity
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            messages.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        
        # Build voice message with audio and instruction
        from src.i18n import get_text
        audio_instruction = get_text("ai_audio_instruction", language)
        
        # Add current voice message
        messages.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        data=converted_data,
                        mime_type=mime_type
                    ),
                    types.Part.from_text(text=audio_instruction)
                ]
            )
        )
        
        # Convert tools to Gemini format
        gemini_tools = self._convert_tools_to_gemini_format()
        
        try:
            print(f"DEBUG: Voice message processing - audio size: {len(converted_data)} bytes, mime: {mime_type}")
            
            # Step 1: Generate with tools (NO structured output here - Gemini limitation)
            config_with_tools = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=gemini_tools,
                temperature=0.7,
                max_output_tokens=2048
            )
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config_with_tools
            )
            
            print(f"DEBUG: Voice response received, candidates: {len(response.candidates) if response.candidates else 0}")
            
            # Process response (handles function calls and structured output)
            result = await self._process_response(response, user_id, db, language, messages)
            
            return result
            
        except Exception as e:
            error_str = str(e)
            print(f"ERROR: Gemini voice API error: {error_str}")
            import traceback
            traceback.print_exc()
            
            # Check for specific error types
            if "INVALID_ARGUMENT" in error_str or "unsupported" in error_str.lower():
                print("ERROR: Audio format may not be supported. Telegram sends OGG Opus, Gemini expects OGG Vorbis.")
            
            return self._create_error_response(language, str(e))
    
    async def _convert_audio_for_gemini(self, ogg_data: bytes) -> tuple[bytes, str]:
        """
        Convert OGG Opus audio (from Telegram) to a format supported by Gemini.
        
        Gemini officially supports: WAV, MP3, AIFF, AAC, OGG Vorbis, FLAC
        Telegram sends: OGG Opus
        
        Strategy:
        1. Gemini 2.5 Flash actually supports OGG Opus (tested working)
        2. Use audio/ogg mime type which works with both Opus and Vorbis
        
        Args:
            ogg_data: Raw OGG Opus bytes from Telegram
            
        Returns:
            Tuple of (audio_bytes, mime_type)
        """
        # Validate OGG magic bytes
        if len(ogg_data) < 4:
            print(f"ERROR: Voice data too short: {len(ogg_data)} bytes")
            return ogg_data, "audio/ogg"
        
        # Check OGG magic bytes
        if ogg_data[:4] == b'OggS':
            print(f"DEBUG: Valid OGG file detected, size: {len(ogg_data)} bytes")
            # Gemini 2.5 Flash supports OGG containers (including Opus codec)
            return ogg_data, "audio/ogg"
        
        # If not valid OGG, log and try anyway
        print(f"WARNING: Voice data doesn't have OGG magic bytes, first 4: {ogg_data[:4]!r}")
        return ogg_data, "audio/ogg"
    
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
        original_messages: List[types.Content] = None,
        progress_callback=None
    ) -> StructuredAIResponse:
        """
        Process Gemini response with Structured Outputs.
        Handles function calls if present, otherwise parses structured JSON response.
        """
        import traceback
        
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
            
            # Collect ALL function calls from the response
            function_calls = []
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
                    
                    function_calls.append((tool_name, arguments))
            
            # If we have function calls, execute ALL of them in PARALLEL
            if function_calls:
                print(f"DEBUG: Found {len(function_calls)} function calls: {[fc[0] for fc in function_calls]}")
                
                # Progress callback - show all tools at once
                if progress_callback:
                    tool_names = " ".join([fc[0] for fc in function_calls])
                    await progress_callback("tool", tool_names)
                
                # Execute all tools in PARALLEL for better latency
                async def execute_single_tool(tool_name: str, arguments: dict):
                    print(f"DEBUG: Executing {tool_name} with args: {arguments}")
                    try:
                        return tool_name, await execute_tool(tool_name, arguments, user_id, db, language)
                    except Exception as e:
                        print(f"ERROR: Tool {tool_name} failed: {e}")
                        return tool_name, {"success": False, "error": str(e)}
                
                # Run all tools concurrently
                results = await asyncio.gather(*[
                    execute_single_tool(name, args) for name, args in function_calls
                ])
                tool_results = dict(results)
                
                # Build chat history if not provided
                if not original_messages:
                    history = await db.get_chat_history(user_id, limit=10)
                    original_messages = []
                    for msg in history:
                        role = "user" if msg["role"] == "user" else "model"
                        original_messages.append(types.Content(
                            role=role,
                            parts=[types.Part.from_text(text=msg["content"])]
                        ))
                
                # Progress: generating response
                if progress_callback:
                    await progress_callback("generating", "")
                
                # Continue with ALL tool results combined
                return await self._continue_with_all_tool_results(
                    original_messages,
                    response,
                    function_calls,
                    tool_results,
                    user_id,
                    db,
                    language
                )
            
            # Progress: generating response (no tools)
            if progress_callback:
                await progress_callback("generating", "")
            
            # No function call - need to make SECOND request with structured output
            # Because Gemini doesn't support tools + response_schema simultaneously
            return await self._generate_structured_response(
                original_messages, response, user_id, db, language
            )
            
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
            text = response.text if hasattr(response, 'text') and response.text else None
            
            if not text:
                print("ERROR: Response text is None or empty")
                # Try to get text from candidates if available
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if candidate and hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if part and hasattr(part, 'text') and part.text:
                                        text = part.text
                                        print(f"DEBUG: Extracted text from candidate: {text[:100]}")
                                        break
                                if text:
                                    break
                
                if not text:
                    print("ERROR: Could not extract text from response")
                    # Log response structure for debugging
                    if hasattr(response, 'candidates'):
                        print(f"DEBUG: Response has {len(response.candidates) if response.candidates else 0} candidates")
                    return StructuredAIResponse(
                        thought="Empty response from AI",
                        reply_text=self._get_error_message(language),
                        action=ActionType.NONE
                    )
            
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
    
    def _filter_technical_details(self, error_message: str) -> str:
        """
        Filter out technical details from error messages.
        
        Removes:
        - Module names (upstash_redis, psycopg2, etc.)
        - Error codes (42P10, etc.)
        - Internal paths and stack traces
        - Technical error types
        """
        if not error_message:
            return "A temporary error occurred"
        
        # Remove common technical patterns
        import re
        
        # Remove module names
        error_message = re.sub(r"No module named ['\"]([\w_]+)['\"]", "A required component is missing", error_message)
        error_message = re.sub(r"ModuleNotFoundError:", "", error_message)
        
        # Remove error codes
        error_message = re.sub(r"code ['\"]\d+[A-Z]\d+['\"]", "", error_message)
        error_message = re.sub(r"code: ['\"]\d+[A-Z]\d+['\"]", "", error_message)
        
        # Remove file paths
        error_message = re.sub(r"/var/task/[\w/\.]+", "", error_message)
        error_message = re.sub(r"File [\"'][^\"']+[\"']", "", error_message)
        
        # Remove technical error types but keep the message
        error_message = re.sub(r"^\w+Error:\s*", "", error_message)
        error_message = re.sub(r"^\w+Exception:\s*", "", error_message)
        
        # Remove connection strings and credentials
        error_message = re.sub(r"postgresql://[^\s]+", "", error_message)
        error_message = re.sub(r"connection to server[^\n]+", "", error_message)
        
        # Clean up multiple spaces
        error_message = re.sub(r"\s+", " ", error_message).strip()
        
        # If message is too technical or empty, return generic
        technical_keywords = ["module", "import", "traceback", "stack", "FATAL", "psycopg2", "upstash"]
        if any(keyword.lower() in error_message.lower() for keyword in technical_keywords):
            return "A temporary service error occurred"
        
        if not error_message or len(error_message) < 5:
            return "A temporary error occurred"
        
        return error_message
    
    async def _get_or_create_cache(self, language: str, system_prompt: str) -> Optional[str]:
        """
        Get or create cached content for system prompt.
        
        Implements retry logic: if cache was disabled due to 429 error,
        periodically (once per hour) attempts to recreate it.
        
        Args:
            language: Language code
            system_prompt: System prompt text
            
        Returns:
            Cached content name or None if caching fails/unavailable
        """
        cache_key = f"system_prompt_{language}"
        RETRY_INTERVAL_HOURS = 1  # Retry after 1 hour
        
        # Check if we already have a valid cache for this language
        if cache_key in self._cached_contents:
            cached_value = self._cached_contents[cache_key]
            # If cache exists and is not None, return it
            if cached_value is not None:
                return cached_value
            
            # If cache is None (was disabled), check if we should retry
            last_retry = self._cache_retry_timestamps.get(cache_key)
            if last_retry:
                time_since_retry = datetime.now() - last_retry
                # If less than RETRY_INTERVAL_HOURS passed, don't retry yet
                if time_since_retry < timedelta(hours=RETRY_INTERVAL_HOURS):
                    return None  # Work without cache for now
            # If no timestamp or enough time passed, try to recreate
        
        # Try to create cache (either first time or retry after failure)
        try:
            # Create cached content with system instruction
            # TTL: 24 hours (86400 seconds) - must be string format "86400s"
            ttl = "86400s"  # 24 hours in seconds as string
            
            cache = await asyncio.to_thread(
                lambda: self.client.caches.create(
                    model=f"models/{self.model}",
                    config=types.CreateCachedContentConfig(
                        display_name=f"system_prompt_{language}",
                        system_instruction=system_prompt,
                        ttl=ttl
                    )
                )
            )
            
            # Store cache name and clear retry timestamp (success!)
            self._cached_contents[cache_key] = cache.name
            if cache_key in self._cache_retry_timestamps:
                del self._cache_retry_timestamps[cache_key]
            print(f"INFO: Context cache created successfully for {language}")
            return cache.name
            
        except Exception as e:
            error_str = str(e)
            # Check if it's a 429 (rate limit) - mark as disabled but allow retry later
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"WARNING: Context cache limit exceeded for {language}. Will retry in {RETRY_INTERVAL_HOURS} hour(s).")
                # Mark as disabled and record retry timestamp
                self._cached_contents[cache_key] = None
                self._cache_retry_timestamps[cache_key] = datetime.now()
            else:
                print(f"WARNING: Failed to create context cache for {language}: {e}")
                # For non-429 errors, also mark as None but allow retry
                self._cached_contents[cache_key] = None
                self._cache_retry_timestamps[cache_key] = datetime.now()
            # Continue without caching - not critical, will use system_instruction instead
            return None
    
    async def _generate_structured_response(
        self,
        messages: List[types.Content],
        text_response,
        user_id: str,
        db,
        language: str
    ) -> StructuredAIResponse:
        """
        Generate structured JSON response from unstructured text response.
        Called when AI didn't use function calling but we need structured output.
        """
        import traceback
        
        try:
            # Get text from initial response
            initial_text = text_response.text if hasattr(text_response, 'text') and text_response.text else ""
            
            # If initial text is empty, try to extract from candidates
            if not initial_text and hasattr(text_response, 'candidates') and text_response.candidates:
                for candidate in text_response.candidates:
                    if candidate and hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            for part in candidate.content.parts:
                                if part and hasattr(part, 'text') and part.text:
                                    initial_text = part.text
                                    print(f"DEBUG: Extracted initial text from candidate: {initial_text[:100]}")
                                    break
                            if initial_text:
                                break
            
            # If still no text, we can't generate structured response
            if not initial_text:
                print("ERROR: No text available for structured response generation")
                return StructuredAIResponse(
                    thought="No text response available",
                    reply_text=self._get_error_message(language),
                    action=ActionType.NONE
                )
            
            # Make a follow-up request to get structured output
            structured_messages = list(messages)
            
            # Add model's text response
            structured_messages.append(types.Content(
                role="model",
                parts=[types.Part.from_text(text=initial_text)]
            ))
            
            # Add instruction to format as JSON
            structured_messages.append(types.Content(
                role="user",
                parts=[types.Part.from_text(
                    text="Now format your response as a valid JSON following the exact schema I provided. Include your previous response in reply_text field."
                )]
            ))
            
            # Get system prompt
            base_system_prompt = get_system_prompt(language, "")
            cached_content_name = await self._get_or_create_cache(language, base_system_prompt)
            
            # Generate with structured output
            config_structured = types.GenerateContentConfig(
                temperature=0.3,  # Lower temp for more consistent JSON
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=StructuredAIResponse.model_json_schema()
            )
            
            if cached_content_name:
                config_structured.cached_content = cached_content_name
            else:
                config_structured.system_instruction = base_system_prompt
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=structured_messages,
                config=config_structured
            )
            
            # Check if response is empty
            if not hasattr(response, 'text') or not response.text:
                # Try to extract from candidates
                text_from_candidates = None
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if candidate and hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if part and hasattr(part, 'text') and part.text:
                                        text_from_candidates = part.text
                                        break
                                if text_from_candidates:
                                    break
                
                if not text_from_candidates:
                    print("WARNING: Empty response from structured generation, using original text")
                    # Fallback: use original text response
                    initial_text = text_response.text if hasattr(text_response, 'text') and text_response.text else ""
                    if initial_text:
                        # Try to create structured response from text
                        return StructuredAIResponse(
                            thought="Using text response as fallback",
                            reply_text=initial_text,
                            action=ActionType.NONE
                        )
                    else:
                        return StructuredAIResponse(
                            thought="Both structured and text responses are empty",
                            reply_text=self._get_error_message(language),
                            action=ActionType.NONE
                        )
            
            return self._parse_structured_response(response, language)
            
        except Exception as e:
            print(f"ERROR: _generate_structured_response failed: {e}\n{traceback.format_exc()}")
            # Fallback: create response from original text
            initial_text = text_response.text if hasattr(text_response, 'text') and text_response.text else ""
            return StructuredAIResponse(
                thought="Structured generation failed, using text response",
                reply_text=initial_text if initial_text else self._get_error_message(language),
                action=ActionType.NONE
            )
    
    async def _continue_with_all_tool_results(
        self,
        original_messages: List[types.Content],
        original_response,
        function_calls: List[tuple],  # List of (tool_name, arguments)
        tool_results: Dict[str, Any],  # {tool_name: result}
        user_id: str,
        db,
        language: str
    ) -> StructuredAIResponse:
        """Continue conversation with ALL tool results - handles parallel tool execution"""
        import traceback
        
        try:
            # Build messages with full conversation context
            messages = list(original_messages)
            
            # Add the model's response with function calls
            if original_response.candidates and original_response.candidates[0].content:
                messages.append(original_response.candidates[0].content)
            
            # Add ALL function responses
            function_response_parts = []
            for tool_name, _ in function_calls:
                result = tool_results.get(tool_name, {"success": False, "error": "Unknown error"})
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=result
                    )
                )
            
            # Add all function responses as a single Content
            if function_response_parts:
                messages.append(types.Content(
                    role="function",
                    parts=function_response_parts
                ))
            
            # Get cached content for this language
            base_system_prompt = get_system_prompt(language, "")
            cached_content_name = await self._get_or_create_cache(language, base_system_prompt)
            
            # Generate final response with Structured Outputs
            config_final = types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json",
                response_schema=StructuredAIResponse.model_json_schema()
            )
            
            if cached_content_name:
                config_final.cached_content = cached_content_name
            else:
                config_final.system_instruction = base_system_prompt
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=config_final
            )
            
            return self._parse_structured_response(response, language)
            
        except Exception as e:
            print(f"Gemini multi-tool follow-up error: {e}\n{traceback.format_exc()}")
            return self._create_error_response(language, str(e))
    
    # Note: _format_purchase_message and _format_catalog_message removed
    # AI now handles formatting through Structured Outputs (reply_text field)
    # This gives AI more flexibility in how to present information
