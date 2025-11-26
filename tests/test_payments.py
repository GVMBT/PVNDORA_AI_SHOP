"""Tests for payment processing"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.payments import PaymentService


@pytest.fixture
def mock_payment_service():
    """Mock payment service"""
    service = PaymentService()
    service.aaio_client = Mock()
    service.stripe_client = Mock()
    return service


@pytest.mark.asyncio
async def test_create_aaio_payment(mock_payment_service):
    """Test creating AAIO payment"""
    mock_order = Mock()
    mock_order.id = "order-123"
    mock_order.amount = 300.0
    mock_order.user_id = "user-123"
    
    mock_payment_service.aaio_client.create_payment = Mock(return_value="https://aaio.ru/pay/123")
    
    payment_url = await mock_payment_service.create_aaio_payment(mock_order)
    
    assert payment_url is not None
    assert "aaio.ru" in payment_url


@pytest.mark.asyncio
async def test_verify_aaio_callback(mock_payment_service):
    """Test verifying AAIO callback signature"""
    callback_data = {
        "order_id": "order-123",
        "status": "paid",
        "amount": "300.00",
        "sign": "valid_signature"
    }
    
    mock_payment_service.aaio_client.verify_signature = Mock(return_value=True)
    
    is_valid = await mock_payment_service.verify_aaio_callback(callback_data)
    
    assert is_valid is True


@pytest.mark.asyncio
async def test_create_stripe_checkout(mock_payment_service):
    """Test creating Stripe checkout session"""
    mock_order = Mock()
    mock_order.id = "order-123"
    mock_order.amount = 30.0  # USD
    
    mock_session = Mock()
    mock_session.url = "https://checkout.stripe.com/session/123"
    mock_payment_service.stripe_client.checkout.Session.create = Mock(return_value=mock_session)
    
    checkout_url = await mock_payment_service.create_stripe_checkout(mock_order)
    
    assert checkout_url is not None
    assert "stripe.com" in checkout_url


@pytest.mark.asyncio
async def test_verify_stripe_webhook(mock_payment_service):
    """Test verifying Stripe webhook signature"""
    payload = b'{"type": "checkout.session.completed"}'
    signature = "valid_signature"
    
    mock_payment_service.stripe_client.Webhook.construct_event = Mock(return_value={
        "type": "checkout.session.completed",
        "data": {"object": {"id": "session-123"}}
    })
    
    event = await mock_payment_service.verify_stripe_webhook(payload, signature)
    
    assert event is not None
    assert event["type"] == "checkout.session.completed"

