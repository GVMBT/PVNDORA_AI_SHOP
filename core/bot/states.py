"""
FSM States for Bot Conversation Flows

Defines states for multi-step interactions:
- Support ticket creation
- Review submission
- Order management
"""

from aiogram.fsm.state import State, StatesGroup


class TicketStates(StatesGroup):
    """States for support ticket creation flow."""

    waiting_for_order_id = State()
    waiting_for_description = State()


class ReviewStates(StatesGroup):
    """States for review submission flow."""

    waiting_for_rating = State()
    waiting_for_text = State()


class RefundStates(StatesGroup):
    """States for refund request flow."""

    waiting_for_order_id = State()
    waiting_for_reason = State()
