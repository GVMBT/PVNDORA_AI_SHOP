"""Tool definitions for Gemini function calling."""

# Tool definitions - schemas sent to Gemini
TOOLS = [
    # === PRODUCT TOOLS ===
    {
        "name": "check_product_availability",
        "description": "Check if a specific product is available in stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name or partial name of the product"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_product_details",
        "description": "Get detailed info about a product including price and stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Unique ID of the product"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "search_products",
        "description": "Search products by user needs. Uses semantic search.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query based on user's needs"
                },
                "category": {
                    "type": "string",
                    "description": "Product category filter",
                    "enum": ["all", "chatgpt", "claude", "midjourney", "image", "code", "writing"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_catalog",
        "description": "Get all available products. Use for catalog/availability requests.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "compare_products",
        "description": "Compare two or more products.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of product names to compare"
                }
            },
            "required": ["product_names"]
        }
    },
    
    # === PURCHASE TOOLS ===
    {
        "name": "create_purchase_intent",
        "description": "Create purchase intent for buying. Use when user wants to buy.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to purchase"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "add_to_waitlist",
        "description": "Add user to waitlist for an out-of-stock product.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product to wait for"
                }
            },
            "required": ["product_name"]
        }
    },
    
    # === CART TOOLS ===
    {
        "name": "get_user_cart",
        "description": "Get user's shopping cart with all items.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "add_to_cart",
        "description": "Add product to cart. Auto-splits into instant/prepaid based on stock.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to add"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to add (default: 1)",
                    "default": 1,
                    "minimum": 1
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "update_cart",
        "description": "Update cart: change quantity or remove item. Don't clear before payment.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["update_quantity", "remove_item", "clear"]
                },
                "product_id": {
                    "type": "string",
                    "description": "Product ID (for update_quantity/remove_item)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "New quantity (for update_quantity)"
                }
            },
            "required": ["operation"]
        }
    },
    
    # === USER TOOLS ===
    {
        "name": "get_user_orders",
        "description": "Get user's recent orders.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of orders to return"
                }
            }
        }
    },
    {
        "name": "add_to_wishlist",
        "description": "Add a product to user's wishlist.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "ID of the product to add to wishlist"
                }
            },
            "required": ["product_id"]
        }
    },
    {
        "name": "get_wishlist",
        "description": "Get user's wishlist with saved products.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_referral_info",
        "description": "Get user's referral link and statistics.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "apply_promo_code",
        "description": "Check and apply a promo code for discount.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The promo code to apply"
                }
            },
            "required": ["code"]
        }
    },
    
    # === SUPPORT TOOLS ===
    {
        "name": "create_support_ticket",
        "description": "Create support ticket for issues with purchase.",
        "parameters": {
            "type": "object",
            "properties": {
                "issue_description": {
                    "type": "string",
                    "description": "Description of the user's issue"
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID if known (optional)"
                }
            },
            "required": ["issue_description"]
        }
    },
    {
        "name": "get_faq_answer",
        "description": "Get answer from FAQ for common questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "User's question to find in FAQ"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "request_refund",
        "description": "Request a refund for a problematic order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to refund"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for refund request"
                }
            },
            "required": ["order_id", "reason"]
        }
    }
]

