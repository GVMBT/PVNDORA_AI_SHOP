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
        
        # Freekassa credentials
        self.freekassa_merchant_id = os.environ.get("FREEKASSA_MERCHANT_ID", "")
        self.freekassa_secret_word_1 = os.environ.get("FREEKASSA_SECRET_WORD_1", "")
        self.freekassa_secret_word_2 = os.environ.get("FREEKASSA_SECRET_WORD_2", "")
        self.freekassa_api_url = os.environ.get("FREEKASSA_API_URL", "https://pay.freekassa.ru")
        
        # Rukassa credentials (lk.rukassa.io)
        self.rukassa_shop_id = os.environ.get("RUKASSA_SHOP_ID", "")
        self.rukassa_token = os.environ.get("RUKASSA_TOKEN", "")
        self.rukassa_api_url = os.environ.get("RUKASSA_API_URL", "https://lk.rukassa.io/api/v1")
        
        # CrystalPay credentials (docs.crystalpay.io)
        self.crystalpay_login = os.environ.get("CRYSTALPAY_LOGIN", "")
        self.crystalpay_secret = os.environ.get("CRYSTALPAY_SECRET", "")
        self.crystalpay_salt = os.environ.get("CRYSTALPAY_SALT", "")
        self.crystalpay_api_url = os.environ.get("CRYSTALPAY_API_URL", "https://api.crystalpay.io/v3")
        
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
    
    @staticmethod
    def _translate_1plat_error(error_msg: str) -> str:
        """Преобразует технические сообщения 1Plat в понятные для пользователя."""
        error_lower = error_msg.lower()
        
        # Известные ошибки и их переводы
        translations = {
            "не удалось получить реквизиты": "Не удалось получить реквизиты для оплаты. Попробуйте через минуту или выберите другой способ оплаты.",
            "подождите минуту": "Подождите минуту перед повторным созданием платежа.",
            "rate limit": "Слишком много запросов. Подождите минуту и попробуйте снова.",
            "too many requests": "Слишком много запросов. Подождите минуту и попробуйте снова.",
        }
        
        # Ищем совпадение в сообщении
        for key, translation in translations.items():
            if key in error_lower:
                return translation
        
        # Если это известная ошибка о реквизитах, но без точного совпадения
        if "реквизит" in error_lower or "details" in error_lower:
            return "Не удалось получить реквизиты для оплаты. Попробуйте через минуту или выберите другой способ оплаты."
        
        # Для остальных ошибок возвращаем общее сообщение
        return "Ошибка при создании платежа. Попробуйте через минуту или выберите другой способ оплаты."

    async def list_payment_methods(self) -> Dict[str, Any]:
        """
        Получить актуальные методы оплаты с 1Plat.
        
        Возвращает структуру для фронтенда:
        {
            "systems": [
                {"system_group": "card", "name": "Банковская карта"},
                {"system_group": "sbp", "name": "СБП"},
                ...
            ]
        }
        """
        shop_id, secret, base_url = self._validate_config()
        api_url = f"{base_url}/api/merchant/payments/methods/by-api"
        client = await self._get_http_client()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-shop": shop_id,
            "x-secret": secret,
        }
        try:
            resp = await client.get(api_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            # Логируем ответ для отладки
            logger.info("1Plat payment methods response: %s", data)
            
            # Нормализуем ответ для фронтенда
            # 1Plat может возвращать разные структуры, обрабатываем основные варианты
            systems = []
            
            # Вариант 1: data.systems (если уже в нужном формате)
            if isinstance(data, dict) and "systems" in data:
                systems = data["systems"]
            # Вариант 2: data - массив систем
            elif isinstance(data, list):
                systems = data
            # Вариант 3: data.data или data.result
            elif isinstance(data, dict):
                systems = data.get("data") or data.get("result") or data.get("systems") or []
            
            # Маппим на поддерживаемые методы
            # 1Plat может возвращать: card, sbp, qr, crypto или другие названия
            method_mapping = {
                "card": "card",
                "cards": "card",
                "bank_card": "card",
                "sbp": "sbp",
                "fast_payment": "sbp",
                "qr": "qr",
                "qrcode": "qr",
                "crypto": "crypto",
                "cryptocurrency": "crypto",
            }
            
            normalized_systems = []
            seen_methods = set()
            
            for system in systems:
                # Извлекаем system_group из разных возможных полей
                system_group = None
                if isinstance(system, dict):
                    system_group = (
                        system.get("system_group") or 
                        system.get("method") or 
                        system.get("type") or
                        system.get("id")
                    )
                elif isinstance(system, str):
                    system_group = system
                
                if system_group:
                    # Нормализуем название метода
                    normalized = method_mapping.get(str(system_group).lower(), str(system_group).lower())
                    
                    # Проверяем, что метод поддерживается
                    if normalized in {"card", "sbp", "qr", "crypto"} and normalized not in seen_methods:
                        normalized_systems.append({
                            "system_group": normalized,
                            "name": system.get("name") if isinstance(system, dict) else normalized.upper()
                        })
                        seen_methods.add(normalized)
            
            # Если ничего не получилось - возвращаем дефолтные методы
            if not normalized_systems:
                logger.warning("Could not parse 1Plat payment methods, using defaults")
                normalized_systems = [
                    {"system_group": "card", "name": "Банковская карта"},
                    {"system_group": "sbp", "name": "СБП"},
                    {"system_group": "qr", "name": "QR-код"},
                    {"system_group": "crypto", "name": "Криптовалюта"},
                ]
            
            return {"systems": normalized_systems}
            
        except Exception as e:
            logger.error("Failed to fetch 1Plat payment methods: %s", e)
            # Возвращаем дефолтные методы при ошибке
            return {
                "systems": [
                    {"system_group": "card", "name": "Банковская карта"},
                    {"system_group": "sbp", "name": "СБП"},
                    {"system_group": "qr", "name": "QR-код"},
                    {"system_group": "crypto", "name": "Криптовалюта"},
                ]
            }

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
        elif method == "freekassa":
            return await self._create_freekassa_payment(
                order_id=order_id,
                amount=amount,
                product_name=product_name,
                currency=currency,
                user_email=user_email,
            )
        elif method == "rukassa":
            return await self._create_rukassa_payment(
                order_id=order_id,
                amount=amount,
                product_name=product_name,
                currency=currency,
                user_email=user_email,
                user_id=user_id,
                payment_method=payment_method,
            )
        elif method == "crystalpay":
            return await self._create_crystalpay_payment(
                order_id=order_id,
                amount=amount,
                product_name=product_name,
                currency=currency,
                user_id=user_id,
            )
        raise ValueError(f"Unknown payment method: {method}. Supported: '1plat', 'freekassa', 'rukassa', 'crystalpay'.")

    # ==================== RUKASSA HELPERS ====================

    async def _rukassa_get_pay_info(self, payment_order_id: str) -> Dict[str, Any]:
        """
        Получить информацию о платеже Rukassa по нашему order_id (который мы передавали в create).
        Возвращает dict ответа API или кидает ValueError.
        """
        shop_id, token, api_url = self._validate_rukassa_config()
        payload = {
            "shop_id": int(shop_id),
            "token": token,
            "order_id": payment_order_id,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        client = await self._get_http_client()
        try:
            response = await client.post(
                f"{api_url}/getPayInfo",
                headers=headers,
                data=payload
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("Rukassa getPayInfo response for order_id=%s: %s", payment_order_id, data)
            if data.get("error"):
                msg = data.get("message") or f"Error code: {data.get('error')}"
                raise ValueError(msg)
            return data
        except Exception as e:
            raise ValueError(f"Rukassa getPayInfo failed: {e}")

    async def revoke_rukassa_payment(self, payment_order_id: str) -> Dict[str, Any]:
        """
        Отменяет незавершённый платеж Rukassa по нашему order_id, если он в статусе WAIT.
        Возвращает {success: bool, status: str, message: str}
        """
        try:
            info = await self._rukassa_get_pay_info(payment_order_id)
            status = str(info.get("status") or "").upper()
            payment_id_real = info.get("id")
            if status == "CANCEL":
                return {"success": True, "status": "CANCEL", "message": "Already cancelled"}
            if status == "PAID":
                return {"success": False, "status": "PAID", "message": "Payment already paid"}
            if not payment_id_real:
                return {"success": False, "status": status, "message": "Rukassa id not found"}

            # Только для WAIT пытаемся отменить
            shop_id, token, api_url = self._validate_rukassa_config()
            payload = {
                "shop_id": int(shop_id),
                "token": token,
                "id": payment_id_real,
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
            client = await self._get_http_client()
            resp = await client.post(f"{api_url}/revoke", headers=headers, data=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                msg = data.get("message") or f"Error code: {data.get('error')}"
                return {"success": False, "status": status, "message": msg}
            return {"success": True, "status": "CANCEL", "message": "Revoked"}
        except Exception as e:
            return {"success": False, "status": "ERROR", "message": str(e)}
    
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
        
        ВАЖНО: Поле method ОБЯЗАТЕЛЬНО для Host2Host.
        Если method не передан, платеж создается в статусе черновика (draft).
        
        Response структура зависит от метода:
        - card/sbp: payment.note содержит pan, bank, fio
        - qr: payment.note содержит qr, qr_img
        - crypto: payment.note содержит address, amount_in_currency, amount_rub, course
        
        Response всегда содержит:
        - url: https://pay.1plat.cash/pay/{guid} (или можно построить из guid)
        - guid: уникальный идентификатор платежа
        - payment: объект с информацией о платеже
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
        
        # Согласно документации 1Plat:
        # Для создания платежа Host2Host обязательно нужно передать поле method.
        # Если данное поле не передавать, то запрос отдаст платеж в статусе черновика.
        payload = {
            "merchant_order_id": order_id,
            "user_id": user_id_int,
            "amount": amount_kopecks,
            "method": method,  # ОБЯЗАТЕЛЬНО для Host2Host (card, sbp, qr, crypto)
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
        
        # Логируем запрос для отладки (без секретного ключа)
        logger.info("1Plat payment creation request for order %s: method=%s, amount=%s kopecks, user_id=%s", 
                   order_id, method, amount_kopecks, user_id_int)
        logger.debug("1Plat API URL: %s", api_url)
        logger.debug("1Plat payload (without secret): %s", {k: v for k, v in payload.items()})
        
        client = await self._get_http_client()
        try:
            response = await client.post(api_url, headers=headers, json=payload)
            logger.info("1Plat API response status: %s for order %s", response.status_code, order_id)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("error") or data.get("message") or "Unknown error"
                logger.error("1Plat API error for order %s: %s", order_id, error_msg)
                # Преобразуем технические сообщения в понятные для пользователя
                user_message = self._translate_1plat_error(error_msg)
                raise ValueError(user_message)
            
            logger.info("1Plat payment created for order %s, method=%s", order_id, method)
            
            # Извлекаем payment_url из response
            # Согласно документации: response.url или можно построить из guid
            payment_url = data.get("url", "")
            if not payment_url:
                guid = data.get("guid", "")
                if guid:
                    # Формируем URL согласно документации: https://pay.1plat.cash/pay/{guid}
                    payment_url = f"https://pay.1plat.cash/pay/{guid}"
                else:
                    logger.error("Payment URL not found in 1Plat response keys=%s", list(data.keys()))
                    raise ValueError(f"Payment URL not found in 1Plat response. Response: {data}")
            
            # Извлекаем информацию о платеже для логирования и сохранения
            payment_info = data.get("payment", {})
            payment_id = payment_info.get("id") or data.get("payment_id")
            guid = data.get("guid", "")
            
            # Логируем payment.note для отладки (содержит реквизиты/QR/крипто-адрес)
            payment_note = payment_info.get("note", {})
            if payment_note:
                # Логируем структуру note без чувствительных данных
                note_keys = list(payment_note.keys())
                logger.info("1Plat payment note structure for order %s: %s", order_id, note_keys)
                # Для отладки можно логировать тип метода из note
                if "pan" in payment_note:
                    logger.debug("Payment method: card/sbp (has pan)")
                elif "qr" in payment_note or "qr_img" in payment_note:
                    logger.debug("Payment method: qr (has qr)")
                elif "address" in payment_note:
                    logger.debug("Payment method: crypto (has address)")
            
            # Проверяем статус платежа
            payment_status = payment_info.get("status")
            if payment_status is not None:
                # Статус 0 = pending (ожидает оплаты) - это нормально
                # Если статус черновика - значит method не был передан
                if payment_status == -1:  # Черновик (draft)
                    logger.warning("1Plat payment created in draft status for order %s. Method may not have been passed correctly.", order_id)
                else:
                    logger.info("1Plat payment status for order %s: %s", order_id, payment_status)
            
            # Сохраняем payment_id или guid для связи с заказом
            if payment_id or guid:
                pid_value = payment_id or guid
                await self._save_payment_reference(order_id, pid_value)
            
            return payment_url
        
        except httpx.HTTPStatusError as e:
            # Логируем полный ответ для отладки
            try:
                error_data = e.response.json()
                error_detail = error_data.get("message") or error_data.get("error") or str(error_data)
                logger.error("1Plat API error %s for order %s, method=%s. Full response: %s", 
                           e.response.status_code, order_id, method, error_data)
            except Exception:
                error_detail = e.response.text[:200]
                logger.error("1Plat API error %s for order %s, method=%s. Response text: %s", 
                           e.response.status_code, order_id, method, error_detail)
            # Преобразуем технические сообщения в понятные для пользователя
            user_message = self._translate_1plat_error(error_detail or 'Unknown error')
            raise ValueError(user_message)
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
    
    # ==================== FREEKASSA ====================
    
    def _validate_freekassa_config(self) -> Tuple[str, str, str]:
        """Проверка обязательных настроек Freekassa и возврат merchant_id, secret_word_1, api_url."""
        merchant_id = self.freekassa_merchant_id or ""
        secret_word_1 = self.freekassa_secret_word_1 or ""
        api_url = self.freekassa_api_url.rstrip("/")
        
        if not merchant_id:
            raise ValueError("Freekassa Merchant ID (FREEKASSA_MERCHANT_ID) не настроен")
        if not secret_word_1:
            raise ValueError("Freekassa Secret Word 1 (FREEKASSA_SECRET_WORD_1) не настроен")
        return merchant_id, secret_word_1, api_url
    
    async def _create_freekassa_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        user_email: str = "",
    ) -> str:
        """
        Create Freekassa payment URL.
        
        Based on Freekassa API documentation:
        - Payment URL: https://pay.freekassa.ru/?m={MERCHANT_ID}&oa={AMOUNT}&o={MERCHANT_ORDER_ID}&s={SIGN}&us_field1={optional}
        - Signature: md5(MERCHANT_ID:AMOUNT:SECRET_WORD_1:MERCHANT_ORDER_ID)
        """
        merchant_id, secret_word_1, api_url = self._validate_freekassa_config()
        
        # Amount in rubles (Freekassa expects rubles)
        amount_rub = float(amount)
        
        # Generate signature: md5(MERCHANT_ID:AMOUNT:SECRET_WORD_1:MERCHANT_ORDER_ID)
        sign_string = f"{merchant_id}:{amount_rub}:{secret_word_1}:{order_id}"
        signature = hashlib.md5(sign_string.encode("utf-8")).hexdigest()
        
        # Build payment URL
        params = {
            "m": merchant_id,
            "oa": str(amount_rub),
            "o": order_id,
            "s": signature,
        }
        
        # Optional fields
        if user_email:
            params["us_field1"] = user_email
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        payment_url = f"{api_url}/?{query_string}"
        
        logger.info("Freekassa payment URL created for order %s", order_id)
        return payment_url
    
    async def verify_freekassa_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify Freekassa webhook signature and extract order info.
        
        Webhook parameters:
        - MERCHANT_ID: Merchant ID
        - AMOUNT: Payment amount
        - MERCHANT_ORDER_ID: Order ID
        - SIGN: Signature (md5(MERCHANT_ID:AMOUNT:SECRET_WORD_2:MERCHANT_ORDER_ID))
        - intid: Internal transaction ID
        - P_EMAIL: User email (optional)
        - CUR_ID: Currency ID (optional)
        
        Returns:
            {"success": bool, "order_id": str, "amount": float, "currency": str, "error": str}
        """
        try:
            merchant_id = str(data.get("MERCHANT_ID", "")).strip()
            amount_str = str(data.get("AMOUNT", "")).strip()
            order_id = str(data.get("MERCHANT_ORDER_ID", "")).strip()
            received_sign = str(data.get("SIGN", "")).strip().lower()
            
            if not merchant_id or not amount_str or not order_id or not received_sign:
                logger.error("Freekassa webhook: Missing required fields")
                return {"success": False, "error": "Missing required fields"}
            
            # Validate merchant ID matches
            expected_merchant_id = self.freekassa_merchant_id
            if merchant_id != expected_merchant_id:
                logger.error("Freekassa webhook: Merchant ID mismatch. Expected %s, got %s", expected_merchant_id, merchant_id)
                return {"success": False, "error": "Invalid merchant ID"}
            
            # Verify signature using SECRET_WORD_2 (for webhooks)
            # Signature: md5(MERCHANT_ID:AMOUNT:SECRET_WORD_2:MERCHANT_ORDER_ID)
            secret_word_2 = self.freekassa_secret_word_2 or ""
            if not secret_word_2:
                logger.error("Freekassa webhook: SECRET_WORD_2 not configured")
                return {"success": False, "error": "SECRET_WORD_2 not configured"}
            
            sign_string = f"{merchant_id}:{amount_str}:{secret_word_2}:{order_id}"
            expected_sign = hashlib.md5(sign_string.encode("utf-8")).hexdigest().lower()
            
            if not hmac.compare_digest(received_sign, expected_sign):
                logger.error("Freekassa webhook: Signature verification failed for order %s", order_id)
                return {"success": False, "error": "Invalid signature"}
            
            amount = float(amount_str)
            currency = data.get("CUR_ID", "RUB")  # Default to RUB
            
            logger.info("Freekassa webhook verified successfully for order %s, amount %s", order_id, amount)
            return {
                "success": True,
                "order_id": order_id,
                "amount": amount,
                "currency": str(currency)
            }
                
        except Exception as e:
            logger.exception("Freekassa webhook verification error")
            return {"success": False, "error": str(e)}
    
    # ==================== RUKASSA (lk.rukassa.io) ====================
    
    def _validate_rukassa_config(self) -> Tuple[str, str, str]:
        """Проверка обязательных настроек Rukassa и возврат shop_id, token, api_url."""
        shop_id = self.rukassa_shop_id or ""
        token = self.rukassa_token or ""
        api_url = self.rukassa_api_url.rstrip("/")
        
        if not shop_id:
            raise ValueError("Rukassa Shop ID (RUKASSA_SHOP_ID) не настроен")
        if not token:
            raise ValueError("Rukassa Token (RUKASSA_TOKEN) не настроен")
        return shop_id, token, api_url
    
    async def _create_rukassa_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        user_email: str = "",
        user_id: int = None,
        payment_method: str = None,
    ) -> str:
        """
        Create Rukassa payment via API.
        
        Based on Rukassa API documentation (lk.rukassa.io/api/v1):
        - Endpoint: POST /create
        - Required: shop_id, order_id, amount, token
        - Optional: data, method, list, currency, user_code, json
        
        Response: id, hash, url (or error, message on failure)
        """
        shop_id, token, api_url = self._validate_rukassa_config()
        
        # Amount in rubles (float)
        amount_rub = float(amount)
        
        # Data object to pass with webhook callback
        callback_data = {
            "product_name": product_name[:100] if product_name else "",
        }
        if user_email:
            callback_data["email"] = user_email
        
        # API request payload (form data style)
        import json as json_module
        payload = {
            "shop_id": int(shop_id),
            "order_id": order_id,
            "amount": amount_rub,
            "token": token,
            "data": json_module.dumps(callback_data),
            "currency": currency or "RUB",
        }
        
        # user_code for Anti-Fraud (use telegram_id or order_id)
        if user_id:
            payload["user_code"] = str(user_id)
        else:
            payload["user_code"] = str(order_id)
        
        # Payment method (card, card_azn, skinpay, yandexmoney, crypta, sbp, clever, sbp_qr)
        if payment_method:
            method_map = {
                "card": "card",
                "card_azn": "card_azn",
                "sbp": "sbp",
                "sbp_qr": "sbp_qr",
                "qr": "sbp_qr",
                "crypto": "crypta",
                "crypta": "crypta",
                "skinpay": "skinpay",
                "yandexmoney": "yandexmoney",
                "clever": "clever",
            }
            rukassa_method = method_map.get(payment_method.lower(), payment_method)
            payload["method"] = rukassa_method
        
        # H2H mode - get payment details for custom form
        use_h2h = os.environ.get("RUKASSA_H2H_MODE", "false").lower() == "true"
        if use_h2h:
            payload["json"] = True
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        
        logger.info("Rukassa payment creation for order %s: amount=%s %s, user_code=%s", 
                   order_id, amount_rub, currency, payload.get("user_code"))
        
        client = await self._get_http_client()
        try:
            # POST to /create endpoint with form data
            response = await client.post(
                f"{api_url}/create",
                headers=headers,
                data=payload  # form-urlencoded
            )
            logger.info("Rukassa API response status: %s for order %s", response.status_code, order_id)
            
            data = response.json()
            logger.debug("Rukassa API response: %s", data)
            
            # Check for errors
            if data.get("error"):
                error_code = data.get("error")
                error_msg = data.get("message") or f"Error code: {error_code}"
                logger.error("Rukassa API error for order %s: code=%s, msg=%s", order_id, error_code, error_msg)
                
                # Перевод кодов ошибок Rukassa в понятные сообщения
                error_messages = {
                    "300": "Платёжная система заморожена. Обратитесь в поддержку Rukassa.",
                    "client is frozen": "Платёжная система заморожена. Обратитесь в поддержку.",
                    "method not available": "Выбранный способ оплаты недоступен.",
                    "method is disabled": "Выбранный способ оплаты отключен.",
                    "insufficient balance": "Недостаточный баланс на счёте магазина.",
                    "invalid amount": "Неверная сумма платежа.",
                    "invalid token": "Ошибка авторизации платёжной системы.",
                }
                
                # Ищем подходящее сообщение
                user_message = None
                error_lower = (str(error_code) + " " + str(error_msg)).lower()
                for key, msg in error_messages.items():
                    if key.lower() in error_lower:
                        user_message = msg
                        break
                
                if not user_message:
                    user_message = f"Ошибка платёжной системы: {error_msg}"
                
                raise ValueError(user_message)
            
            # Extract payment data from response
            payment_id = data.get("id")
            payment_hash = data.get("hash")
            payment_url = data.get("url")
            
            # H2H mode returns card details instead of URL
            if use_h2h and data.get("card"):
                # Build custom form URL with payment details
                from urllib.parse import urlencode
                form_params = {
                    "card": data.get("card", ""),
                    "bank": data.get("bank", ""),
                    "receiver": data.get("receiver", ""),
                    "amount": data.get("amount", amount_rub),
                    "date": data.get("date", ""),
                    "order_id": order_id,
                    "hash": payment_hash or "",
                    "id": payment_id or "",
                }
                payment_url = f"{self.base_url}/payment/form?{urlencode(form_params)}"
                logger.info("Rukassa H2H payment: order=%s, card=%s, bank=%s", 
                           order_id, data.get("card", "")[:4] + "****", data.get("bank"))
            elif not payment_url:
                logger.error("Rukassa: URL not in response. Keys: %s", list(data.keys()))
                raise ValueError("Payment URL not found in Rukassa response")
            
            # Save payment reference
            if payment_id or payment_hash:
                await self._save_payment_reference(order_id, str(payment_id or payment_hash))
            
            logger.info("Rukassa payment created: order=%s, id=%s, hash=%s", order_id, payment_id, payment_hash)
            return payment_url
            
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_detail = error_data.get("message") or error_data.get("error") or str(error_data)
            except Exception:
                error_detail = e.response.text[:200]
            logger.error("Rukassa API error %s for order %s: %s", e.response.status_code, order_id, error_detail)
            raise ValueError(f"Rukassa API error: {error_detail}")
        except httpx.RequestError as e:
            logger.error("Rukassa network error: %s", e)
            raise ValueError(f"Failed to connect to Rukassa API: {str(e)}")
    
    async def verify_rukassa_webhook(self, data: Dict[str, Any], signature: str = None) -> Dict[str, Any]:
        """
        Verify Rukassa webhook signature and extract order info.
        
        Webhook parameters from Rukassa (POST):
        - id (Int): Payment ID in Rukassa system
        - order_id (Int): Order ID in our system  
        - amount (Float): Payment amount
        - in_amount (Float): Amount actually paid by client
        - data (Json): Custom data passed during payment creation
        - createdDateTime (String): Payment creation time
        - status (String): PAID if successful
        
        Signature verification:
        - Header: Signature (HTTP_SIGNATURE)
        - Formula: hmac_sha256(id + '|' + createdDateTime + '|' + amount, token)
        
        Returns:
            {"success": bool, "order_id": str, "amount": float, "currency": str, "error": str}
        """
        try:
            # Extract required fields
            payment_id = str(data.get("id", "")).strip()
            order_id = str(data.get("order_id", "")).strip()
            amount_str = str(data.get("amount", "")).strip()
            in_amount_str = str(data.get("in_amount", "")).strip()
            status = str(data.get("status", "")).strip().upper()
            created_datetime = str(data.get("createdDateTime", "")).strip()
            
            # Log webhook data
            logger.info("Rukassa webhook: id=%s, order_id=%s, amount=%s, in_amount=%s, status=%s", 
                       payment_id, order_id, amount_str, in_amount_str, status)
            
            if not order_id:
                logger.error("Rukassa webhook: order_id not found")
                return {"success": False, "error": "order_id not found"}
            
            if not payment_id:
                logger.error("Rukassa webhook: payment id not found")
                return {"success": False, "error": "payment id not found"}
            
            # Verify signature if provided
            # Signature = hmac_sha256(id + '|' + createdDateTime + '|' + amount, token)
            token = self.rukassa_token or ""
            if signature and token:
                sign_string = f"{payment_id}|{created_datetime}|{amount_str}"
                expected_signature = hmac.new(
                    token.encode("utf-8"),
                    sign_string.encode("utf-8"),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature.lower(), expected_signature.lower()):
                    logger.error("Rukassa webhook: Signature mismatch for order %s", order_id)
                    logger.debug("Rukassa signature: received=%s, expected=%s", signature, expected_signature)
                    return {"success": False, "error": "Invalid signature"}
                
                logger.info("Rukassa webhook: Signature verified for order %s", order_id)
            elif not signature:
                logger.warning("Rukassa webhook: No signature provided for order %s", order_id)
            
            # Check payment status - PAID means successful
            if status != "PAID":
                logger.warning("Rukassa webhook: Payment status '%s' for order %s", status, order_id)
                return {"success": False, "error": f"Payment not successful. Status: {status}"}
            
            # Parse amounts
            try:
                amount = float(amount_str) if amount_str else 0.0
                in_amount = float(in_amount_str) if in_amount_str else amount
            except (ValueError, TypeError):
                amount = 0.0
                in_amount = 0.0
            
            # Verify paid amount >= expected amount
            if in_amount < amount:
                logger.warning("Rukassa webhook: Underpayment for order %s. Expected %s, got %s", 
                             order_id, amount, in_amount)
                return {"success": False, "error": f"Underpayment. Expected {amount}, received {in_amount}"}
            
            # Parse custom data if provided
            custom_data = data.get("data")
            if custom_data and isinstance(custom_data, str):
                try:
                    import html
                    import json as json_module
                    custom_data = json_module.loads(html.unescape(custom_data))
                except Exception:
                    pass
            
            logger.info("Rukassa webhook verified: order=%s, amount=%s, in_amount=%s", 
                       order_id, amount, in_amount)
            return {
                "success": True,
                "order_id": order_id,
                "amount": amount,
                "in_amount": in_amount,
                "currency": "RUB",
                "custom_data": custom_data
            }
                
        except Exception as e:
            logger.exception("Rukassa webhook verification error")
            return {"success": False, "error": str(e)}
    
    # ==================== CRYSTALPAY (docs.crystalpay.io) ====================
    
    def _validate_crystalpay_config(self) -> Tuple[str, str, str, str]:
        """Проверка обязательных настроек CrystalPay и возврат login, secret, salt, api_url."""
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
    
    async def _create_crystalpay_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        user_id: int = None,
    ) -> str:
        """
        Create CrystalPay invoice via API.
        
        Based on CrystalPay API documentation (docs.crystalpay.io/v3):
        - Endpoint: POST /invoice/create/
        - Required: auth_login, auth_secret, amount, type, lifetime
        - Optional: currency, required_method, description, extra, redirect_url, callback_url
        
        Response: id, url, rub_amount, currency, amount, type
        """
        login, secret, salt, api_url = self._validate_crystalpay_config()
        
        # Amount in rubles (CrystalPay expects float)
        amount_rub = float(amount)
        
        # Build callback URL
        callback_url = f"{self.base_url}/api/webhook/crystalpay"
        
        # API request payload (JSON)
        # lifetime = 15 минут для синхронизации с резервом товара
        payload = {
            "auth_login": login,
            "auth_secret": secret,
            "amount": amount_rub,
            "type": "purchase",  # purchase для покупки товара, topup для пополнения
            "lifetime": 15,  # время жизни инвойса в минутах (синхронизировано с резервом)
            "currency": currency or "RUB",
            "description": product_name[:200] if product_name else "Оплата заказа",
            "extra": order_id,  # сохраняем order_id для callback
            "callback_url": callback_url,
            "redirect_url": f"{self.base_url}/payment/result?order_id={order_id}",
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        logger.info("CrystalPay payment creation for order %s: amount=%s %s", 
                   order_id, amount_rub, currency)
        
        client = await self._get_http_client()
        try:
            response = await client.post(
                f"{api_url}/invoice/create/",
                headers=headers,
                json=payload
            )
            logger.info("CrystalPay API response status: %s for order %s", response.status_code, order_id)
            
            data = response.json()
            logger.debug("CrystalPay API response: %s", data)
            
            # Check for errors
            if data.get("error"):
                errors = data.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Unknown error"
                logger.error("CrystalPay API error for order %s: %s", order_id, error_msg)
                raise ValueError(f"CrystalPay error: {error_msg}")
            
            # Extract payment data from response
            invoice_id = data.get("id")
            payment_url = data.get("url")
            
            if not payment_url:
                logger.error("CrystalPay: URL not in response. Keys: %s", list(data.keys()))
                raise ValueError("Payment URL not found in CrystalPay response")
            
            # Save payment reference (invoice_id)
            if invoice_id:
                await self._save_payment_reference(order_id, str(invoice_id))
            
            logger.info("CrystalPay payment created: order=%s, invoice_id=%s", order_id, invoice_id)
            return payment_url
            
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_detail = ", ".join(error_data.get("errors", [])) or str(error_data)
            except Exception:
                error_detail = e.response.text[:200]
            logger.error("CrystalPay API error %s for order %s: %s", e.response.status_code, order_id, error_detail)
            raise ValueError(f"CrystalPay API error: {error_detail}")
        except httpx.RequestError as e:
            logger.error("CrystalPay network error: %s", e)
            raise ValueError(f"Failed to connect to CrystalPay API: {str(e)}")
    
    async def verify_crystalpay_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify CrystalPay webhook signature and extract order info.
        
        CrystalPay callback format (POST JSON):
        - signature: sha1(id + ':' + salt)
        - id: Invoice ID
        - state: payed, notpayed, processing, cancelled, etc.
        - extra: Our order_id (passed during creation)
        - amount, rub_amount, currency, etc.
        
        Returns:
            {"success": bool, "order_id": str, "amount": float, "currency": str, "error": str}
        """
        try:
            # Extract required fields
            invoice_id = str(data.get("id", "")).strip()
            received_signature = str(data.get("signature", "")).strip().lower()
            state = str(data.get("state", "")).strip().lower()
            order_id = str(data.get("extra", "")).strip()  # Our order_id stored in extra
            
            # Amount handling
            amount_str = str(data.get("amount", "0")).strip()
            rub_amount_str = str(data.get("rub_amount", "0")).strip()
            currency = str(data.get("currency", "RUB")).strip().upper()
            
            # Log webhook data
            logger.info("CrystalPay webhook: id=%s, state=%s, order_id=%s, amount=%s %s", 
                       invoice_id, state, order_id, amount_str, currency)
            
            if not invoice_id:
                logger.error("CrystalPay webhook: invoice id not found")
                return {"success": False, "error": "invoice id not found"}
            
            # If order_id not in extra, try to lookup by invoice_id in our DB
            if not order_id:
                found_order_id, _ = await self._lookup_order_id(invoice_id, None)
                if found_order_id:
                    order_id = found_order_id
                else:
                    logger.error("CrystalPay webhook: order_id not found in extra or DB")
                    return {"success": False, "error": "order_id not found"}
            
            # Verify signature: sha1(id + ':' + salt)
            salt = self.crystalpay_salt or ""
            if received_signature and salt:
                sign_string = f"{invoice_id}:{salt}"
                expected_signature = hashlib.sha1(sign_string.encode()).hexdigest().lower()
                
                if not hmac.compare_digest(received_signature, expected_signature):
                    logger.error("CrystalPay webhook: Signature mismatch for invoice %s", invoice_id)
                    logger.debug("CrystalPay signature: received=%s, expected=%s", received_signature, expected_signature)
                    return {"success": False, "error": "Invalid signature"}
                
                logger.info("CrystalPay webhook: Signature verified for invoice %s", invoice_id)
            elif not received_signature:
                logger.warning("CrystalPay webhook: No signature provided for invoice %s", invoice_id)
            
            # Check payment state - "payed" means successful
            if state != "payed":
                logger.warning("CrystalPay webhook: Payment state '%s' for order %s", state, order_id)
                return {"success": False, "error": f"Payment not successful. State: {state}"}
            
            # Parse amounts
            try:
                amount = float(amount_str) if amount_str else 0.0
                rub_amount = float(rub_amount_str) if rub_amount_str else amount
            except (ValueError, TypeError):
                amount = 0.0
                rub_amount = 0.0
            
            logger.info("CrystalPay webhook verified: order=%s, amount=%s %s, rub_amount=%s", 
                       order_id, amount, currency, rub_amount)
            return {
                "success": True,
                "order_id": order_id,
                "amount": amount,
                "rub_amount": rub_amount,
                "currency": currency,
                "invoice_id": invoice_id
            }
                
        except Exception as e:
            logger.exception("CrystalPay webhook verification error")
            return {"success": False, "error": str(e)}
    
    async def get_crystalpay_invoice_info(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get CrystalPay invoice info by ID.
        
        Useful for checking payment status manually.
        """
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
            response = await client.post(
                f"{api_url}/invoice/info/",
                headers=headers,
                json=payload
            )
            data = response.json()
            
            if data.get("error"):
                errors = data.get("errors", [])
                error_msg = ", ".join(errors) if errors else "Unknown error"
                raise ValueError(f"CrystalPay error: {error_msg}")
            
            return data
        except Exception as e:
            logger.error("CrystalPay get invoice info error: %s", e)
            raise
    
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

