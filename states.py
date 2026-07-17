from aiogram.fsm.state import State, StatesGroup


class AddItem(StatesGroup):
    """Диалог добавления новой заготовки (мясо/гарнир/салат)."""
    category = State()
    name = State()
    quantity = State()              # только для мяса
    choosing_garnishes = State()    # только для мяса — выбор разрешённых гарниров


class EditItem(StatesGroup):
    """Диалог изменения мясной заготовки."""
    choose_category = State()       # выбор категории для редактирования
    choose_item = State()
    new_name = State()              # для переименования
    new_quantity = State()          # для изменения количества


class EditGarnishes(StatesGroup):
    """Диалог изменения списка гарниров для мясной заготовки."""
    choose_item = State()
    choosing_garnishes = State()


class SetTime(StatesGroup):
    """Диалог настройки времени ежедневной рассылки."""
    waiting_time = State()


class DailyMeal(StatesGroup):
    """Диалог выбора блюда мужем."""
    choosing_garnish = State()
    choosing_salad = State()
    confirming = State()
    delivery_request = State()