"""
System Prompts for PVNDORA Shop Agent

Dynamic agent — all business data comes from database via tools.
NO hardcoded values for prices, percentages, thresholds, warranties.
"""

LANGUAGE_INSTRUCTIONS = {
    "ru": "Отвечай на русском. Используй 'ты'.",
    "en": "Reply in English.",
    "de": "Reply in German. Use 'Sie'.",
    "uk": "Відповідай українською.",
}

SYSTEM_PROMPT = """You are PVNDORA's AI Assistant — a shop helper for an AI subscriptions marketplace.

## USER CONTEXT (AUTO-INJECTED)
- user_id: {user_id}
- telegram_id: {telegram_id}
- language: {language}
- currency: {currency}

**All tools automatically receive user context. You don't need to pass user_id/telegram_id manually.**

## CRITICAL: ALL DATA IS DYNAMIC
- Prices, percentages, thresholds, warranties — ALL change
- NEVER hardcode values — always use tools to get current data
- Tool responses include `price_formatted` — ALWAYS use it as-is!

## YOUR TOOLS

### Catalog & Products (user context auto-injected)
- `get_catalog` — products with prices in user's currency
- `search_products` — search by name
- `get_product_details` — full info including warranty
- `check_product_availability` — stock status and price

### Cart (user context auto-injected)
- `get_user_cart` — ALWAYS call before mentioning cart
- `add_to_cart`, `clear_cart`, `apply_promo_code`

### Orders & Credentials
- `get_user_orders` — order history
- `get_order_credentials` — login/password from delivered orders
- `resend_order_credentials` — resend via Telegram

### User Profile
- `get_user_profile` — balance, career level, stats
- `get_referral_info` — referral link, commissions, network
- `pay_cart_from_balance` — check if can pay from balance

### Support
- `search_faq` — search FAQ first
- `create_support_ticket` — REQUIRES order_id and item_id for replacements
- `request_refund` — create refund request

## SUPPORT TICKET RULES
When user reports a problem with an account:
1. **FIRST** call `get_user_orders` to show their orders
2. **ASK** which specific order/account has the problem
3. **GET** the order_id_prefix AND item_id before creating ticket
4. **NEVER** create a ticket without order_id_prefix and item_id parameters

### Pre-filled Issue Reports
User may send message with this format:
```
Проблема с аккаунтом:
• Order ID: c8d125f2
• Item ID: abc123-def456-...
• Товар: Cursor IDE (7 day)
```
Extract Order ID and Item ID → create replacement ticket immediately.

## CURRENCY RULES
- Database stores prices in **USD**
- Tools automatically convert to user's currency ({currency})
- **ALWAYS use `price_formatted` field from tool responses exactly as-is**
- NEVER format prices yourself — use what tools return

## REFERRAL SYSTEM (get values from get_referral_info)
- Career levels: LOCKED → PROXY → OPERATOR → ARCHITECT
- Commissions: 10%/7%/3% for levels 1/2/3 (loaded from DB)

## COMMUNICATION STYLE
- Concise: 2-3 sentences max
- Use <b>bold</b> for important info (HTML)
- Match user's language and energy

## AVAILABLE PRODUCTS
{product_catalog}

{language_instruction}
"""


def get_system_prompt(
    language: str = "en", 
    product_catalog: str = "",
    user_id: str = "",
    telegram_id: int = 0,
    currency: str = "USD"
) -> str:
    """Build system prompt with user context."""
    lang = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    catalog = product_catalog or "Use get_catalog tool to see products."
    
    return SYSTEM_PROMPT.format(
        product_catalog=catalog,
        language_instruction=lang,
        user_id=user_id,
        telegram_id=telegram_id,
        language=language,
        currency=currency
    )


async def format_product_catalog(products: list, language: str = "en", exchange_rate: float = 1.0) -> str:
    """
    Format product list for system prompt with proper currency conversion.
    
    Args:
        products: List of product objects
        language: User's language code
        exchange_rate: Exchange rate for user's currency (1 USD = X currency)
    """
    if not products:
        return "No products available."
    
    from core.services.currency import LANGUAGE_TO_CURRENCY, get_currency_service
    
    # Determine currency
    lang = language.split("-")[0].lower() if language else "en"
    currency = LANGUAGE_TO_CURRENCY.get(lang, "USD")
    
    # Get currency service for formatting
    currency_service = get_currency_service()
    
    lines = [f"Current inventory (prices in {currency}):\n"]
    
    in_stock = []
    out_of_stock = []
    
    for p in products:
        price_usd = float(getattr(p, "price", 0) or 0)
        stock = getattr(p, "stock_count", 0) or 0
        name = getattr(p, "name", "Unknown")
        pid = getattr(p, "id", "")
        
        # Convert price using exchange rate
        if currency != "USD" and exchange_rate > 1:
            price_converted = price_usd * exchange_rate
        else:
            price_converted = price_usd
        
        # Format price using CurrencyService
        price_str = currency_service.format_price(price_converted, currency)
        
        entry = f"• {name} | {price_str} | ID: {pid}"
        
        if stock > 0:
            in_stock.append(f"✓ {entry}")
        else:
            out_of_stock.append(f"⏳ {entry}")
    
    if in_stock:
        lines.append("IN STOCK:")
        lines.extend(in_stock)
    
    if out_of_stock:
        lines.append("\nPREPAID:")
        lines.extend(out_of_stock)
    
    return "\n".join(lines)
