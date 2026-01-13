"""
Common Error Constants

Centralized error messages to avoid string duplication (SonarQube S1192).
"""

# User errors
ERROR_USER_NOT_FOUND = "User not found"
ERROR_USER_BANNED = "User is banned"
ERROR_UNAUTHORIZED = "Unauthorized"

# Order errors
ERROR_ORDER_NOT_FOUND = "Order not found"
ERROR_ORDER_ACCESS_DENIED = "Order does not belong to user"
ERROR_ORDER_INVALID_STATUS = "Invalid order status"

# Product errors
ERROR_PRODUCT_NOT_FOUND = "Product not found"
ERROR_PRODUCT_OUT_OF_STOCK = "Product out of stock"

# Payment errors
ERROR_PAYMENT_FAILED = "Payment failed"
ERROR_INSUFFICIENT_BALANCE = "Insufficient balance"

# Generic errors
ERROR_INVALID_REQUEST = "Invalid request"
ERROR_INTERNAL = "Internal server error"
ERROR_NOT_FOUND = "Not found"
