"""Base Adapter for AI Providers.

Defines unified interface for all AI generation providers.
Each provider implements this interface to handle their specific API.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class GenerationType(str, Enum):
    """Type of content being generated."""
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"


class GenerationStatus(str, Enum):
    """Status of generation job."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CustomOption:
    """Custom option definition for Dynamic UI."""
    id: str
    type: str  # 'boolean', 'select', 'text', 'number'
    label: str
    options: list[str] | None = None  # For 'select' type
    default: Any = None
    min_value: float | None = None  # For 'number' type
    max_value: float | None = None


@dataclass
class AdapterCapabilities:
    """Capabilities of an AI model for Dynamic UI."""
    resolutions: list[str] = field(default_factory=lambda: ["720p"])
    max_duration_seconds: int | None = None
    supports_audio: bool = False
    supports_extend: bool = False
    supports_image_to_video: bool = False
    custom_options: list[CustomOption] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "resolutions": self.resolutions,
            "max_duration_seconds": self.max_duration_seconds,
            "supports_audio": self.supports_audio,
            "supports_extend": self.supports_extend,
            "supports_image_to_video": self.supports_image_to_video,
            "custom_options": [
                {
                    "id": opt.id,
                    "type": opt.type,
                    "label": opt.label,
                    "options": opt.options,
                    "default": opt.default,
                }
                for opt in self.custom_options
            ],
        }


@dataclass
class GenerationRequest:
    """Unified request for AI generation.
    
    Contains both standard fields (supported by all providers)
    and custom_params for provider-specific options.
    """
    prompt: str
    type: GenerationType
    
    # Standard fields (available for most providers)
    aspect_ratio: str = "16:9"
    duration_seconds: int | None = None
    resolution: str | None = None
    
    # For image-to-video modes
    start_frame_url: str | None = None
    end_frame_url: str | None = None
    
    # For video extension
    source_video_url: str | None = None
    
    # Provider-specific parameters
    # Examples:
    # - Veo: {"audio_sync": True, "cinematic_preset": "cyberpunk"}
    # - Kling: {"camera_motion": "orbit_360"}
    # - Suno: {"style": "electronic ambient", "instrumental": True}
    custom_params: dict[str, Any] = field(default_factory=dict)
    
    # Internal tracking
    user_id: str | None = None
    generation_id: str | None = None


@dataclass
class GenerationResult:
    """Unified result from AI generation."""
    job_id: str
    status: GenerationStatus
    
    # Progress (0-100)
    progress: int = 0
    
    # Result URLs (when completed)
    result_url: str | None = None
    thumbnail_url: str | None = None
    
    # Metadata
    duration_seconds: float | None = None
    has_audio: bool = False
    file_size_bytes: int | None = None
    
    # Error info (when failed)
    error_message: str | None = None
    error_code: str | None = None
    
    # Provider-specific data
    raw_response: dict[str, Any] | None = None
    
    def is_terminal(self) -> bool:
        """Check if status is terminal (no more updates expected)."""
        return self.status in (
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED,
        )


class BaseAdapter(ABC):
    """Base class for all AI provider adapters.
    
    Each provider must implement:
    - generate() - Start a new generation
    - check_status() - Poll for status updates
    - get_capabilities() - Return model capabilities for UI
    
    Optional:
    - cancel() - Cancel a running generation
    - handle_webhook() - Process webhook callbacks
    """
    
    # Model identifier (must match studio_model_prices.id)
    model_id: str = ""
    
    # Display name
    display_name: str = ""
    
    # Generation type
    generation_type: GenerationType = GenerationType.VIDEO
    
    # Does this provider support webhooks?
    supports_webhooks: bool = False
    
    # Webhook URL path (if supported)
    webhook_path: str | None = None
    
    def __init__(self) -> None:
        """Initialize adapter with API credentials from environment."""
        self._validate_credentials()
    
    def _validate_credentials(self) -> None:
        """Validate that required API credentials are set.
        
        Override in subclass to check specific env vars.
        """
        pass
    
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Start a new generation.
        
        Args:
            request: Unified generation request
            
        Returns:
            GenerationResult with job_id and initial status
            
        Raises:
            AdapterError: If generation fails to start
        """
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> GenerationResult:
        """Check status of a generation job.
        
        Args:
            job_id: Provider's job identifier
            
        Returns:
            GenerationResult with current status and progress
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilities:
        """Return model capabilities for Dynamic UI.
        
        Returns:
            AdapterCapabilities describing what this model supports
        """
        pass
    
    async def cancel(self, job_id: str) -> bool:
        """Cancel a running generation.
        
        Default implementation returns False (not supported).
        Override in subclass if provider supports cancellation.
        
        Args:
            job_id: Provider's job identifier
            
        Returns:
            True if cancelled successfully
        """
        logger.warning(f"{self.model_id} does not support cancellation")
        return False
    
    async def handle_webhook(self, payload: dict[str, Any]) -> GenerationResult | None:
        """Process webhook callback from provider.
        
        Default implementation returns None (not supported).
        Override in subclass if provider sends webhooks.
        
        Args:
            payload: Webhook payload from provider
            
        Returns:
            GenerationResult if payload was processed, None otherwise
        """
        logger.warning(f"{self.model_id} does not support webhooks")
        return None
    
    def _build_webhook_url(self, base_url: str, generation_id: str) -> str:
        """Build webhook callback URL for this generation.
        
        Args:
            base_url: Base URL of the application
            generation_id: Our internal generation ID
            
        Returns:
            Full webhook URL
        """
        if not self.webhook_path:
            return ""
        return f"{base_url}{self.webhook_path}?generation_id={generation_id}"


class AdapterError(Exception):
    """Error from AI provider adapter."""
    
    def __init__(
        self,
        message: str,
        code: str | None = None,
        retryable: bool = False,
        raw_error: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.raw_error = raw_error


class RateLimitError(AdapterError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None) -> None:
        super().__init__(message, code="RATE_LIMIT", retryable=True)
        self.retry_after = retry_after


class InsufficientCreditsError(AdapterError):
    """Provider account has insufficient credits."""
    
    def __init__(self, message: str = "Insufficient credits on provider account") -> None:
        super().__init__(message, code="INSUFFICIENT_CREDITS", retryable=False)


class ModelUnavailableError(AdapterError):
    """Model is temporarily unavailable."""
    
    def __init__(self, message: str = "Model temporarily unavailable") -> None:
        super().__init__(message, code="MODEL_UNAVAILABLE", retryable=True)
