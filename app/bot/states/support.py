from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SupportRequestStates(StatesGroup):
    waiting_for_message = State()
