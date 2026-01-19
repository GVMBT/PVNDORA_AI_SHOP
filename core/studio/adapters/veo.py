"""Google Veo Adapter.

Supports Veo 3.1 and Veo Fast models via Google AI Studio API.
Veo is unique in that it can generate video WITH native audio.

API Reference: https://ai.google.dev/gemini-api/docs/video
"""

import os
from typing import Any

import httpx

from core.logging import get_logger
from core.studio.adapters.base import (
    AdapterCapabilities,
    AdapterError,
    BaseAdapter,
    CustomOption,
    GenerationRequest,
    GenerationResult,
    GenerationStatus,
    GenerationType,
    ModelUnavailableError,
    RateLimitError,
)

logger = get_logger(__name__)

# Google AI Studio API base URL
GOOGLE_AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class VeoAdapter(BaseAdapter):
    """Adapter for Google Veo video generation.
    
    Supports:
    - Text-to-video generation
    - Image-to-video (start frame)
    - Native audio generation (unique to Veo!)
    - Multiple resolutions (720p, 1080p, 4K)
    - Multiple durations (4s, 6s, 8s)
    """
    
    model_id = "veo-3.1"
    display_name = "VEO 3.1"
    generation_type = GenerationType.VIDEO
    supports_webhooks = False  # Veo uses polling
    
    # Veo-specific constants (from official docs)
    VEO_MODEL = "veo-3.1-generate-preview"  # Official model name
    
    def __init__(self, fast_mode: bool = False) -> None:
        """Initialize Veo adapter.
        
        Args:
            fast_mode: If True, use faster but lower quality model
        """
        self.fast_mode = fast_mode
        if fast_mode:
            self.model_id = "veo-fast"
            self.display_name = "VEO FAST"
        
        super().__init__()
        
        self.api_key = os.environ.get("GOOGLE_AI_API_KEY", "")
        self.http_client = httpx.AsyncClient(timeout=120.0)
    
    def _validate_credentials(self) -> None:
        """Check that Google AI API key is set."""
        if not os.environ.get("GOOGLE_AI_API_KEY"):
            logger.warning("GOOGLE_AI_API_KEY not set - Veo adapter will not work")
    
    def get_capabilities(self) -> AdapterCapabilities:
        """Return Veo capabilities for Dynamic UI."""
        if self.fast_mode:
            return AdapterCapabilities(
                resolutions=["720p"],
                max_duration_seconds=6,
                supports_audio=False,
                supports_extend=False,
                supports_image_to_video=False,
                custom_options=[],
            )
        
        return AdapterCapabilities(
            resolutions=["720p", "1080p", "4k"],
            max_duration_seconds=8,
            supports_audio=True,  # Veo's unique feature!
            supports_extend=True,
            supports_image_to_video=True,
            custom_options=[
                CustomOption(
                    id="audio_sync",
                    type="boolean",
                    label="Генерировать звук",
                    default=True,
                ),
                CustomOption(
                    id="cinematic_preset",
                    type="select",
                    label="Стиль",
                    options=["default", "cinematic", "documentary", "animation"],
                    default="default",
                ),
                CustomOption(
                    id="negative_prompt",
                    type="text",
                    label="Негативный промпт",
                    default="",
                ),
            ],
        )
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Start Veo generation.
        
        Args:
            request: Generation request with prompt and options
            
        Returns:
            GenerationResult with operation ID for polling
        """
        if not self.api_key:
            raise AdapterError("Google AI API key not configured", code="NO_API_KEY")
        
        # Build Veo-specific payload
        payload = self._build_payload(request)
        
        try:
            # Use predictLongRunning for async video generation
            response = await self.http_client.post(
                f"{GOOGLE_AI_BASE_URL}/models/{self.VEO_MODEL}:predictLongRunning",
                json={"instances": [payload]},
                params={"key": self.api_key},
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
            )
            
            if response.status_code == 429:
                raise RateLimitError("Veo rate limit exceeded")
            
            if response.status_code == 503:
                raise ModelUnavailableError("Veo model temporarily unavailable")
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise AdapterError(
                    f"Veo API error: {response.status_code}",
                    code=str(response.status_code),
                    raw_error=error_data,
                )
            
            data = response.json()
            operation_name = data.get("name", "")
            
            if not operation_name:
                raise AdapterError("No operation ID in Veo response", raw_error=data)
            
            logger.info(f"Veo generation started: {operation_name}")
            
            return GenerationResult(
                job_id=operation_name,
                status=GenerationStatus.PROCESSING,
                progress=0,
                has_audio=request.custom_params.get("audio_sync", True),
                raw_response=data,
            )
            
        except httpx.TimeoutException as e:
            raise AdapterError("Veo API timeout", code="TIMEOUT", retryable=True, raw_error=e)
        except httpx.HTTPError as e:
            raise AdapterError(f"Veo HTTP error: {e}", code="HTTP_ERROR", retryable=True, raw_error=e)
    
    async def check_status(self, job_id: str) -> GenerationResult:
        """Poll Veo operation status.
        
        Args:
            job_id: Operation name from generate()
            
        Returns:
            GenerationResult with current status
        """
        if not self.api_key:
            raise AdapterError("Google AI API key not configured", code="NO_API_KEY")
        
        try:
            response = await self.http_client.get(
                f"{GOOGLE_AI_BASE_URL}/{job_id}",
                params={"key": self.api_key},
            )
            
            if response.status_code != 200:
                raise AdapterError(f"Veo status check failed: {response.status_code}")
            
            data = response.json()
            
            # Check if operation is done
            if data.get("done"):
                # Check for error
                if "error" in data:
                    error = data["error"]
                    return GenerationResult(
                        job_id=job_id,
                        status=GenerationStatus.FAILED,
                        error_message=error.get("message", "Unknown error"),
                        error_code=str(error.get("code", "")),
                        raw_response=data,
                    )
                
                # Success - extract video URL
                result = data.get("response", {})
                video_uri = self._extract_video_uri(result)
                
                return GenerationResult(
                    job_id=job_id,
                    status=GenerationStatus.COMPLETED,
                    progress=100,
                    result_url=video_uri,
                    has_audio=True,  # Veo always generates with audio if requested
                    raw_response=data,
                )
            
            # Still processing - estimate progress from metadata
            metadata = data.get("metadata", {})
            progress = self._estimate_progress(metadata)
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatus.PROCESSING,
                progress=progress,
                raw_response=data,
            )
            
        except httpx.HTTPError as e:
            raise AdapterError(f"Veo status check HTTP error: {e}", retryable=True)
    
    async def cancel(self, job_id: str) -> bool:
        """Cancel Veo operation.
        
        Note: Google AI API may not support cancellation for all operations.
        """
        try:
            response = await self.http_client.post(
                f"{GOOGLE_AI_BASE_URL}/{job_id}:cancel",
                params={"key": self.api_key},
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to cancel Veo operation {job_id}: {e}")
            return False
    
    def _build_payload(self, request: GenerationRequest) -> dict[str, Any]:
        """Build Veo API payload from GenerationRequest.
        
        Format for predictLongRunning (REST API):
        {
            "prompt": "...",
            "config": {"number_of_videos": 1, "resolution": "720p"}
        }
        """
        payload: dict[str, Any] = {
            "prompt": request.prompt,
        }
        
        # Build config
        config: dict[str, Any] = {
            "number_of_videos": 1,
            "resolution": request.resolution or "720p",
        }
        
        # Add aspect ratio if specified
        if request.aspect_ratio:
            # Veo accepts "16:9" or "9:16"
            config["aspect_ratio"] = request.aspect_ratio
        
        payload["config"] = config
        
        # Add negative prompt if provided
        if request.custom_params.get("negative_prompt"):
            payload["negativePrompt"] = request.custom_params["negative_prompt"]
        
        # Add start frame for image-to-video
        if request.start_frame_url:
            payload["image"] = {
                "imageUri": request.start_frame_url,
            }
        
        return payload
    
    def _extract_video_uri(self, result: dict[str, Any]) -> str | None:
        """Extract video URI from Veo response.
        
        Response structure (from docs):
        {
            "generateVideoResponse": {
                "generatedSamples": [{"video": {"uri": "gs://..."}}]
            }
        }
        Or:
        {
            "generated_videos": [{"video": {"uri": "gs://..."}}]
        }
        """
        # Try generateVideoResponse structure (REST API)
        if "generateVideoResponse" in result:
            samples = result["generateVideoResponse"].get("generatedSamples", [])
            if samples and len(samples) > 0:
                video = samples[0].get("video", {})
                return video.get("uri")
        
        # Try generated_videos structure (SDK style)
        if "generated_videos" in result:
            videos = result["generated_videos"]
            if videos and len(videos) > 0:
                video = videos[0].get("video", {})
                return video.get("uri") or video.get("name")
        
        # Try generatedSamples directly
        if "generatedSamples" in result:
            samples = result["generatedSamples"]
            if samples and len(samples) > 0:
                video = samples[0].get("video", {})
                return video.get("uri")
        
        # Fallback: check for direct video/videoUri
        if "videoUri" in result:
            return result["videoUri"]
        
        if "video" in result:
            video = result["video"]
            if isinstance(video, dict):
                return video.get("uri") or video.get("url") or video.get("name")
        
        logger.warning(f"Could not extract video URI from Veo result: {result}")
        return None
    
    def _estimate_progress(self, metadata: dict[str, Any]) -> int:
        """Estimate progress percentage from metadata."""
        # Veo may provide progress info in metadata
        if "progressPercent" in metadata:
            return int(metadata["progressPercent"])
        
        # Otherwise estimate based on state
        state = metadata.get("state", "").lower()
        if state == "queued":
            return 5
        elif state == "preprocessing":
            return 15
        elif state == "generating":
            return 50
        elif state == "postprocessing":
            return 85
        
        return 30  # Default mid-progress


class VeoFastAdapter(VeoAdapter):
    """Adapter for Veo Fast model (quicker, lower quality)."""
    
    model_id = "veo-fast"
    display_name = "VEO FAST"
    
    def __init__(self) -> None:
        super().__init__(fast_mode=True)
