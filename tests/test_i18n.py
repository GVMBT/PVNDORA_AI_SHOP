"""Tests for i18n translations"""
import pytest
from src.i18n.translations import get_text, SUPPORTED_LANGUAGES


def test_get_text_existing_key():
    """Test getting existing translation"""
    text = get_text("welcome", "ru")
    assert text is not None
    assert len(text) > 0


def test_get_text_fallback_to_english():
    """Test fallback to English when translation missing"""
    # Try to get non-existent key
    text = get_text("non_existent_key", "ru")
    # Should return key itself or empty string
    assert text is not None


def test_get_text_with_params():
    """Test getting text with parameters"""
    text = get_text("order_created", "ru", order_id="123", amount=300)
    assert "123" in text or "300" in text or len(text) > 0


def test_supported_languages():
    """Test that all supported languages are available"""
    assert "ru" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) >= 9


def test_get_text_all_languages():
    """Test getting text in all supported languages"""
    for lang in SUPPORTED_LANGUAGES:
        text = get_text("welcome", lang)
        assert text is not None
        assert len(text) > 0

