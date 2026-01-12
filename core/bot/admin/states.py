"""
FSM States for Admin Bot

Defines conversation states for broadcast creation flow.
"""

from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    """States for broadcast creation flow"""

    # Step 1: Select target bot
    select_bot = State()

    # Step 2: Select audience
    select_audience = State()

    # Step 3: Select languages
    select_languages = State()

    # Step 4: Enter content for each language
    enter_content = State()

    # Step 5: Optional media upload
    upload_media = State()

    # Step 6: Optional buttons
    add_buttons = State()

    # Step 7: Preview & confirm
    preview = State()

    # Step 8: Schedule or send
    schedule = State()
