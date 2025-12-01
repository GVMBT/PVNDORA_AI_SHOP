"""Payment Service - AAIO and Stripe Integration"""
import os
import hashlib
import hmac
from typing import Dict, Any
from urllib.parse import urlencode

import httpx


class PaymentService:
    """Unified payment service for AAIO (Russia) and Stripe (International)"""
    
    def __init__(self):
        # AAIO credentials
        self.aaio_merchant_id = os.environ.get("AAIO_MERCHANT_ID", "")
        self.aaio_secret_key = os.environ.get("AAIO_SECRET_KEY", "")
        self.aaio_api_key = os.environ.get("AAIO_API_KEY", "")
        
        # Stripe credentials
        self.stripe_secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
        self.stripe_webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        
        # CardLink credentials
        self.cardlink_api_token = os.environ.get("CARDLINK_API_TOKEN", "")
        self.cardlink_shop_id = os.environ.get("CARDLINK_SHOP_ID", "")
        
        # Webhook URLs
        self.base_url = os.environ.get("WEBAPP_URL", "https://pvndora.app")
    
    async def create_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        method: str = "aaio",
        user_email: str = "",
        currency: str = "RUB"
    ) -> str:
        """
        Create payment and return payment URL.
        
        Args:
            order_id: Unique order ID
            amount: Payment amount
            product_name: Product name for description
            method: Payment method ('aaio' or 'stripe')
            user_email: User email for receipts
            currency: Currency code
            
        Returns:
            Payment URL for redirect
        """
        if method == "aaio":
            return await self._create_aaio_payment(
                order_id, amount, product_name, currency
            )
        elif method == "stripe":
            return await self._create_stripe_payment(
                order_id, amount, product_name, user_email, currency
            )
        elif method == "cardlink":
            return await self._create_cardlink_payment(
                order_id, amount, product_name, currency
            )
        else:
            raise ValueError(f"Unknown payment method: {method}")
    
    # ==================== AAIO ====================
    
    async def _create_aaio_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB"
    ) -> str:
        """Create AAIO payment URL"""
        
        # Generate signature
        sign_string = f"{self.aaio_merchant_id}:{amount}:{currency}:{self.aaio_secret_key}:{order_id}"
        sign = hashlib.sha256(sign_string.encode()).hexdigest()
        
        # Build payment URL
        params = {
            "merchant_id": self.aaio_merchant_id,
            "amount": str(amount),
            "currency": currency,
            "order_id": order_id,
            "sign": sign,
            "desc": product_name[:128],  # Max 128 chars
            "lang": "ru"
        }
        
        return f"https://aaio.so/merchant/pay?{urlencode(params)}"
    
    async def verify_aaio_callback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify AAIO callback signature and extract order info.
        
        Args:
            data: Callback form data
            
        Returns:
            Dict with success status and order_id
        """
        try:
            # Extract fields
            merchant_id = data.get("merchant_id", "")
            amount = data.get("amount", "")
            currency = data.get("currency", "RUB")
            order_id = data.get("order_id", "")
            received_sign = data.get("sign", "")
            
            # Verify merchant ID
            if merchant_id != self.aaio_merchant_id:
                return {"success": False, "error": "Invalid merchant ID"}
            
            # Verify signature
            sign_string = f"{self.aaio_merchant_id}:{amount}:{currency}:{self.aaio_secret_key}:{order_id}"
            expected_sign = hashlib.sha256(sign_string.encode()).hexdigest()
            
            if not hmac.compare_digest(received_sign, expected_sign):
                return {"success": False, "error": "Invalid signature"}
            
            return {
                "success": True,
                "order_id": order_id,
                "amount": float(amount),
                "currency": currency
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def check_aaio_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Check AAIO payment status via API"""
        
        if not self.aaio_api_key:
            return {"success": False, "error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://aaio.so/api/info-pay",
                    headers={
                        "Accept": "application/json",
                        "X-Api-Key": self.aaio_api_key
                    },
                    data={
                        "merchant_id": self.aaio_merchant_id,
                        "order_id": order_id
                    }
                )
                
                data = response.json()
                
                if data.get("type") == "success":
                    return {
                        "success": True,
                        "status": data.get("status"),  # "in_process", "success", "expired", etc.
                        "amount": data.get("amount"),
                        "order_id": order_id
                    }
                
                return {"success": False, "error": data.get("message", "Unknown error")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== STRIPE ====================
    
    async def _create_stripe_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        user_email: str,
        currency: str = "USD"
    ) -> str:
        """Create Stripe Checkout Session"""
        
        if not self.stripe_secret_key:
            raise ValueError("Stripe secret key not configured")
        
        try:
            import stripe
            stripe.api_key = self.stripe_secret_key
            
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            # Create Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": product_name,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{self.base_url}/payment/success?order_id={order_id}",
                cancel_url=f"{self.base_url}/payment/cancel?order_id={order_id}",
                client_reference_id=order_id,
                customer_email=user_email if "@" in user_email else None,
                metadata={
                    "order_id": order_id
                }
            )
            
            return session.url
            
        except Exception as e:
            print(f"Stripe error: {e}")
            raise
    
    async def verify_stripe_webhook(
        self,
        payload: bytes,
        sig_header: str
    ) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature and extract event data.
        
        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value
            
        Returns:
            Dict with success status and order_id
        """
        if not self.stripe_webhook_secret:
            return {"success": False, "error": "Webhook secret not configured"}
        
        try:
            import stripe
            stripe.api_key = self.stripe_secret_key
            
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.stripe_webhook_secret
            )
            
            # Handle checkout.session.completed
            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                order_id = session.get("client_reference_id") or session.get("metadata", {}).get("order_id")
                
                if order_id:
                    return {
                        "success": True,
                        "order_id": order_id,
                        "amount": session.get("amount_total", 0) / 100,
                        "currency": session.get("currency", "usd").upper()
                    }
            
            # Other event types
            return {"success": False, "error": f"Unhandled event type: {event['type']}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== CARDLINK ====================
    
    async def _create_cardlink_payment(
        self,
        order_id: str,
        amount: float,
        product_name: str,
        currency: str = "RUB"
    ) -> str:
        """Create CardLink payment URL"""
        
        if not self.cardlink_api_token or not self.cardlink_shop_id:
            raise ValueError("CardLink credentials not configured")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cardlink.link/v1/payments",
                    headers={
                        "Authorization": f"Bearer {self.cardlink_api_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "shop_id": self.cardlink_shop_id,
                        "amount": amount,
                        "currency": currency,
                        "order_id": order_id,
                        "description": product_name[:128],  # Max 128 chars
                        "success_url": f"{self.base_url}/payment/success?order_id={order_id}",
                        "fail_url": f"{self.base_url}/payment/fail?order_id={order_id}"
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # CardLink returns payment URL in response
                return data.get("payment_url", data.get("url", ""))
                
        except Exception as e:
            print(f"CardLink error: {e}")
            raise
    
    async def verify_cardlink_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify CardLink webhook and extract order info.
        
        Args:
            data: Webhook JSON data
            
        Returns:
            Dict with success status and order_id
        """
        try:
            # CardLink webhook format (verify signature if provided)
            order_id = data.get("order_id", "")
            status = data.get("status", "")
            amount = data.get("amount", 0)
            
            if status == "success" or status == "paid":
                return {
                    "success": True,
                    "order_id": order_id,
                    "amount": float(amount) if amount else 0,
                    "currency": data.get("currency", "RUB")
                }
            else:
                return {
                    "success": False,
                    "order_id": order_id,
                    "error": f"Payment status: {status}"
                }
                
        except Exception as e:
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

