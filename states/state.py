# Состояния FSM
from aiogram.fsm.state import StatesGroup, State


class UserState(StatesGroup):
    selected_buttons = State()  # Состояние для хранения выбранных кнопок
    selected_names = State()  # Состояние для хранения выбранных названий
    years = State()
    graf = State()