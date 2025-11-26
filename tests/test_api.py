"""Tests for API endpoints"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from api.index import app


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_auth():
    """Mock Telegram auth"""
    return Mock(id=123456789, username="testuser", first_name="Test")


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_products(client):
    """Test getting products list"""
    with patch('api.index.get_database') as mock_get_db:
        mock_db = Mock()
        mock_product = Mock()
        mock_product.id = "product-123"
        mock_product.name = "ChatGPT Plus"
        mock_product.description = "Test"
        mock_product.price = 300.0
        mock_product.type = "shared"
        mock_product.status = "active"
        mock_product.warranty_hours = 24
        mock_product.stock_count = 5
        mock_db.get_products = AsyncMock(return_value=[mock_product])
        mock_db.get_product_rating = AsyncMock(return_value={"average": 4.5, "count": 10})
        mock_get_db.return_value = mock_db
        
        response = client.get("/api/products")
        assert response.status_code == 200
        assert len(response.json()) > 0


def test_get_product_by_id(client):
    """Test getting product by ID"""
    with patch('api.index.get_database') as mock_get_db:
        mock_db = Mock()
        mock_product = Mock()
        mock_product.id = "product-123"
        mock_product.name = "ChatGPT Plus"
        mock_product.description = "Test"
        mock_product.price = 300.0
        mock_product.type = "shared"
        mock_product.status = "active"
        mock_product.warranty_hours = 24
        mock_product.stock_count = 5
        mock_product.instructions = "Use VPN"
        mock_product.terms = "No refunds"
        
        mock_db.get_product_by_id = AsyncMock(return_value=mock_product)
        mock_db.get_product_rating = AsyncMock(return_value={"average": 4.5, "count": 10})
        mock_db.get_product_reviews = AsyncMock(return_value=[])
        mock_get_db.return_value = mock_db
        
        response = client.get("/api/products/product-123")
        assert response.status_code == 200
        assert response.json()["id"] == "product-123"


def test_get_product_not_found(client):
    """Test getting non-existent product"""
    with patch('api.index.get_database') as mock_get_db:
        mock_db = Mock()
        mock_db.get_product_by_id = AsyncMock(return_value=None)
        mock_get_db.return_value = mock_db
        
        response = client.get("/api/products/non-existent")
        assert response.status_code == 404


def test_create_order_unauthorized(client):
    """Test creating order without auth"""
    response = client.post("/api/orders", json={
        "product_id": "product-123"
    })
    assert response.status_code == 401


def test_submit_review_unauthorized(client):
    """Test submitting review without auth"""
    response = client.post("/api/reviews", json={
        "order_id": "order-123",
        "rating": 5
    })
    assert response.status_code == 401


def test_admin_endpoints_unauthorized(client):
    """Test admin endpoints without auth"""
    response = client.get("/api/admin/orders")
    assert response.status_code == 403


def test_admin_endpoints_authorized(client):
    """Test admin endpoints with auth"""
    with patch('api.index.get_database') as mock_get_db, \
         patch.dict('os.environ', {'ADMIN_API_KEY': 'test_admin_key'}):
        mock_db = Mock()
        mock_db.get_all_orders = AsyncMock(return_value=[])
        mock_get_db.return_value = mock_db
        
        response = client.get(
            "/api/admin/orders",
            headers={"Authorization": "Bearer test_admin_key"}
        )
        assert response.status_code == 200


def test_cron_endpoints_unauthorized(client):
    """Test cron endpoints without secret"""
    response = client.get("/api/cron/review-requests")
    assert response.status_code == 401


def test_cron_endpoints_authorized(client):
    """Test cron endpoints with secret"""
    with patch('api.index.get_database') as mock_get_db, \
         patch('api.index.NotificationService') as mock_notif, \
         patch.dict('os.environ', {'CRON_SECRET': 'test_secret'}):
        mock_db = Mock()
        mock_db.client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value.data = []
        mock_get_db.return_value = mock_db
        
        mock_notif_instance = Mock()
        mock_notif_instance.send_review_request = AsyncMock()
        mock_notif.return_value = mock_notif_instance
        
        response = client.get(
            "/api/cron/review-requests",
            headers={"Authorization": "Bearer test_secret"}
        )
        assert response.status_code == 200

