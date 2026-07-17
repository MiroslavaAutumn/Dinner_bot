from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

DELIVERY_CALLBACK = "meat:delivery"
CANCEL_CALLBACK = "cancel"
BACK_CALLBACK = "back"


def category_keyboard(prefix: str = "cat", show_back: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории (мясо/гарнир/салат)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🥩 Мясо", callback_data=f"{prefix}:meat")
    builder.button(text="🍚 Гарнир", callback_data=f"{prefix}:garnish")
    builder.button(text="🥗 Салат", callback_data=f"{prefix}:salad")

    if show_back:
        builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)

    if show_back:
        builder.adjust(1)  # один столбик
    else:
        builder.adjust(1)  # один столбик
    return builder.as_markup()


def yes_no_keyboard(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=yes_cb)
    builder.button(text="Нет", callback_data=no_cb)
    builder.adjust(2)
    return builder.as_markup()


def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🍽️ Выбрать сейчас", callback_data="start_choose")
    builder.adjust(1)
    return builder.as_markup()


def meats_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура выбора мяса для мужа — все в один столбик."""
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=f"{item['name']} ({item['quantity']})",
            callback_data=f"meat:{item['id']}",
        )
    builder.button(text="🚚 Доставка", callback_data=DELIVERY_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def garnishes_simple_keyboard(garnishes: list[dict], show_back: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора гарнира для мужа — все в один столбик."""
    builder = InlineKeyboardBuilder()
    for g in garnishes:
        builder.button(text=g["name"], callback_data=f"garnish:{g['id']}")
    if show_back:
        builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def garnishes_keyboard(garnishes: list[dict], selected_ids: set[int] | None = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора гарниров с возможностью множественного выбора (для жены)."""
    builder = InlineKeyboardBuilder()
    selected_ids = selected_ids or set()
    for g in garnishes:
        check = " ✅" if g["id"] in selected_ids else ""
        builder.button(
            text=f"{g['name']}{check}",
            callback_data=f"garnish_toggle:{g['id']}",
        )
    builder.button(text="✅ Готово", callback_data="garnish_done")
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def salads_keyboard(salads: list[dict], show_back: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора салата для мужа — все в один столбик."""
    builder = InlineKeyboardBuilder()
    for s in salads:
        builder.button(text=s["name"], callback_data=f"salad:{s['id']}")
    if show_back:
        builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Точно", callback_data="confirm:yes")
    builder.button(text="↩️ Выбрать заново", callback_data="confirm:no")
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def delete_items_keyboard(items: list[dict], selected_ids: set[int], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура для множественного удаления (без кнопки Назад)."""
    builder = InlineKeyboardBuilder()
    for item in items:
        check = " ✅" if item["id"] in selected_ids else ""
        builder.button(
            text=f"{item['name']}{check}",
            callback_data=f"{prefix}:{item['id']}",
        )
    builder.button(text="🗑️ Удалить выбранные", callback_data="delete_confirm")
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def delete_items_keyboard_with_back(items: list[dict], selected_ids: set[int], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура для множественного удаления с кнопкой Назад."""
    builder = InlineKeyboardBuilder()
    for item in items:
        check = " ✅" if item["id"] in selected_ids else ""
        builder.button(
            text=f"{item['name']}{check}",
            callback_data=f"{prefix}:{item['id']}",
        )
    builder.button(text="🗑️ Удалить выбранные", callback_data="delete_confirm")
    builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def items_edit_keyboard(items: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора позиции для редактирования (без кнопки Назад)."""
    builder = InlineKeyboardBuilder()
    for item in items:
        label = f"{item['name']} ({item.get('quantity', '')})".replace(" ()", "")
        builder.button(text=label, callback_data=f"{prefix}:{item['id']}")
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def items_edit_keyboard_with_back(items: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора позиции для редактирования с кнопкой Назад."""
    builder = InlineKeyboardBuilder()
    for item in items:
        label = f"{item['name']} ({item.get('quantity', '')})".replace(" ()", "")
        builder.button(text=label, callback_data=f"{prefix}:{item['id']}")
    builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def simple_edit_keyboard(items: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора элемента для переименования (без кнопки Назад)."""
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=item["name"], callback_data=f"{prefix}:{item['id']}")
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def simple_edit_keyboard_with_back(items: list[dict], prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора элемента для переименования с кнопкой Назад."""
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=item["name"], callback_data=f"{prefix}:{item['id']}")
    builder.button(text="🔙 Назад", callback_data=BACK_CALLBACK)
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def meat_edit_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(
            text=f"{item['name']} ({item['quantity']})",
            callback_data=f"edit_garnish:{item['id']}",
        )
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)  # один столбик
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=CANCEL_CALLBACK)
    builder.adjust(1)
    return builder.as_markup()