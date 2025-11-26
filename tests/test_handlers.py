"""Tests for bot handlers"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram.types import Message, User as TgUser, Chat
from src.bot.handlers import cmd_start, cmd_my_orders, handle_text_message


@pytest.fixture
def mock_message():
    """Mock Telegram message"""
    message = Mock(spec=Message)
    message.from_user = Mock(spec=TgUser)
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.from_user.first_name = "Test"
    message.from_user.language_code = "ru"
    message.chat = Mock(spec=Chat)
    message.chat.id = 123456789
    message.text = "/start"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_db_user():
    """Mock database user"""
    from src.services.database import User
    return User(
        id="user-123",
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        language_code="ru",
        balance=0.0,
        referrer_id=None,
        personal_ref_percent=20,
        is_admin=False,
        is_banned=False,
        warnings_count=0,
        do_not_disturb=False
    )


@pytest.fixture
def mock_bot():
    """Mock bot"""
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=Mock(username="test_bot"))
    return bot


@pytest.mark.asyncio
async def test_cmd_start_new_user(mock_message, mock_db_user, mock_bot):
    """Test /start command for new user"""
    with patch('src.bot.handlers.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_chat_history = AsyncMock(return_value=[])
        mock_db.save_chat_message = AsyncMock()
        mock_get_db.return_value = mock_db
        
        await cmd_start(mock_message, mock_db_user, mock_bot)
        
        mock_message.answer.assert_called_once()
        assert "Добро пожаловать" in mock_message.answer.call_args[0][0] or "Welcome" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_start_returning_user(mock_message, mock_db_user, mock_bot):
    """Test /start command for returning user"""
    with patch('src.bot.handlers.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_chat_history = AsyncMock(return_value=[{"role": "user", "content": "Hello"}])
        mock_db.save_chat_message = AsyncMock()
        mock_get_db.return_value = mock_db
        
        await cmd_start(mock_message, mock_db_user, mock_bot)
        
        mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_start_with_referral(mock_message, mock_db_user, mock_bot):
    """Test /start command with referral link"""
    mock_message.text = "/start ref_987654321"
    
    with patch('src.bot.handlers.get_database') as mock_get_db, \
         patch('asyncio.to_thread') as mock_thread:
        mock_db = Mock()
        mock_db.get_chat_history = AsyncMock(return_value=[])
        mock_db.save_chat_message = AsyncMock()
        mock_db.get_user_by_telegram_id = AsyncMock(return_value=Mock(id="referrer-123"))
        mock_thread.return_value = Mock()
        mock_get_db.return_value = mock_db
        
        await cmd_start(mock_message, mock_db_user, mock_bot)
        
        # Verify referral was processed
        mock_db.get_user_by_telegram_id.assert_called_with(987654321)


@pytest.mark.asyncio
async def test_cmd_my_orders(mock_message, mock_db_user):
    """Test /my_orders command"""
    with patch('src.bot.handlers.get_database') as mock_get_db:
        mock_db = Mock()
        mock_order = Mock()
        mock_order.id = "order-123"
        mock_order.product_id = "product-123"
        mock_order.amount = 300.0
        mock_order.status = "completed"
        mock_db.get_user_orders = AsyncMock(return_value=[mock_order])
        mock_db.get_product_by_id = AsyncMock(return_value=Mock(name="ChatGPT Plus"))
        mock_get_db.return_value = mock_db
        
        await cmd_my_orders(mock_message, mock_db_user)
        
        mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_my_orders_empty(mock_message, mock_db_user):
    """Test /my_orders when user has no orders"""
    with patch('src.bot.handlers.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_user_orders = AsyncMock(return_value=[])
        mock_get_db.return_value = mock_db
        
        await cmd_my_orders(mock_message, mock_db_user)
        
        mock_message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_message(mock_message, mock_db_user, mock_bot):
    """Test handling text message"""
    mock_message.text = "Нужен ChatGPT"
    
    with patch('src.bot.handlers.get_database') as mock_get_db, \
         patch('src.bot.handlers.AIConsultant') as mock_consultant, \
         patch('asyncio.create_task') as mock_task:
        mock_db = Mock()
        mock_db.save_chat_message = AsyncMock()
        mock_db.get_product_by_id = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_db
        
        mock_ai_response = Mock()
        mock_ai_response.text = "Вот что я нашел..."
        mock_ai_response.product_id = None
        mock_ai_response.show_shop = False
        
        mock_consultant_instance = Mock()
        mock_consultant_instance.get_response = AsyncMock(return_value=mock_ai_response)
        mock_consultant.return_value = mock_consultant_instance
        
        # Mock typing task
        mock_task.return_value = Mock()
        mock_task.return_value.cancel = Mock()
        
        await handle_text_message(mock_message, mock_db_user, mock_bot)
        
        mock_message.answer.assert_called_once()

