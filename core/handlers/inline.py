"""
Inline Query Handlers - Viral Sharing

Handles inline queries for:
- Product sharing with preview
- switchInlineQuery mechanism
- Viral referral sharing
"""

import hashlib
from typing import Optional

from aiogram import Router, F
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChosenInlineResult
)


router = Router(name="inline")


# ============================================================
# Inline Query Handler
# ============================================================

@router.inline_query()
async def handle_inline_query(
    inline_query: InlineQuery,
    language_code: str,
    **kwargs
):
    """
    Handle inline queries for product sharing.
    
    Users can share products via @bot_username query
    Results show product preview and invite friends.
    """
    query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    
    results = []
    
    if not query:
        # Show default sharing options
        results.append(
            InlineQueryResultArticle(
                id="share_ref",
                title="🎁 Share your referral link",
                description="Invite friends and earn bonuses!",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🎁 <b>Check out PVNDORA!</b>\n\n"
                        f"Premium AI subscriptions at great prices:\n"
                        f"• ChatGPT Plus\n"
                        f"• Claude Pro\n"
                        f"• Midjourney\n"
                        f"• And more!\n\n"
                        f"👇 Start here:"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🚀 Open PVNDORA",
                        url=f"https://t.me/pvndora_bot?start=ref_{user_id}"
                    )]
                ])
            )
        )
        
        results.append(
            InlineQueryResultArticle(
                id="share_catalog",
                title="🛍 Share product catalog",
                description="Share the catalog with friends",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🛍 <b>PVNDORA Catalog</b>\n\n"
                        f"Premium AI subscriptions:\n"
                        f"✅ Best prices\n"
                        f"✅ Instant delivery\n"
                        f"✅ Warranty included\n\n"
                        f"Check it out! 👇"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🛍 Open Catalog",
                        url=f"https://t.me/pvndora_bot?start=ref_{user_id}"
                    )]
                ])
            )
        )
    
    else:
        # Search products to share
        # Import here to avoid circular imports
        from core.db import get_supabase
        
        try:
            supabase = await get_supabase()
            
            # Search products by name
            search_result = await supabase.table("products").select(
                "id, name, description, price, type"
            ).ilike("name", f"%{query}%").eq(
                "status", "active"
            ).limit(10).execute()
            
            products = search_result.data or []
            
            for product in products:
                product_id = product["id"]
                name = product["name"]
                description = product.get("description", "")[:100]
                price = product.get("price", 0)
                
                # Create unique result ID
                result_id = hashlib.md5(f"{product_id}:{user_id}".encode()).hexdigest()
                
                results.append(
                    InlineQueryResultArticle(
                        id=result_id,
                        title=f"📦 {name}",
                        description=f"{description}... • {price:.0f}₽",
                        input_message_content=InputTextMessageContent(
                            message_text=(
                                f"📦 <b>{name}</b>\n\n"
                                f"{description}\n\n"
                                f"💰 Price: <b>{price:.0f}₽</b>\n\n"
                                f"🛒 Buy it here:"
                            ),
                            parse_mode="HTML"
                        ),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Buy {name}",
                                url=f"https://t.me/pvndora_bot?start=product_{product_id}_ref_{user_id}"
                            )]
                        ])
                    )
                )
        
        except Exception as e:
            # If DB not available, show generic result
            results.append(
                InlineQueryResultArticle(
                    id="search_error",
                    title="🔍 Search PVNDORA",
                    description=f"Search for: {query}",
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            f"🔍 Looking for <b>{query}</b>?\n\n"
                            f"Find the best AI subscriptions at PVNDORA!"
                        ),
                        parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🔍 Search in PVNDORA",
                            url=f"https://t.me/pvndora_bot?start=ref_{user_id}"
                        )]
                    ])
                )
            )
    
    # Answer with results
    await inline_query.answer(
        results,
        cache_time=300,  # Cache for 5 minutes
        is_personal=True  # Different results per user (for referral links)
    )


@router.chosen_inline_result()
async def handle_chosen_inline_result(
    chosen_result: ChosenInlineResult,
    **kwargs
):
    """
    Track when user sends an inline result.
    
    Used for analytics on viral sharing.
    """
    result_id = chosen_result.result_id
    user_id = chosen_result.from_user.id
    query = chosen_result.query
    
    # Log analytics event
    try:
        from core.db import get_supabase
        supabase = await get_supabase()
        
        # Get user
        user = await supabase.table("users").select("id").eq(
            "telegram_id", user_id
        ).single().execute()
        
        if user.data:
            await supabase.table("analytics_events").insert({
                "user_id": user.data["id"],
                "event_type": "share",
                "metadata": {
                    "result_id": result_id,
                    "query": query
                }
            }).execute()
    
    except Exception:
        pass  # Non-critical, don't fail


# ============================================================
# switchInlineQuery Helpers
# ============================================================

def get_share_keyboard(
    product_id: Optional[str] = None,
    product_name: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    Get keyboard with share button using switchInlineQuery.
    
    Args:
        product_id: Product to pre-fill in query
        product_name: Product name for display
    
    Returns:
        Keyboard with share button
    """
    if product_name:
        query = product_name
    else:
        query = ""
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Share with friends",
            switch_inline_query=query
        )]
    ])


def get_share_current_chat_keyboard(
    product_name: str
) -> InlineKeyboardMarkup:
    """
    Get keyboard for sharing in current chat.
    
    Uses switch_inline_query_current_chat.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Share here",
            switch_inline_query_current_chat=product_name
        )]
    ])

