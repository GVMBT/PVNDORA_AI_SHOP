"""Payment Service - CrystalPay Integration
All methods use async/await with supabase-py v2 (no asyncio.to_thread).
"""

import hashlib
import hmac
import logging
import os
from typing import Any, cast

import httpx

from core.services.money import to_float

logger = logging.getLogger(__name__)


class PaymentService:
    """Payment service for CrystalPay payment gateway"""

    def __init__(self):
        # CrystalPay credentials (docs.crystalpay.io)
        self.crystalpay_login = os.environ.get("CRYSTALPAY_LOGIN", "")
        self.crystalpay_secret = os.environ.get("CRYSTALPAY_SECRET", "")
        self.crystalpay_salt = os.environ.get("CRYSTALPAY_SALT", "")
        self.crystalpay_api_url = os.environ.get(
            "CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3"
        )

        # Webhook URLs
        self.base_url = os.environ.get("WEBAPP_URL", "https://pvndora.app")

        # HTTP client (lazy init)
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy creation of shared httpx client with timeouts."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0, read=10.0, write=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._http_client

    def _validate_crystalpay_config(self) -> tuple[str, str, str, str]:
        """Validate required CrystalPay settings."""
        login = self.crystalpay_login or ""
        secret = self.crystalpay_secret or ""
        salt = self.crystalpay_salt or ""
        api_url = self.crystalpay_api_url.rstrip("/")

        if not login:
            raise ValueError("CrystalPay Login (CRYSTALPAY_LOGIN) не настроен")
        if not secret:
            raise ValueError("CrystalPay Secret (CRYSTALPAY_SECRET) не настроен")
        if not salt:
            raise ValueError("CrystalPay Salt (CRYSTALPAY_SALT) не настроен")
        return login, secret, salt, api_url

    async def _save_payment_reference(self, order_id: str, pid_value: str) -> None:
        """Save payment_id to order (best-effort)."""
        if not order_id or not pid_value:
            return
        try:
            from core.services.database import get_database

            db = get_database()
            await db.client.table("orders").update({"payment_id": pid_value}).eq(
                "id", order_id
            ).execute()
        except Exception as e:
            logger.warning("Failed to save payment reference for order %s: %s", order_id, e)

    async def _lookup_order_id(self, payment_id: str | None) -> tuple[str | None, str | None]:
        """Find order_id and status by payment_id in DB."""
        if not payment_id:
            return None, None
        try:
            from core.services.database import get_database

            db = get_database()
            result = (
                await db.client.table("orders")
                .select("id,status")
                .eq("payment_id", payment_id)
                .limit(1)
                .execute()
            )
            if result.data and isinstance(result.data, list):
                row = result.data[0]
                if isinstance(row, dict):
                    return row.get("id"), row.get("status")
        except Exception as e:
            logger.warning("Lookup by payment_id failed: %s", e)
        return None, None

    # ==================== MAIN API ====================

    async def create_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        method: str = "crystalpay",
        currency: str = "RUB",
        _user_id: int | None = None,  # Kept for API compatibility
        is_telegram_miniapp: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create payment and return payment URL.

        Args:
            order_id: Unique order ID
            amount: Payment amount
            product_name: Product name for description
            method: Payment method (only 'crystalpay' supported)
            currency: Currency code (RUB, USD, etc.)
            user_id: User ID (telegram_id)
            is_telegram_miniapp: Whether request is from TMA

        Returns:
            Dict with payment_url, invoice_id
        """
        # Only CrystalPay is supported
        if method and method not in ("crystalpay", "card", "crypto"):
            logger.warning("Unknown payment method '%s', using crystalpay", method)

        return await self._create_crystalpay_payment(
            order_id=order_id,
            amount=amount,
            product_name=product_name,
            currency=currency,
            is_telegram_miniapp=is_telegram_miniapp,
        )

    async def create_invoice(
        self,
        amount: float,
        order_id: str,
        description: str = "",
        user_telegram_id: int | None = None,
        currency: str = "RUB",
    ) -> dict[str, Any]:
        """
        Alias for create_payment for backward compatibility.
        """
        return await self.create_payment(
            order_id=order_id,
            amount=amount,
            product_name=description,
            currency=currency,
            user_id=user_telegram_id,
        )

    async def list_payment_methods(self) -> dict[str, Any]:
        """
        Return available payment methods.
        CrystalPay supports card, crypto, etc.
        """
        return {
            "systems": [
                {"system_group": "card", "name": "Банковская карта"},
                {"system_group": "crypto", "name": "Криптовалюта"},
            ]
        }

    # ==================== CRYSTALPAY ====================

    async def _create_crystalpay_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        _user_id: int | None = None,
        is_telegram_miniapp: bool = True,
    ) -> dict[str, Any]:
        """
        Create CrystalPay invoice via API.

        Based on CrystalPay API documentation (docs.crystalpay.io/v3):
        - Endpoint: POST /invoice/create/
        - Required: auth_login, auth_secret, amount, type, lifetime
        - Optional: currency, description, extra, redirect_url, callback_url

        Response: id, url, rub_amount, currency, amount, type
        """
        login, secret, salt, api_url = self._validate_crystalpay_config()

        payment_amount = to_float(amount)
        payment_currency = (currency or "RUB").upper()

        # Build callback URL
        callback_url = f"{self.base_url}/api/webhook/crystalpay"
        # Redirect URL - Use Telegram Deep Link to return user to Mini App with fresh initData
        # This opens Telegram app directly instead of browser, preserving auth session
        bot_username = os.environ.get("BOT_USERNAME", "pvndora_ai_bot")
        redirect_url = f"https://t.me/{bot_username}?startapp=payresult_{order_id}"

        # TEST mode
        test_mode = os.environ.get("CRYSTALPAY_TEST_MODE", "false").lower() == "true"
        required_method = "TEST" if test_mode else None

        # Description: CrystalPay limit 64 chars
        safe_description = (product_name or f"Order {order_id}")[:60]

        payload = {
            "auth_login": login,
            "auth_secret": secret,
            "amount": payment_amount,
            "type": "purchase",
            "lifetime": 15,  # minutes
            "currency": payment_currency,
            "description": safe_description,
            "extra": order_id,
            "callback_url": callback_url,
            "redirect_url": redirect_url,
        }
        if required_method:
            payload["required_method"] = required_method

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.info(
            "CrystalPay payment creation for order %s: amount=%s %s",
            order_id,
            payment_amount,
            payment_currency,
        )

        client = await self._get_http_client()
        try:
            response = await client.post(
                f"{api_url}/invoice/create/", headers=headers, json=payload
            )
            logger.info(
                "CrystalPay API response status: %s for order %s", response.status_code, order_id
            )

            data = response.json()

            if not isinstance(data, dict):
                return {}

            if data.get("error"):
                errors = data.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Unknown error"
                logger.error("CrystalPay API error for order %s: %s", order_id, error_msg)
                raise ValueError(f"CrystalPay error: {error_msg}")

            invoice_id = data.get("id")
            payment_url = data.get("url")

            if not payment_url:
                logger.error("CrystalPay: URL not in response. Keys: %s", list(data.keys()))
                raise ValueError("Payment URL not found in CrystalPay response")

            # Save payment reference
            if invoice_id:
                await self._save_payment_reference(order_id, str(invoice_id))

            logger.info("CrystalPay payment created: order=%s, invoice_id=%s", order_id, invoice_id)
            return {
                "payment_url": payment_url,
                "url": payment_url,
                "invoice_id": invoice_id,
                "id": invoice_id,
            }

        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_detail = ", ".join(error_data.get("errors", [])) or str(error_data)
            except Exception:
                error_detail = e.response.text[:200]
            logger.exception(
                "CrystalPay API error %s for order %s: %s",
                e.response.status_code,
                order_id,
                error_detail,
            )
            raise ValueError(f"CrystalPay API error: {error_detail}")
        except httpx.RequestError as e:
            logger.exception("CrystalPay network error")
            raise ValueError(f"Failed to connect to CrystalPay API: {e!s}")

    async def create_crystalpay_payment_topup(
        self,
        topup_id: str,
        user_id: str,
        amount: float,
        currency: str = "RUB",
        is_telegram_miniapp: bool = True,
    ) -> dict[str, Any]:
        """
        Create CrystalPay invoice for balance top-up.
        """
        login, secret, salt, api_url = self._validate_crystalpay_config()

        payment_amount = to_float(amount)
        payment_currency = currency.upper()

        callback_url = f"{self.base_url}/api/webhook/crystalpay/topup"
        # Redirect URL - Use Telegram Deep Link to return user to Mini App with fresh initData
        bot_username = os.environ.get("BOT_USERNAME", "pvndora_ai_bot")
        redirect_url = f"https://t.me/{bot_username}?startapp=topup_{topup_id}"

        test_mode = os.environ.get("CRYSTALPAY_TEST_MODE", "false").lower() == "true"
        required_method = "TEST" if test_mode else None

        if payment_currency == "USD":
            safe_description = f"Balance top-up: ${payment_amount:.2f}"[:60]
        else:
            safe_description = f"Balance top-up: {payment_amount:.0f} {payment_currency}"[:60]

        payload = {
            "auth_login": login,
            "auth_secret": secret,
            "amount": payment_amount,
            "type": "topup",
            "lifetime": 30,
            "currency": payment_currency,
            "description": safe_description,
            "extra": f"topup_{topup_id}",
            "callback_url": callback_url,
            "redirect_url": redirect_url,
        }
        if required_method:
            payload["required_method"] = required_method

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.info(
            "CrystalPay TOPUP: topup_id=%s, amount=%s %s, user=%s",
            topup_id,
            payment_amount,
            payment_currency,
            user_id,
        )

        client = await self._get_http_client()
        try:
            response = await client.post(
                f"{api_url}/invoice/create/", headers=headers, json=payload
            )

            data = response.json()

            if not isinstance(data, dict):
                return {}

            if data.get("error"):
                errors = data.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Unknown error"
                logger.error("CrystalPay TOPUP error: %s", error_msg)
                raise ValueError(f"CrystalPay error: {error_msg}")

            payment_url = data.get("url")
            invoice_id = data.get("id")

            if not payment_url:
                raise ValueError("Payment URL not found in CrystalPay response")

            logger.info(
                "CrystalPay TOPUP created: topup_id=%s, invoice_id=%s", topup_id, invoice_id
            )
            return {
                "payment_url": payment_url,
                "invoice_id": invoice_id,
            }

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:200]
            logger.exception(
                "CrystalPay TOPUP API error %s: %s", e.response.status_code, error_detail
            )
            raise ValueError(f"CrystalPay API error: {error_detail}")
        except httpx.RequestError as e:
            logger.exception("CrystalPay TOPUP network error")
            raise ValueError(f"Failed to connect to CrystalPay API: {e!s}")

    def _extract_webhook_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract and normalize webhook data (reduces cognitive complexity)."""
        return {
            "invoice_id": str(data.get("id", "")).strip(),
            "received_signature": str(data.get("signature", "")).strip().lower(),
            "state": str(data.get("state", "")).strip().lower(),
            "order_id": str(data.get("extra", "")).strip(),
            "amount_str": str(data.get("amount", "0")).strip(),
            "rub_amount_str": str(data.get("rub_amount", "0")).strip(),
            "currency": str(data.get("currency", "RUB")).strip().upper(),
        }

    async def _resolve_order_id(self, order_id: str, invoice_id: str) -> tuple[str | None, str]:
        """Resolve order_id from extra or lookup (reduces cognitive complexity)."""
        if order_id:
            return order_id, ""
        found_order_id, _ = await self._lookup_order_id(invoice_id)
        if found_order_id:
            return found_order_id, ""
        logger.error("CrystalPay webhook: order_id not found")
        return None, "order_id not found"

    def _verify_signature(self, invoice_id: str, received_signature: str, salt: str) -> tuple[bool, str]:
        """Verify webhook signature (reduces cognitive complexity)."""
        if not received_signature:
            return True, ""  # No signature to verify

        if not salt:
            logger.warning("CrystalPay webhook: Signature provided but CRYSTALPAY_SALT not configured!")
            return True, ""  # Continue without verification

        sign_string = f"{invoice_id}:{salt}"
        # nosec B324 - SHA1 required by CrystalPay API for signature verification
        expected_signature = hashlib.sha1(sign_string.encode()).hexdigest().lower()

        if not hmac.compare_digest(received_signature, expected_signature):
            logger.error("CrystalPay webhook: Signature mismatch for invoice %s", invoice_id)
            return False, "Invalid signature"

        logger.info("CrystalPay webhook: Signature verified for invoice %s", invoice_id)
        return True, ""

    def _parse_amounts(self, amount_str: str, rub_amount_str: str) -> tuple[float, float]:
        """Parse amount strings to floats (reduces cognitive complexity)."""
        try:
            amount = to_float(amount_str) if amount_str else 0.0
            rub_amount = to_float(rub_amount_str) if rub_amount_str else amount
            return amount, rub_amount
        except (ValueError, TypeError):
            return 0.0, 0.0

    async def verify_crystalpay_webhook(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Verify CrystalPay webhook signature and extract order info.

        CrystalPay callback format (POST JSON):
        - signature: sha1(id + ':' + salt)
        - id: Invoice ID
        - state: payed, notpayed, processing, cancelled, etc.
        - extra: Our order_id (passed during creation)
        - amount, rub_amount, currency, etc.
        """
        try:
            webhook_data = self._extract_webhook_data(data)
            invoice_id = webhook_data["invoice_id"]
            received_signature = webhook_data["received_signature"]
            state = webhook_data["state"]
            order_id = webhook_data["order_id"]
            amount_str = webhook_data["amount_str"]
            rub_amount_str = webhook_data["rub_amount_str"]
            currency = webhook_data["currency"]

            logger.info(
                "CrystalPay webhook: id=%s, state=%s, order_id=%s, amount=%s %s",
                invoice_id,
                state,
                order_id,
                amount_str,
                currency,
            )

            if not invoice_id:
                logger.error("CrystalPay webhook: invoice id not found")
                return {"success": False, "error": "invoice id not found"}

            order_id, error = await self._resolve_order_id(order_id, invoice_id)
            if not order_id:
                return {"success": False, "error": error}

            salt = self.crystalpay_salt or ""
            is_valid, sig_error = self._verify_signature(invoice_id, received_signature, salt)
            if not is_valid:
                return {"success": False, "error": sig_error}

            if state != "payed":
                logger.warning("CrystalPay webhook: Payment state '%s' for order %s", state, order_id)
                return {"success": False, "error": f"Payment not successful. State: {state}"}

            amount, rub_amount = self._parse_amounts(amount_str, rub_amount_str)

            logger.info(
                "CrystalPay webhook verified: order=%s, amount=%s %s", order_id, amount, currency
            )
            return {
                "success": True,
                "order_id": order_id,
                "amount": amount,
                "rub_amount": rub_amount,
                "currency": currency,
                "invoice_id": invoice_id,
            }

        except Exception as e:
            logger.exception("CrystalPay webhook verification error")
            return {"success": False, "error": str(e)}

    async def get_crystalpay_invoice_info(self, invoice_id: str) -> dict[str, Any]:
        """Get CrystalPay invoice info by ID."""
        login, secret, salt, api_url = self._validate_crystalpay_config()

        payload = {
            "auth_login": login,
            "auth_secret": secret,
            "id": invoice_id,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        client = await self._get_http_client()
        try:
            response = await client.post(f"{api_url}/invoice/info/", headers=headers, json=payload)
            data = response.json()

            if not isinstance(data, dict):
                return {}

            if data.get("error"):
                errors = data.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Unknown error"
                raise ValueError(f"CrystalPay error: {error_msg}")

            return data
        except Exception:
            logger.exception("CrystalPay get invoice info error")
            raise

    # ==================== REFUNDS ====================

    async def process_refund(
        self, order_id: str, amount: float, method: str = "crystalpay"
    ) -> dict[str, Any]:
        """
        Process refund for an order.
        Refunds are credited to user balance (manual processing).
        """
        if not order_id:
            return {"success": False, "error": "order_id is required"}
        if amount is None or amount <= 0:
            return {"success": False, "error": "amount must be positive"}

        try:
            from core.services.database import get_database

            db = get_database()

            order = await db.get_order_by_id(order_id)
            if not order:
                return {"success": False, "error": "Order not found"}

            status_lower = (getattr(order, "status", "") or "").lower()
            forbidden_statuses = {"refunded", "cancelled"}
            if status_lower in forbidden_statuses:
                return {
                    "success": False,
                    "error": f"Refund not allowed for status '{order.status}'",
                }

            order_amount = to_float(getattr(order, "amount", 0) or 0)
            if to_float(amount) > order_amount:
                return {"success": False, "error": "amount exceeds order total"}

            if getattr(order, "refund_requested", False):
                return {
                    "success": True,
                    "method": "manual",
                    "amount": to_float(amount),
                    "message": "Refund already requested",
                }

            user_id = getattr(order, "user_id", None)
            if user_id:
                result = (
                    await db.client.table("orders")
                    .select("id", count=cast(Any, "exact"))
                    .eq("user_id", user_id)
                    .eq("refund_requested", True)
                    .execute()
                )
                open_refunds = result.count or 0
                if open_refunds >= 3:
                    return {"success": False, "error": "Refund request limit reached"}

            # Create support ticket for manual refund
            await db.client.table("tickets").insert(
                {
                    "user_id": getattr(order, "user_id", None),
                    "order_id": order_id,
                    "issue_type": "refund",
                    "description": f"Manual refund requested, amount={amount}",
                    "status": "open",
                }
            ).execute()

            await db.client.table("orders").update(
                {"refund_requested": True, "status": "refund_pending"}
            ).eq("id", order_id).execute()

            return {
                "success": True,
                "method": "manual",
                "amount": to_float(amount),
                "message": "Refund queued for manual processing",
            }
        except Exception as e:
            logger.exception("Failed to process refund %s", order_id)
            return {"success": False, "error": str(e)}

    async def aclose(self) -> None:
        """Close http client if created."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
