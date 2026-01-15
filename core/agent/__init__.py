"""PVNDORA Shop Agent.

Full-featured AI assistant powered by LangGraph + Gemini.
Handles: Catalog, Cart, Orders, Credentials, Referrals, Support.
"""

from .agent import ShopAgent, get_shop_agent, reset_agent

__all__ = ["ShopAgent", "get_shop_agent", "reset_agent"]
