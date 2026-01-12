"""Internationalization System"""

import json
from pathlib import Path
from typing import Any

# Supported languages with their names
SUPPORTED_LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "uk": "Українська",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "tr": "Türkçe",
    "ar": "العربية",
    "hi": "हिन्दी",
}

# Default language
DEFAULT_LANGUAGE = "en"

# Cache for loaded translations
_translations: dict[str, dict[str, Any]] = {}


def _get_locales_path() -> Path:
    """Get path to locales directory"""
    # Try different paths for Vercel and local development
    paths = [
        Path(__file__).parent.parent.parent / "locales",  # From core/i18n/
        Path("locales"),  # Current directory
        Path("/var/task/locales"),  # Vercel
    ]

    for path in paths:
        if path.exists():
            return path

    # Create default path if none exists
    default_path = Path(__file__).parent.parent.parent / "locales"
    default_path.mkdir(exist_ok=True)
    return default_path


def _load_translations(lang: str) -> dict[str, Any]:
    """Load translations for a language"""
    if lang in _translations:
        return _translations[lang]

    locales_path = _get_locales_path()
    file_path = locales_path / f"{lang}.json"

    if not file_path.exists():
        # Fallback to English
        if lang != DEFAULT_LANGUAGE:
            return _load_translations(DEFAULT_LANGUAGE)
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                _translations[lang] = data
                return _translations[lang]
            return {}
    except Exception:
        return {}


def get_text(key: str, lang: str = DEFAULT_LANGUAGE, default: str | None = None, **kwargs) -> str:
    """
    Get translated text by key.

    Args:
        key: Translation key (e.g., "welcome", "btn_buy", "faq.title")
        lang: Language code (e.g., "ru", "en")
        default: Default value if key not found (instead of returning key)
        **kwargs: Variables to format into the string

    Returns:
        Translated string or key/default if not found
    """
    # Normalize language code (take first part: "ru-RU" -> "ru")
    lang = lang.split("-")[0].lower() if lang else DEFAULT_LANGUAGE

    # Check if language is supported
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    translations = _load_translations(lang)

    # Support nested keys with dot notation (e.g., "faq.title")
    text: Any = None
    if "." in key:
        keys = key.split(".")
        current_val: Any = translations
        try:
            for k in keys:
                current_val = current_val[k]
            text = current_val
        except (KeyError, TypeError):
            text = None
    else:
        text = translations.get(key)

    # Fallback to English if key not found
    if text is None and lang != DEFAULT_LANGUAGE:
        eng_translations = _load_translations(DEFAULT_LANGUAGE)
        if "." in key:
            keys = key.split(".")
            current_val = eng_translations
            try:
                for k in keys:
                    current_val = current_val[k]
                text = current_val
            except (KeyError, TypeError):
                text = None
        else:
            text = eng_translations.get(key)

    # Return default or key if still not found
    if text is None:
        return default if default is not None else key

    # If it's still a dict (partial key), return the key or default
    if not isinstance(text, str):
        return default if default is not None else key

    # Format with kwargs if provided
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, AttributeError):
            return text

    return text


def get_all_texts(lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Get all translations for a language"""
    lang = lang.split("-")[0].lower() if lang else DEFAULT_LANGUAGE
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return _load_translations(lang)


def detect_language(language_code: str | None) -> str:
    """
    Detect and normalize language code from Telegram.

    Args:
        language_code: Language code from Telegram user

    Returns:
        Normalized supported language code
    """
    if not language_code:
        return DEFAULT_LANGUAGE

    # Normalize: "ru-RU" -> "ru"
    lang = language_code.split("-")[0].lower()

    # Return if supported, otherwise default
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def reload_translations() -> None:
    """Clear translation cache and reload"""
    global _translations
    _translations = {}
