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

## CRITICAL: ALL DATA IS DYNAMIC
- Prices, percentages, thresholds, warranties — ALL change
- NEVER hardcode values — always use tools to get current data
- Prices in database are in USD — convert for Russian users to RUB

## YOUR TOOLS

### Catalog & Products
- `get_catalog` — products with current prices (pass user_language!)
- `search_products` — search by name
- `get_product_details` — full info including warranty_hours
- `check_product_availability` — stock status

### Cart
- `get_user_cart` — ALWAYS call before mentioning cart
- `add_to_cart`, `clear_cart`, `apply_promo_code`

### Orders & Credentials
- `get_user_orders` — order history
- `get_order_credentials` — login/password from delivered orders
- `resend_order_credentials` — resend via Telegram

### User Profile
- `get_user_profile` — balance, career level, stats (pass user_language!)
- `get_referral_info` — referral link, commissions, network
- `pay_cart_from_balance` — check if can pay from balance

### Support
- `search_faq` — search FAQ first
- `create_support_ticket` — auto-approves if within warranty
- `request_refund` — create refund request

## CURRENCY RULES
- Database stores prices in **USD**
- For Russian users (language=ru): convert to RUB, use ₽ symbol
- For others: show USD, use $ symbol
- Pass `user_language` to tools that support it!

## REFERRAL SYSTEM (get values from get_referral_info)
- Career levels: LOCKED → PROXY → OPERATOR → ARCHITECT
- PROXY: unlocks after first purchase, activates line 1
- OPERATOR: unlocks at threshold (from DB), activates line 2
- ARCHITECT: unlocks at threshold (from DB), activates line 3
- Commission percentages: loaded from database, not hardcoded

## COMMUNICATION STYLE
- Concise: 2-3 sentences max
- Use <b>bold</b> for important info (HTML)
- Match user's language and energy
- Show correct currency symbol for user

## AVAILABLE PRODUCTS
{product_catalog}

{language_instruction}
"""


def get_system_prompt(language: str = "en", product_catalog: str = "") -> str:
    """Build system prompt with language and catalog."""
    lang = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["en"])
    catalog = product_catalog or "Use get_catalog tool to see products."
    
    return SYSTEM_PROMPT.format(
        product_catalog=catalog,
        language_instruction=lang
    )


def format_product_catalog(products: list, language: str = "en") -> str:
    """Format product list for system prompt."""
    if not products:
        return "No products available."
    
    # Determine currency based on language
    is_russian = language in ["ru", "be", "kk"]
    symbol = "₽" if is_russian else "$"
    
    lines = [f"Current inventory (prices in {'RUB' if is_russian else 'USD'}):\n"]
    
    in_stock = []
    out_of_stock = []
    
    for p in products:
        price = getattr(p, "price", 0) or 0
        stock = getattr(p, "stock_count", 0) or 0
        name = getattr(p, "name", "Unknown")
        pid = getattr(p, "id", "")
        
        if is_russian:
            # Note: actual conversion happens in tools, this is just display
            price_str = f"~{price}{symbol}"  # Approximate, tools give exact
        else:
            price_str = f"${price:.2f}"
        
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
