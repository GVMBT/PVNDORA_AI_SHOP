"""Cart models with Decimal-based pricing."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from core.services.money import to_decimal, round_money, subtract, divide, multiply


@dataclass
class CartItem:
    """Single item in the cart."""
    product_id: str
    product_name: str
    quantity: int
    instant_quantity: int  # Available in stock
    prepaid_quantity: int  # Needs to be ordered
    unit_price: Decimal
    discount_percent: Decimal = Decimal("0")
    added_at: str = ""
    
    def __post_init__(self):
        if not self.added_at:
            self.added_at = datetime.now(timezone.utc).isoformat()
        # Normalize numeric fields
        self.unit_price = to_decimal(self.unit_price)
        self.discount_percent = to_decimal(self.discount_percent)
    
    @property
    def final_price(self) -> Decimal:
        """Price after discount for a single unit."""
        multiplier = subtract(Decimal("1"), divide(self.discount_percent, Decimal("100")))
        return round_money(multiply(self.unit_price, multiplier))
    
    @property
    def total_price(self) -> Decimal:
        """Total price for all units."""
        return round_money(multiply(self.final_price, self.quantity))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "instant_quantity": self.instant_quantity,
            "prepaid_quantity": self.prepaid_quantity,
            "unit_price": str(self.unit_price),
            "discount_percent": float(self.discount_percent),
            "added_at": self.added_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CartItem":
        """Create from dictionary."""
        return cls(
            product_id=data["product_id"],
            product_name=data["product_name"],
            quantity=int(data["quantity"]),
            instant_quantity=int(data["instant_quantity"]),
            prepaid_quantity=int(data["prepaid_quantity"]),
            unit_price=to_decimal(data["unit_price"]),
            discount_percent=to_decimal(data.get("discount_percent", 0)),
            added_at=data.get("added_at", ""),
        )


@dataclass
class Cart:
    """Shopping cart containing multiple items."""
    user_telegram_id: int
    items: List[CartItem]
    promo_code: Optional[str] = None
    promo_discount_percent: Decimal = Decimal("0")
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self.promo_discount_percent = to_decimal(self.promo_discount_percent)
    
    @property
    def total_items(self) -> int:
        """Total number of items in cart."""
        return sum(item.quantity for item in self.items)
    
    @property
    def instant_total(self) -> Decimal:
        """Total for items available instantly."""
        return sum(item.final_price * item.instant_quantity for item in self.items)
    
    @property
    def prepaid_total(self) -> Decimal:
        """Total for items that need to be ordered."""
        return sum(item.final_price * item.prepaid_quantity for item in self.items)
    
    @property
    def subtotal(self) -> Decimal:
        """Subtotal after item-level discounts but before cart-level promo code."""
        # Calculate subtotal with item-level discounts (from CartItem.final_price)
        return sum(item.total_price for item in self.items)
    
    @property
    def total(self) -> Decimal:
        """Final total after all discounts.
        
        Calculation order:
        1. Apply item-level discounts (CartItem.discount_percent) -> item.final_price
        2. Apply cart-level promo discount (Cart.promo_discount_percent) -> final total
        """
        # Step 1: Subtotal already includes item-level discounts (from CartItem.final_price)
        subtotal_after_items = self.subtotal
        
        # Step 2: Apply cart-level promo discount (if promo_code is cart-wide, not product-specific)
        if self.promo_discount_percent > 0:
            multiplier = subtract(Decimal("1"), divide(self.promo_discount_percent, Decimal("100")))
            return round_money(multiply(subtotal_after_items, multiplier))
        
        return subtotal_after_items
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "user_telegram_id": self.user_telegram_id,
            "items": [item.to_dict() for item in self.items],
            "promo_code": self.promo_code,
            "promo_discount_percent": float(self.promo_discount_percent),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Cart":
        """Create from dictionary."""
        items = [CartItem.from_dict(item) for item in data.get("items", [])]
        return cls(
            user_telegram_id=data["user_telegram_id"],
            items=items,
            promo_code=data.get("promo_code"),
            promo_discount_percent=to_decimal(data.get("promo_discount_percent", 0)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", "")
        )

