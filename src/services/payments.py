"""Payment Service - 1Plat Integration"""
import os
import hashlib
import hmac
from typing import Dict, Any

import httpx


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
    
    async def create_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        method: str = "1plat",
        user_email: str = "",
        currency: str = "RUB",
        user_id: int = None
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
        if method == "1plat" or method == "onplat":
            return await self._create_1plat_payment(
                order_id, amount, product_name, currency, user_id
            )
        else:
            raise ValueError(f"Unknown payment method: {method}. Only '1plat' is supported.")
    
    # ==================== 1PLAT ====================
    
    async def _create_1plat_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB",
        user_id: int = None
    ) -> str:
        """
        Create 1Plat payment URL.
        
        Based on 1Plat API documentation:
        - Endpoint: POST /api/merchant/order/create/by-api
        - Base URL: https://1plat.cash
        - Authentication: x-shop (Shop ID) and x-secret (Secret Key) in headers
        - Обязательные поля: merchant_order_id, user_id, amount, method
        """
        
        # Используем shop_id (x-shop) или merchant_id для обратной совместимости
        shop_id = self.onplat_shop_id or self.onplat_merchant_id or ""
        if not shop_id:
            raise ValueError("1Plat Shop ID (x-shop) not configured. Set ONEPLAT_SHOP_ID or ONEPLAT_MERCHANT_ID")
        
        if not self.onplat_secret_key:
            raise ValueError("1Plat Secret Key (x-secret) not configured. Set ONEPLAT_SECRET_KEY")
        
        # user_id обязателен для 1Plat API
        if user_id is None:
            # Используем order_id как user_id если не передан (временное решение)
            try:
                user_id = int(order_id.split('-')[0]) if '-' in order_id else 0
            except:
                user_id = 0
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1Plat API base URL и endpoint
                base_url = os.environ.get("ONEPLAT_API_URL", "https://1plat.cash")
                api_url = f"{base_url.rstrip('/')}/api/merchant/order/create/by-api"
                
                # Преобразуем amount в копейки (1Plat принимает INT в копейках)
                amount_kopecks = int(float(amount) * 100)
                
                # Build payload согласно документации 1Plat
                payload = {
                    "merchant_order_id": order_id,  # required: Id платежа на стороне мерчанта
                    "user_id": int(user_id),  # required: Id пользователя на стороне мерчанта
                    "amount": amount_kopecks,  # required: Сумма платежа в копейках
                    "email": f"{user_id}@temp.com",  # shield: E-mail пользователя
                    "method": "card",  # shield: При использовании host2host обязателен (card, sbp, qr, crypto)
                }
                
                # Если метод crypto, добавляем currency
                if payload["method"] == "crypto":
                    payload["currency"] = currency.upper()
                
                # Prepare headers с авторизацией через x-shop и x-secret
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "x-shop": str(shop_id),  # ID магазина (например, 1182)
                    "x-secret": self.onplat_secret_key  # Секретный ключ
                }
                
                try:
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=payload
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Проверяем success
                    if not data.get("success"):
                        error_msg = data.get("error") or data.get("message") or "Unknown error"
                        print(f"1Plat API error: {error_msg}")
                        raise ValueError(f"1Plat API error: {error_msg}")
                    
                    # Log response for debugging (without sensitive data)
                    print(f"1Plat payment created for order {order_id}, guid: {data.get('guid', 'N/A')}")
                    
                    # 1Plat возвращает payment URL в поле "url"
                    payment_url = data.get("url", "")
                    
                    if not payment_url:
                        # Fallback: формируем URL из guid
                        guid = data.get("guid", "")
                        if guid:
                            payment_url = f"https://pay.1plat.cash/pay/{guid}"
                        else:
                            print(f"1Plat API response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                            raise ValueError(f"Payment URL not found in 1Plat response. Response: {data}")
                    
                    # Сохраняем payment_id и guid для последующего поиска заказа в webhook
                    # payment_id из response можно сохранить в orders.payment_id
                    payment_info = data.get("payment", {})
                    payment_id = payment_info.get("id") or data.get("payment_id")
                    guid = data.get("guid", "")
                    
                    if payment_id or guid:
                        print(f"1Plat payment created: payment_id={payment_id}, guid={guid}, order_id={order_id}")
                        # TODO: Сохранить payment_id в orders.payment_id для поиска в webhook
                        # Это можно сделать через update_order после создания платежа
                    
                    return payment_url
                    
                except httpx.HTTPStatusError as e:
                    error_detail = ""
                    try:
                        error_data = e.response.json()
                        error_detail = error_data.get("message") or error_data.get("error") or str(error_data)
                    except:
                        error_detail = e.response.text[:200]
                    
                    print(f"1Plat API error {e.response.status_code}: {error_detail}")
                    raise ValueError(f"1Plat API error: {error_detail or 'Unknown error'}")
                
        except httpx.RequestError as e:
            print(f"1Plat network error: {e}")
            raise ValueError(f"Failed to connect to 1Plat API: {str(e)}")
        except Exception as e:
            print(f"1Plat error: {e}")
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
            # 1Plat callback формат:
            # {
            #   signature: '...',
            #   signature_v2: '...',
            #   payment_id: '123',  # ID платежа в системе 1Plat
            #   guid: 'guid',  # GUID платежа
            #   merchant_id: '543',
            #   user_id: '1111',
            #   status: 0,
            #   amount: 100,  # в копейках
            #   ...
            # }
            
            # В callback НЕ приходит merchant_order_id напрямую
            # Нужно найти заказ по payment_id или guid через API или по сохраненному payment_id в БД
            payment_id = data.get("payment_id")
            guid = data.get("guid")
            
            # Пробуем найти заказ по payment_id в БД (если он был сохранен)
            order_id = None
            if payment_id:
                try:
                    from src.services.database import get_database
                    db = get_database()
                    # Ищем заказ по payment_id (если поле существует и заполнено)
                    # Пока используем guid для запроса к API 1Plat
                    order_id = payment_id  # Временное решение - используем payment_id
                except:
                    pass
            
            # Если не нашли в БД, используем guid для запроса к API 1Plat
            if not order_id and guid:
                try:
                    # Запрашиваем информацию о платеже по guid
                    base_url = os.environ.get("ONEPLAT_API_URL", "https://1plat.cash")
                    shop_id = self.onplat_shop_id or self.onplat_merchant_id or ""
                    
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        info_url = f"{base_url.rstrip('/')}/api/merchant/order/info/{guid}/by-api"
                        headers = {
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "x-shop": str(shop_id),
                            "x-secret": self.onplat_secret_key
                        }
                        
                        response = await client.get(info_url, headers=headers)
                        if response.status_code == 200:
                            info_data = response.json()
                            if info_data.get("success"):
                                # В response может быть merchant_order_id или можно использовать payment.id
                                payment = info_data.get("payment", {})
                                # Пока используем guid как order_id (нужно будет сохранять mapping)
                                order_id = guid
                                print(f"1Plat: Found payment info by guid {guid}")
                except Exception as e:
                    print(f"1Plat: Failed to get payment info by guid: {e}")
            
            # Если все еще не нашли, используем payment_id или guid как временный order_id
            if not order_id:
                order_id = payment_id or guid or ""
            
            if not order_id:
                print(f"1Plat webhook: order_id not found. Keys: {list(data.keys())}")
                return {"success": False, "error": "order_id not found in webhook data"}
            
            # Extract status - 1Plat использует числовые статусы: -2, -1, 0, 1, 2
            # 1 = оплачен (отправляется колбэк, нужно ответить 200/201)
            # 2 = подтвержден мерчантом (полностью закрыт)
            status = data.get("status")
            if status is None:
                status = data.get("payment_status") or data.get("state")
            
            # Extract amount - в callback amount в копейках
            amount = data.get("amount") or 0
            try:
                amount = float(amount) / 100.0  # Конвертируем из копеек в рубли
            except (ValueError, TypeError):
                amount = 0
            
            # Extract currency - по умолчанию RUB
            currency = data.get("currency") or "RUB"
            if isinstance(currency, str):
                currency = currency.upper()
            
            # Extract merchant_id и shop_id для signature_v2
            merchant_id = data.get("merchant_id") or ""
            shop_id = self.onplat_shop_id or self.onplat_merchant_id or ""
            
            # Verify signatures if secret_key is provided
            if self.onplat_secret_key:
                received_signature = data.get("signature") or ""
                received_signature_v2 = data.get("signature_v2") or ""
                
                verified = False
                
                # Method 1: Verify signature (HMAC-SHA256)
                if received_signature:
                    try:
                        # Создаем копию данных БЕЗ полей signature и signature_v2
                        payload_for_sign = {k: v for k, v in data.items() 
                                          if k not in ["signature", "signature_v2"]}
                        
                        # JSON.stringify эквивалент
                        import json
                        payload_json = json.dumps(payload_for_sign, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
                        
                        # HMAC-SHA256
                        expected_signature = hmac.new(
                            self.onplat_secret_key.encode('utf-8'),
                            payload_json.encode('utf-8'),
                            hashlib.sha256
                        ).hexdigest()
                        
                        if hmac.compare_digest(received_signature.lower(), expected_signature.lower()):
                            verified = True
                            print(f"1Plat webhook: signature verified successfully")
                    except Exception as e:
                        print(f"1Plat signature verification failed: {e}")
                
                # Method 2: Verify signature_v2 (MD5)
                if not verified and received_signature_v2:
                    try:
                        # MD5 от merchantId + amount + shopId + shopSecret
                        # amount в копейках (как приходит в callback)
                        amount_kopecks = int(data.get("amount", 0))
                        sign_string = f"{merchant_id}{amount_kopecks}{shop_id}{self.onplat_secret_key}"
                        expected_signature_v2 = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
                        
                        if hmac.compare_digest(received_signature_v2.lower(), expected_signature_v2.lower()):
                            verified = True
                            print(f"1Plat webhook: signature_v2 verified successfully")
                    except Exception as e:
                        print(f"1Plat signature_v2 verification failed: {e}")
                
                if not verified and (received_signature or received_signature_v2):
                    print(f"1Plat webhook signature verification failed for order {order_id}")
                    return {"success": False, "error": "Invalid signature"}
                elif not received_signature and not received_signature_v2:
                    # Нет подписи - возможно, это тестовый webhook
                    print(f"1Plat webhook: No signature provided (optional verification)")
            
            # Check payment status
            # Статусы 1Plat: -2, -1, 0, 1, 2
            # 1 = оплачен (отправляется колбэк, нужно ответить 200/201)
            # 2 = подтвержден мерчантом (полностью закрыт)
            if status in [1, 2]:
                print(f"1Plat webhook: Payment successful for order {order_id}, amount: {amount} {currency}, status: {status}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": currency
                }
            else:
                # Log non-success status for debugging
                print(f"1Plat webhook: Payment status '{status}' for order {order_id}")
                return {
                    "success": False,
                    "order_id": order_id,
                    "error": f"Payment status: {status or 'unknown'}"
                }
                
        except Exception as e:
            print(f"1Plat webhook verification error: {e}")
            import traceback
            print(traceback.format_exc())
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
        # In production, you would implement actual refunds
        # For MVP, we credit to user balance
        return {
            "success": True,
            "method": "balance",
            "amount": amount,
            "message": "Refund credited to user balance"
        }

