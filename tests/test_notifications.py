"""Tests for notification service"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.notifications import NotificationService


@pytest.fixture
def mock_notification_service():
    """Mock notification service"""
    service = NotificationService()
    service._bot_instance = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_send_order_credentials(mock_notification_service):
    """Test sending order credentials to user"""
    mock_order = Mock()
    mock_order.id = "order-123"
    mock_order.user_id = "user-123"
    mock_order.product_id = "product-123"
    
    mock_stock_item = Mock()
    mock_stock_item.content = "login:password"
    
    with patch('src.services.notifications.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_order_by_id = AsyncMock(return_value=mock_order)
        mock_db.get_stock_item = AsyncMock(return_value=mock_stock_item)
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"telegram_id": 123456789, "language_code": "ru"}]
        mock_get_db.return_value = mock_db
        
        await mock_notification_service.send_order_credentials("order-123")
        
        # Verify message was sent
        mock_notification_service._bot_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_notify_supplier(mock_notification_service):
    """Test notifying supplier about sale"""
    with patch('src.services.notifications.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"telegram_id": 987654321, "name": "Supplier"}]
        mock_get_db.return_value = mock_db
        
        await mock_notification_service._notify_supplier(
            "supplier-123",
            "ChatGPT Plus",
            300.0
        )
        
        # Verify message was sent to supplier
        mock_notification_service._bot_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_review_request(mock_notification_service):
    """Test sending review request"""
    mock_order = Mock()
    mock_order.id = "order-123"
    mock_order.status = "completed"
    mock_order.user_id = "user-123"
    
    with patch('src.services.notifications.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_order_by_id = AsyncMock(return_value=mock_order)
        mock_db.client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"telegram_id": 123456789, "language_code": "ru"}]
        mock_get_db.return_value = mock_db
        
        await mock_notification_service.send_review_request("order-123")
        
        # Verify message was sent
        mock_notification_service._bot_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_expiration_reminder(mock_notification_service):
    """Test sending expiration reminder"""
    await mock_notification_service.send_expiration_reminder(
        telegram_id=123456789,
        product_name="ChatGPT Plus",
        days_left=3,
        language="ru"
    )
    
    # Verify message was sent
    mock_notification_service._bot_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_waitlist_notification(mock_notification_service):
    """Test sending waitlist notification"""
    await mock_notification_service.send_waitlist_notification(
        telegram_id=123456789,
        product_name="ChatGPT Plus",
        language="ru"
    )
    
    # Verify message was sent
    mock_notification_service._bot_instance.send_message.assert_called_once()

