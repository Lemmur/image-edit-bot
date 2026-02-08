"""FSM состояния для Telegram бота"""

from aiogram.fsm.state import State, StatesGroup


class ImageEditStates(StatesGroup):
    """Состояния для процесса редактирования изображений"""
    
    # Ожидание изображения от пользователя
    waiting_for_image = State()
    
    # Ожидание positive prompt
    waiting_for_prompt = State()
    
    # Ожидание negative prompt (опционально)
    waiting_for_negative = State()
    
    # Настройка параметров генерации
    configuring_params = State()
    
    # Подтверждение задачи перед запуском
    confirming = State()
