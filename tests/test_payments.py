import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional

import httpx
import pytest  # type: ignore[reportMissingImports]

from core.services.payments import PaymentService
from core.services import payments as payments_module


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, mapping: Dict[str, Dict[str, Any]], updates: List):
        self.mapping = mapping
        self.updates = updates
        self._mode: Optional[str] = None
        self._value: Optional[str] = None
        self._update_data: Optional[Dict[str, Any]] = None

    def select(self, *_):
        self._mode = "select"
        return self

    def update(self, data: Dict[str, Any]):
        self._mode = "update"
        self._update_data = data
        return self

    def eq(self, _field: str, value: str):
        self._value = value
        return self

    def limit(self, *_):
        return self

    def execute(self):
        if self._mode == "select":
            record = self.mapping.get(self._value)
            return _Result([record] if record else [])
        if self._mode == "update":
            self.updates.append((self._value, self._update_data))
            return _Result([])
        return _Result([])


class _FakeClient:
    def __init__(self, mapping: Dict[str, Dict[str, Any]], updates: List):
        self.mapping = mapping
        self.updates = updates

    def table(self, name: str):
        assert name == "orders"
        return _FakeTable(self.mapping, self.updates)


class _FakeDB:
    def __init__(self, mapping: Dict[str, Dict[str, Any]], updates: List):
        self.client = _FakeClient(mapping, updates)


def _make_signature(payload: Dict[str, Any], secret: str) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
    return hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_verify_webhook_valid_signature(monkeypatch):
    secret = "secret-key"
    mapping = {"pid-1": {"id": "order-123", "status": "pending"}}
    updates: List = []

    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, updates))

    payload = {
        "payment_id": "pid-1",
        "guid": "guid-1",
        "status": 1,
        "amount": 1000,
        "currency": "rub",
    }
    payload["signature"] = _make_signature({k: v for k, v in payload.items() if k != "signature"}, secret)

    result = await service.verify_1plat_webhook(payload)

    assert result["success"] is True
    assert result["order_id"] == "order-123"
    assert result["amount"] == 10.0
    assert result["currency"] == "RUB"


@pytest.mark.asyncio
async def test_verify_webhook_invalid_signature(monkeypatch):
    secret = "secret-key"
    mapping = {"pid-2": {"id": "order-234", "status": "pending"}}
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, []))

    payload = {
        "payment_id": "pid-2",
        "guid": "guid-2",
        "status": 1,
        "amount": 500,
        "currency": "RUB",
        "signature": "bad",
    }

    result = await service.verify_1plat_webhook(payload)

    assert result["success"] is False
    assert result["error"] == "Invalid signature"


@pytest.mark.asyncio
async def test_verify_webhook_missing_signature(monkeypatch):
    secret = "secret-key"
    mapping = {"pid-2": {"id": "order-234", "status": "pending"}}
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, []))

    payload = {
        "payment_id": "pid-2",
        "guid": "guid-2",
        "status": 1,
        "amount": 500,
        "currency": "RUB",
    }

    result = await service.verify_1plat_webhook(payload)

    assert result["success"] is False
    assert result["error"] == "Missing signature"


@pytest.mark.asyncio
async def test_verify_webhook_missing_amount(monkeypatch):
    secret = "secret-key"
    mapping = {"pid-3": {"id": "order-345", "status": "pending"}}
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, []))

    payload = {
        "payment_id": "pid-3",
        "guid": "guid-3",
        "status": 1,
        "currency": "RUB",
    }
    payload["signature"] = _make_signature({k: v for k, v in payload.items() if k != "signature"}, secret)

    result = await service.verify_1plat_webhook(payload)

    assert result["success"] is True
    assert result["amount"] == 0.0


@pytest.mark.asyncio
async def test_verify_webhook_idempotent_on_completed(monkeypatch):
    secret = "secret-key"
    mapping = {"pid-4": {"id": "order-456", "status": "completed"}}
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, []))

    payload = {
        "payment_id": "pid-4",
        "guid": "guid-4",
        "status": 1,
        "amount": 500,
        "currency": "RUB",
    }
    payload["signature"] = _make_signature({k: v for k, v in payload.items() if k != "signature"}, secret)

    result = await service.verify_1plat_webhook(payload)

    assert result["success"] is True
    assert result["order_id"] == "order-456"


@pytest.mark.asyncio
async def test_create_payment_uses_method_and_currency(monkeypatch):
    secret = "secret-key"
    mapping: Dict[str, Dict[str, Any]] = {}
    updates: List = []
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()
    monkeypatch.setattr(payments_module, "get_database", lambda: _FakeDB(mapping, updates))

    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["method"] == "crypto"
        assert body["currency"] == "USD"
        return httpx.Response(
            200,
            json={
                "success": True,
                "url": "https://pay.test/ok",
                "guid": "guid-crypto",
                "payment": {"id": "pay-crypto"},
            },
        )

    transport = httpx.MockTransport(handler)
    service._http_client = httpx.AsyncClient(transport=transport)

    url = await service.create_payment(
        order_id="order-789",
        amount=12.5,
        product_name="Test",
        method="1plat",
        user_email="",
        currency="USD",
        user_id=111,
        payment_method="crypto",
    )

    assert url == "https://pay.test/ok"
    assert updates and updates[0][0] == "order-789"

    await service._http_client.aclose()


@pytest.mark.asyncio
async def test_create_payment_requires_config(monkeypatch):
    monkeypatch.delenv("ONEPLAT_SHOP_ID", raising=False)
    monkeypatch.delenv("ONEPLAT_SECRET_KEY", raising=False)
    service = PaymentService()

    with pytest.raises(ValueError):
        await service.create_payment(
            order_id="order-000",
            amount=1.0,
            product_name="Test",
            method="1plat",
            user_email="test@example.com",
            currency="RUB",
        )


@pytest.mark.asyncio
async def test_create_payment_requires_user_id(monkeypatch):
    secret = "secret-key"
    monkeypatch.setenv("ONEPLAT_SHOP_ID", "1182")
    monkeypatch.setenv("ONEPLAT_SECRET_KEY", secret)
    service = PaymentService()

    with pytest.raises(ValueError):
        await service.create_payment(
            order_id="order-000",
            amount=1.0,
            product_name="Test",
            method="1plat",
            user_email="test@example.com",
            currency="RUB",
        )
