from aiogram.fsm.state import State, StatesGroup


class AddItem(StatesGroup):
    """Диалог добавления новой заготовки (мясо/гарнир/салат)."""
    category = State()
    name = State()
    quantity = State()
    choosing_garnishes = State()


class EditItem(StatesGroup):
    """Диалог изменения мясной заготовки."""
    choose_category = State()
    choose_item = State()
    new_name = State()
    new_quantity = State()


class EditGarnishes(StatesGroup):
    """Диалог изменения списка гарниров для мясной заготовки."""
    choose_item = State()
    choosing_garnishes = State()


class SetTime(StatesGroup):
    """Диалог настройки времени."""
    waiting_time = State()              # для /settime
    waiting_reminder_time = State()     # для /setreminder
    waiting_cancel_time = State()       # для /setcancel


class DailyMeal(StatesGroup):
    """Диалог выбора блюда мужем."""
    choosing_garnish = State()
    choosing_salad = State()
    confirming = State()
    delivery_request = State()