"""Payment Service - 1Plat Integration"""
import asyncio
import hashlib
import hmac
import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class PaymentService:
    """Payment service for 1Plat payment gateway"""
    
    def __init__(self):
        # 1Plat credentials
        # x-shop = Shop ID (Merchant ID) - видно рядом с названием магазина в ЛК
        # x-secret = Secret Key - в настройках магазина в ЛК
        self.onplat_shop_id = os.environ.get("ONEPLAT_SHOP_ID", "")  # x-shop (ID магазина, например #1182)
        self.onplat_secret_key = os.environ.get("ONEPLAT_SECRET_KEY", "")  # x-secret (секретный ключ)
        # Для обратной совместимости
        self.onplat_api_key = os.environ.get("ONEPLAT_API_KEY", "")
        self.onplat_merchant_id = os.environ.get("ONEPLAT_MERCHANT_ID", "")
        
        # Webhook URLs
        self.base_url = os.environ.get("WEBAPP_URL", "https://pvndora.app")
        
        # HTTP client (ленивая инициализация, общий для запросов)
        self._http_client: Optional[httpx.AsyncClient] = None

    # ==================== INTERNAL HELPERS ====================

    def _validate_config(self) -> Tuple[str, str, str]:
        """Проверка обязательных настроек и возврат shop_id, secret, base_url."""
        shop_id = self.onplat_shop_id or self.onplat_merchant_id or ""
        secret = self.onplat_secret_key or ""
        base_url = os.environ.get("ONEPLAT_API_URL", "https://1plat.cash")
        
        if not shop_id:
            raise ValueError("1Plat Shop ID (ONEPLAT_SHOP_ID или ONEPLAT_MERCHANT_ID) не настроен")
        if not secret:
            raise ValueError("1Plat Secret Key (ONEPLAT_SECRET_KEY) не настроен")
        return str(shop_id), secret, base_url.rstrip("/")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Ленивое создание общего httpx клиента с таймаутами."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0, read=10.0, write=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._http_client

    @staticmethod
    def _normalize_method(method: str) -> str:
        """Разрешённые методы оплаты."""
        allowed = {"card", "sbp", "qr", "crypto"}
        normalized = (method or "card").lower()
        if normalized not in allowed:
            raise ValueError(f"Unsupported payment method: {method}")
        return normalized

    @staticmethod
    def _prepare_email(user_email: str, user_id: int) -> str:
        """Возвращает валидный email или пустую строку (без заглушек)."""
        if user_email and "@" in user_email:
            return user_email
        return ""

    async def list_payment_methods(self) -> Dict[str, Any]:
        """Получить актуальные методы оплаты с 1Plat."""
        shop_id, secret, base_url = self._validate_config()
        api_url = f"{base_url}/api/merchant/payments/methods/by-api"
        client = await self._get_http_client()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-shop": shop_id,
            "x-secret": secret,
        }
        resp = await client.get(api_url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _save_payment_reference(self, order_id: str, pid_value: str) -> None:
        """Сохранить payment_id/guid в заказ (best-effort)."""
        if not order_id or not pid_value:
            return
        try:
            from src.services.database import get_database
            db = get_database()
            await asyncio.to_thread(
                lambda: db.client.table("orders")
                .update({"payment_id": pid_value})
                .eq("id", order_id)
                .execute()
            )
        except Exception as e:
            logger.warning("Failed to save payment reference for order %s: %s", order_id, e)

    async def _lookup_order_id(self, payment_id: Optional[str], guid: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Найти order_id и статус по payment_id/guid в БД."""
        order_id = None
        status = None
        try:
            if not payment_id and not guid:
                return None, None
            from src.services.database import get_database
            db = get_database()

            def _select_by(field: str, value: str):
                return db.client.table("orders").select("id,status").eq(field, value).limit(1).execute()

            if payment_id:
                result = await asyncio.to_thread(lambda: _select_by("payment_id", payment_id))
                if result.data:
                    order_id = result.data[0].get("id")
                    status = result.data[0].get("status")
            if not order_id and guid:
                result = await asyncio.to_thread(lambda: _select_by("payment_id", guid))
                if result.data:
                    order_id = result.data[0].get("id")
                    status = result.data[0].get("status")
        except Exception as e:
            logger.warning("Lookup by payment_id/guid failed: %s", e)
        return order_id, status
    
    async def create_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        method: str = "1plat",
        user_email: str = "",
        currency: str = "RUB",
        user_id: int = None,
        payment_method: str = "card",
    ) -> str:
        """
        Create payment and return payment URL.
        
        Args:
            order_id: Unique order ID
            amount: Payment amount
            product_name: Product name for description
            method: Payment method (only '1plat' supported)
            user_email: User email for receipts (not used for 1Plat)
            currency: Currency code
            user_id: User ID (required for 1Plat)
            
        Returns:
            Payment URL for redirect
        """
        if method in ("1plat", "onplat"):
            return await self._create_1plat_payment(
                order_id=order_id,
                amount=amount,
                product_name=product_name,
                currency=currency,
                user_id=user_id,
                user_email=user_email,
                method_override=payment_method,
            )
        raise ValueError(f"Unknown payment method: {method}. Only '1plat' is supported.")
    
    # ==================== 1PLAT ====================
    
    async def _create_1plat_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        user_id: int = None,
        user_email: str = "",
        method_override: str = "card",
    ) -> str:
        """
        Create 1Plat payment URL.
        
        Based on 1Plat API documentation:
        - Endpoint: POST /api/merchant/order/create/by-api
        - Base URL: https://1plat.cash
        - Authentication: x-shop (Shop ID) and x-secret (Secret Key) in headers
        - Обязательные поля: merchant_order_id, user_id, amount, method
        """
        shop_id, secret, base_url = self._validate_config()
        method = self._normalize_method(method_override)
        
        # user_id обязателен для 1Plat API (без эвристик)
        if user_id is None:
            raise ValueError("user_id обязателен для создания платежа")
            try:
            user_id_int = int(str(user_id))
            except Exception:
            raise ValueError("user_id должен быть числом (используйте telegram_id)")
        
        api_url = f"{base_url}/api/merchant/order/create/by-api"
        amount_kopecks = int(float(amount) * 100)
        
        payload = {
            "merchant_order_id": order_id,
            "user_id": user_id_int,
            "amount": amount_kopecks,
            "method": method,
        }
        email_value = self._prepare_email(user_email, user_id)
        if email_value:
            payload["email"] = email_value
        if method == "crypto":
            payload["currency"] = (currency or "RUB").upper()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-shop": shop_id,
            "x-secret": secret,
        }
        
        client = await self._get_http_client()
        try:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("error") or data.get("message") or "Unknown error"
                logger.error("1Plat API error for order %s: %s", order_id, error_msg)
                raise ValueError(f"1Plat API error: {error_msg}")
            
            logger.info("1Plat payment created for order %s", order_id)
            
            payment_url = data.get("url", "")
            if not payment_url:
                guid = data.get("guid", "")
                if guid:
                    payment_url = f"https://pay.1plat.cash/pay/{guid}"
                else:
                    logger.error("Payment URL not found in 1Plat response keys=%s", list(data.keys()))
                    raise ValueError(f"Payment URL not found in 1Plat response. Response: {data}")
            
            payment_info = data.get("payment", {})
            payment_id = payment_info.get("id") or data.get("payment_id")
            guid = data.get("guid", "")
            
            if payment_id or guid:
                pid_value = payment_id or guid
                await self._save_payment_reference(order_id, pid_value)
            
            return payment_url
        
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("message") or error_data.get("error") or str(error_data)
            except Exception:
                error_detail = e.response.text[:200]
            logger.error("1Plat API error %s: %s", e.response.status_code, error_detail)
            raise ValueError(f"1Plat API error: {error_detail or 'Unknown error'}")
        except httpx.RequestError as e:
            logger.error("1Plat network error: %s", e)
            raise ValueError(f"Failed to connect to 1Plat API: {str(e)}")
        except Exception:
            logger.exception("1Plat payment creation failed for order %s", order_id)
            raise
    
    async def verify_1plat_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify 1Plat webhook signature and extract order info.
        
        According to 1Plat documentation, callback format:
        {
            signature: '...',
            signature_v2: '...',
            payment_id: '123',
            guid: 'guid',
            merchant_id: '543',
            user_id: '1111',
            status: 0,
            amount: 100,
            amount_to_pay: 100,
            amount_to_shop: 85,
            expired: 'date',
        }
        
        Args:
            data: Webhook JSON data
            
        Returns:
            Dict with success status, order_id, amount, currency
        """
        try:
            shop_id, secret, base_url = self._validate_config()
            
            payment_id = data.get("payment_id") or data.get("paymentId")
            guid = data.get("guid")
            merchant_id = data.get("merchant_id") or ""
            currency = str(data.get("currency") or "RUB").upper()
            
            raw_amount = data.get("amount") or data.get("amount_to_shop") or data.get("amount_to_pay") or 0
            try:
                amount = float(raw_amount) / 100.0
            except (ValueError, TypeError):
                amount = 0.0
            
            order_id, order_status = await self._lookup_order_id(payment_id, guid)
            
            # Если не нашли в БД, используем guid для запроса к API 1Plat
            if not order_id and guid:
                try:
                    client = await self._get_http_client()
                    info_url = f"{base_url}/api/merchant/order/info/{guid}/by-api"
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "x-shop": shop_id,
                        "x-secret": secret,
                    }
                    
                    response = await client.get(info_url, headers=headers)
                    if response.status_code == 200:
                        info_data = response.json()
                        if info_data.get("success"):
                            payment = info_data.get("payment", {})
                            order_id = payment.get("merchant_order_id") or payment.get("order_id") or guid
                            if not amount and payment.get("amount"):
                                amount = float(payment.get("amount")) / 100.0
                            if payment.get("currency") and isinstance(payment.get("currency"), str):
                                currency = payment.get("currency").upper()
                            logger.info("1Plat: Found payment info by guid %s", guid)
                except Exception as e:
                    logger.warning("1Plat: Failed to get payment info by guid %s: %s", guid, e)
            
            # Если все еще не нашли, используем payment_id или guid как временный order_id
            if not order_id:
                order_id = payment_id or guid or ""
            
            if not order_id:
                logger.error("1Plat webhook: order_id not found. Keys: %s", list(data.keys()))
                return {"success": False, "error": "order_id not found in webhook data"}
            
            # Extract status - 1Plat использует числовые статусы: -2, -1, 0, 1, 2
            status = data.get("status") or data.get("payment_status") or data.get("state")
            try:
                status_val = int(status) if status is not None else None
            except (ValueError, TypeError):
                status_val = status
            
            # Idempotency: если заказ уже завершён, подтверждаем без повторной обработки
            processed_statuses = {"completed", "delivered", "paid", "fulfilled"}
            if order_status and str(order_status).lower() in processed_statuses:
                logger.info("1Plat webhook: order %s already processed with status %s", order_id, order_status)
                return {
                    "success": True,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": currency,
                }
            
            # Verify signatures if secret_key is provided
            received_signature = data.get("signature") or ""
            received_signature_v2 = data.get("signature_v2") or ""
            payload_from_body = data.get("payload") if isinstance(data.get("payload"), dict) else None
            
            verified = False
            
            # Method 1: Verify signature (HMAC-SHA256)
            if received_signature:
                try:
                    payload_for_sign_source = payload_from_body if payload_from_body is not None else data
                    payload_for_sign = {
                        k: v for k, v in payload_for_sign_source.items()
                        if k not in ["signature", "signature_v2"]
                    }
                    import json
                    payload_json = json.dumps(payload_for_sign, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
                    
                    expected_signature = hmac.new(
                        secret.encode("utf-8"),
                        payload_json.encode("utf-8"),
                        hashlib.sha256
                    ).hexdigest()
                    
                    if hmac.compare_digest(received_signature.lower(), expected_signature.lower()):
                        verified = True
                        logger.info("1Plat webhook: signature verified successfully for order %s", order_id)
                except Exception as e:
                    logger.warning("1Plat signature verification failed: %s", e)
            
            # Method 2: Verify signature_v2 (MD5)
            if not verified and received_signature_v2:
                try:
                    sign_amount = (
                        data.get("amount")
                        or data.get("amount_to_pay")
                        or data.get("amount_to_shop")
                        or 0
                    )
                    sign_string = f"{merchant_id}{sign_amount}{shop_id}{secret}"
                    expected_signature_v2 = hashlib.md5(sign_string.encode("utf-8")).hexdigest()
                    
                    if hmac.compare_digest(received_signature_v2.lower(), expected_signature_v2.lower()):
                        verified = True
                        logger.info("1Plat webhook: signature_v2 verified successfully for order %s", order_id)
                except Exception as e:
                    logger.warning("1Plat signature_v2 verification failed: %s", e)
            
            if not (received_signature or received_signature_v2):
                logger.error("1Plat webhook: signature is required but missing for order %s", order_id)
                return {"success": False, "error": "Missing signature"}

            if not verified:
                logger.error("1Plat webhook signature verification failed for order %s", order_id)
                return {"success": False, "error": "Invalid signature"}
            
            success_statuses = {1, 2}
            if status_val in success_statuses:
                logger.info("1Plat webhook: Payment successful for order %s, status %s", order_id, status_val)
                return {
                    "success": True,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": currency
                }
            
            logger.warning("1Plat webhook: Payment status '%s' for order %s", status, order_id)
            return {
                "success": False,
                "order_id": order_id,
                "error": f"Payment status: {status or 'unknown'}"
            }
                
        except Exception as e:
            logger.exception("1Plat webhook verification error")
            return {"success": False, "error": str(e)}
    
    # ==================== REFUNDS ====================
    
    async def process_refund(
        self,
        order_id: str,
        amount: float,
        method: str
    ) -> Dict[str, Any]:
        """
        Process refund for an order.
        
        For now, refunds are credited to user balance rather than
        actual payment refunds (simpler and faster).
        
        Args:
            order_id: Order ID to refund
            amount: Amount to refund
            method: Original payment method
            
        Returns:
            Refund result
        """
        if not order_id:
            return {"success": False, "error": "order_id is required"}
        if amount is None or amount <= 0:
            return {"success": False, "error": "amount must be positive"}
        
        try:
            from src.services.database import get_database
            db = get_database()
            
            # Fetch order to validate existence and ownership fields
            order = await db.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "Order not found"}
            
            status_lower = (getattr(order, "status", "") or "").lower()
            forbidden_statuses = {"refund_pending", "refunded", "cancelled", "rejected", "failed"}
            allowed_statuses = {"pending", "paid", "delivered", "fulfilled", "completed"}
            if status_lower in forbidden_statuses or (status_lower and allowed_statuses and status_lower not in allowed_statuses):
                return {"success": False, "error": f"Refund not allowed for status '{order.status}'"}
            
            order_amount = float(getattr(order, "amount", 0) or 0)
            if amount > order_amount:
                return {"success": False, "error": "amount exceeds order total"}
            
            if getattr(order, "refund_requested", False):
                return {"success": True, "method": "manual", "amount": float(amount), "message": "Refund already requested"}
            
            user_id = getattr(order, "user_id", None)
            if user_id:
                def _count_open():
                    result = db.client.table("orders").select("id", count="exact").eq("user_id", user_id).eq("refund_requested", True).execute()
                    return result.count or 0
                open_refunds = await asyncio.to_thread(_count_open)
                if open_refunds >= 3:
                    return {"success": False, "error": "Refund request limit reached"}
            
            # Best-effort: create support ticket for manual refund and mark the order flag
            await asyncio.to_thread(
                lambda: db.client.table("tickets").insert({
                    "user_id": getattr(order, "user_id", None),
                    "order_id": order_id,
                    "issue_type": "refund",
                    "description": f"Manual refund requested ({method}), amount={amount}",
                    "status": "open"
                }).execute()
            )
            
            await asyncio.to_thread(
                lambda: db.client.table("orders").update({
                    "refund_requested": True,
                    "status": "refund_pending"
                }).eq("id", order_id).execute()
            )
            
        return {
            "success": True,
                "method": "manual",
                "amount": float(amount),
                "message": "Refund queued for manual processing"
            }
        except Exception as e:
            logger.error("Failed to process refund %s: %s", order_id, e)
            return {"success": False, "error": str(e)}

    async def aclose(self) -> None:
        """Закрывает http-клиент, если он создавался."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

