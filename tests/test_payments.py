"""Tests for payment processing"""
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from src.services.payments import PaymentService


@pytest.fixture
def payment_service():
    """Payment service with test credentials"""
    with patch.dict(os.environ, {
        "AAIO_MERCHANT_ID": "test_merchant",
        "AAIO_SECRET_KEY": "test_secret",
        "STRIPE_SECRET_KEY": "sk_test_123",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "WEBAPP_URL": "https://test.vercel.app"
    }):
        service = PaymentService()
        return service


@pytest.mark.asyncio
async def test_create_aaio_payment(payment_service):
    """Test creating AAIO payment"""
    payment_url = await payment_service._create_aaio_payment(
        order_id="order-123",
        amount=300.0,
        product_name="ChatGPT Plus",
        currency="RUB"
    )
    
    assert payment_url is not None
    assert "aaio.so" in payment_url
    assert "order-123" in payment_url
    assert "300" in payment_url


@pytest.mark.asyncio
async def test_verify_aaio_callback_valid(payment_service):
    """Test verifying valid AAIO callback signature"""
    import hashlib
    
    # Generate valid signature
    sign_string = f"{payment_service.aaio_merchant_id}:300.00:RUB:{payment_service.aaio_secret_key}:order-123"
    valid_sign = hashlib.sha256(sign_string.encode()).hexdigest()
    
    callback_data = {
        "merchant_id": payment_service.aaio_merchant_id,
        "order_id": "order-123",
        "amount": "300.00",
        "currency": "RUB",
        "sign": valid_sign
    }
    
    result = await payment_service.verify_aaio_callback(callback_data)
    
    assert result["success"] is True
    assert result["order_id"] == "order-123"


@pytest.mark.asyncio
async def test_verify_aaio_callback_invalid_signature(payment_service):
    """Test verifying invalid AAIO callback signature"""
    callback_data = {
        "merchant_id": payment_service.aaio_merchant_id,
        "order_id": "order-123",
        "amount": "300.00",
        "currency": "RUB",
        "sign": "invalid_signature"
    }
    
    result = await payment_service.verify_aaio_callback(callback_data)
    
    assert result["success"] is False
    assert "signature" in result["error"].lower()


@pytest.mark.asyncio
async def test_create_payment_aaio_method(payment_service):
    """Test creating payment with AAIO method"""
    payment_url = await payment_service.create_payment(
        order_id="order-123",
        amount=300.0,
        product_name="ChatGPT Plus",
        method="aaio"
    )
    
    assert payment_url is not None
    assert "aaio.so" in payment_url


@pytest.mark.asyncio
async def test_create_payment_stripe_method(payment_service):
    """Test creating payment with Stripe method"""
    with patch('stripe.checkout.Session.create') as mock_stripe:
        mock_session = Mock()
        mock_session.url = "https://checkout.stripe.com/session/123"
        mock_stripe.return_value = mock_session
        
        payment_url = await payment_service.create_payment(
            order_id="order-123",
            amount=30.0,
            product_name="ChatGPT Plus",
            method="stripe",
            currency="USD"
        )
        
        assert payment_url is not None
        assert "stripe.com" in payment_url

