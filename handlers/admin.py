"""
Хендлеры, доступные только жене (WIFE_CHAT_ID):
/add       — добавить заготовку (мясо / гарнир / салат)
/list      — посмотреть текущие остатки
/edit      — изменить количество мясной заготовки ИЛИ переименовать (мясо/гарнир/салат)
/delete    — удалить позицию (мясо/гарнир/салат) с множественным выбором
/setgarnish — изменить список гарниров для мясной заготовки
/settime   — задать время ежедневной рассылки мужу
/ask       — отправить мужу вопрос прямо сейчас (вручную, без ожидания расписания)
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import AddItem, EditItem, EditGarnishes, SetTime
from config import WIFE_CHAT_ID

router = Router()
router.message.filter(F.from_user.id == WIFE_CHAT_ID)
router.callback_query.filter(F.from_user.id == WIFE_CHAT_ID)


# ---------- Отмена ----------

@router.callback_query(F.data == kb.CANCEL_CALLBACK)
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена через кнопку для жены."""
    current_state = await state.get_state()
    if current_state is None:
        await callback.answer("Нет активных действий")
        return

    await state.clear()
    await callback.message.delete()
    await callback.answer()
    await callback.message.answer("Отменено ✅")


# ---------- Назад ----------

@router.callback_query(F.data == kb.BACK_CALLBACK)
async def back_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Назад' для жены."""
    current_state = await state.get_state()
    data = await state.get_data()

    # ---- Редактирование ----
    if current_state == EditItem.choose_item:
        # Возвращаемся к выбору категории
        await state.set_state(EditItem.choose_category)
        await callback.message.edit_text(
            "Что редактируем?",
            reply_markup=kb.category_keyboard(prefix="editcat", show_back=False)
        )
        await callback.answer()
        return

    if current_state == EditItem.new_name or current_state == EditItem.new_quantity:
        # Возвращаемся к выбору действия для мяса или к списку элементов
        item_type = data.get("item_type")
        item_id = data.get("item_id")
        category = data.get("edit_category", "meat")

        if item_type == "meat" and item_id:
            item = await db.get_item_by_id(item_id)
            if item:
                await state.set_state(EditItem.choose_item)
                action_keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="📝 Переименовать", callback_data=f"rename_meat:{item_id}")],
                        [InlineKeyboardButton(text="🔢 Изменить количество", callback_data=f"change_qty:{item_id}")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
                        [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
                    ]
                )
                await callback.message.edit_text(
                    f"Что сделать с «{item['name']}»?",
                    reply_markup=action_keyboard
                )
                await callback.answer()
                return

        # Для гарниров и салатов возвращаемся к списку
        await state.set_state(EditItem.choose_item)

        if category == "garnish":
            items = await db.get_garnishes()
            if items:
                await callback.message.edit_text(
                    "Какой гарнир переименовать?",
                    reply_markup=kb.simple_edit_keyboard(items, "edit_garnish")
                )
            else:
                await state.clear()
                await callback.message.edit_text("Гарниров нет.")
        elif category == "salad":
            items = await db.get_salads()
            if items:
                await callback.message.edit_text(
                    "Какой салат переименовать?",
                    reply_markup=kb.simple_edit_keyboard(items, "edit_salad")
                )
            else:
                await state.clear()
                await callback.message.edit_text("Салатов нет.")
        else:
            # Для мяса возвращаемся к списку мяса
            items = await db.get_all_items()
            if items:
                await state.set_state(EditItem.choose_item)
                await callback.message.edit_text(
                    "Какую заготовку редактируем?",
                    reply_markup=kb.items_edit_keyboard(items, "edit_meat")
                )
            else:
                await state.clear()
                await callback.message.edit_text("Мясных заготовок нет.")

        await callback.answer()
        return

    if current_state == EditItem.choose_category:
        # Возвращаемся в главное меню
        await state.clear()
        await callback.message.delete()
        await callback.answer()
        await callback.message.answer("Главное меню. Используй команды.")
        return

    # ---- Удаление ----
    if current_state == "delete_selecting":
        # Возвращаемся к выбору категории удаления
        await state.set_state("delete_category")
        await callback.message.edit_text(
            "Что удаляем?",
            reply_markup=kb.category_keyboard(prefix="delcat", show_back=False)
        )
        await callback.answer()
        return

    if current_state == "delete_category":
        # Возвращаемся в главное меню
        await state.clear()
        await callback.message.delete()
        await callback.answer()
        await callback.message.answer("Главное меню. Используй команды.")
        return

    # ---- Добавление ----
    if current_state == AddItem.category:
        # Возвращаемся в главное меню
        await state.clear()
        await callback.message.delete()
        await callback.answer()
        await callback.message.answer("Главное меню. Используй команды.")
        return

    if current_state == AddItem.name or current_state == AddItem.quantity or current_state == AddItem.choosing_garnishes:
        # Возвращаемся к выбору категории
        await state.set_state(AddItem.category)
        await callback.message.edit_text(
            "Что добавляем?",
            reply_markup=kb.category_keyboard(show_back=False)
        )
        await callback.answer()
        return

    # Для всех остальных случаев
    await state.clear()
    await callback.message.delete()
    await callback.answer()
    await callback.message.answer("Отменено ✅")


# ---------- /add ----------

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    await state.set_state(AddItem.category)
    await message.answer("Что добавляем?", reply_markup=kb.category_keyboard(show_back=False))


@router.callback_query(AddItem.category, F.data.startswith("cat:"))
async def add_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddItem.name)
    label = {"meat": "мясной заготовки", "garnish": "гарнира", "salad": "салата"}[category]

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        f"Введи название {label}:",
        reply_markup=back_keyboard
    )
    await callback.answer()


@router.message(AddItem.name)
async def add_name_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    category = data["category"]
    name = message.text.strip()

    if category == "garnish":
        await db.add_garnish(name)
        await state.clear()
        await message.answer(f"Готово ✅ Гарнир «{name}» добавлен.")
        return

    if category == "salad":
        await db.add_salad(name)
        await state.clear()
        await message.answer(f"Готово ✅ Салат «{name}» добавлен.")
        return

    await state.update_data(name=name)
    await state.set_state(AddItem.quantity)

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await message.answer(
        "Сколько порций/штук сейчас в наличии?",
        reply_markup=back_keyboard
    )


@router.message(AddItem.quantity)
async def add_quantity_entered(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Введи число, например: 4")
        return
    await state.update_data(quantity=int(message.text.strip()))

    garnishes = await db.get_garnishes()
    if not garnishes:
        data = await state.get_data()
        await db.add_meat_item(data["name"], data["quantity"])
        await state.clear()
        await message.answer(
            f"Готово ✅\n{data['name']} ({data['quantity']} шт) — "
            "гарниры можно будет добавить позже командой /setgarnish"
        )
        return

    await state.set_state(AddItem.choosing_garnishes)
    await state.update_data(selected_garnishes=set())
    await message.answer(
        "Выбери гарниры, которые можно подавать к этому мясу:\n"
        "(можно выбрать несколько, потом нажми ✅ Готово)",
        reply_markup=kb.garnishes_keyboard(garnishes),
    )


@router.callback_query(AddItem.choosing_garnishes, F.data == "garnish_done")
async def add_garnish_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = list(data.get("selected_garnishes", set()))

    if not selected_ids:
        await callback.answer("Выбери хотя бы один гарнир!", show_alert=True)
        return

    await db.add_meat_item(data["name"], data["quantity"], selected_ids)
    await state.clear()

    all_garnishes = await db.get_garnishes()
    garnish_names = [g["name"] for g in all_garnishes if g["id"] in selected_ids]

    await callback.message.edit_text(
        f"Готово ✅\n"
        f"{data['name']} ({data['quantity']} шт)\n"
        f"Доступные гарниры: {', '.join(garnish_names)}"
    )
    await callback.answer()


@router.callback_query(AddItem.choosing_garnishes, F.data.startswith("garnish_toggle:"))
async def add_garnish_toggle(callback: CallbackQuery, state: FSMContext):
    garnish_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_garnishes", set())

    if garnish_id in selected:
        selected.remove(garnish_id)
    else:
        selected.add(garnish_id)

    await state.update_data(selected_garnishes=selected)

    garnishes = await db.get_garnishes()
    await callback.message.edit_reply_markup(
        reply_markup=kb.garnishes_keyboard(garnishes, selected)
    )
    await callback.answer()


# ---------- /list ----------

@router.message(Command("list"))
async def cmd_list(message: Message):
    items = await db.get_all_items()
    garnishes = await db.get_garnishes()
    salads = await db.get_salads()

    lines = ["🥩 Мясо:"]
    if items:
        for item in items:
            meat_garnishes = await db.get_meat_garnishes(item["id"])
            garnish_names = [g["name"] for g in meat_garnishes]
            if garnish_names:
                lines.append(f"  • {item['name']}: {item['quantity']} → {', '.join(garnish_names)}")
            else:
                lines.append(f"  • {item['name']}: {item['quantity']} (без гарниров)")
    else:
        lines.append("  (пусто)")

    lines.append("\n🍚 Гарниры (всегда в наличии):")
    lines.append("  " + ", ".join(g["name"] for g in garnishes) if garnishes else "  (пусто)")

    lines.append("\n🥗 Салаты (всегда в наличии):")
    lines.append("  " + ", ".join(s["name"] for s in salads) if salads else "  (пусто)")

    await message.answer("\n".join(lines))


# ---------- /edit (изменить количество ИЛИ переименовать) ----------

@router.message(Command("edit"))
async def cmd_edit(message: Message, state: FSMContext):
    await state.set_state(EditItem.choose_category)
    await message.answer(
        "Что редактируем?",
        reply_markup=kb.category_keyboard(prefix="editcat", show_back=False)
    )


@router.callback_query(EditItem.choose_category, F.data.startswith("editcat:"))
async def edit_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(edit_category=category)

    if category == "meat":
        items = await db.get_all_items()
        if not items:
            await callback.message.edit_text("Мясных заготовок пока нет.")
            await state.clear()
            await callback.answer()
            return
        await state.set_state(EditItem.choose_item)
        await callback.message.edit_text(
            "Какую заготовку редактируем?",
            reply_markup=kb.items_edit_keyboard_with_back(items, "edit_meat")
        )
    elif category == "garnish":
        items = await db.get_garnishes()
        if not items:
            await callback.message.edit_text("Гарниров пока нет.")
            await state.clear()
            await callback.answer()
            return
        await state.set_state(EditItem.choose_item)
        await callback.message.edit_text(
            "Какой гарнир переименовать?",
            reply_markup=kb.simple_edit_keyboard_with_back(items, "edit_garnish")
        )
    else:  # salad
        items = await db.get_salads()
        if not items:
            await callback.message.edit_text("Салатов пока нет.")
            await state.clear()
            await callback.answer()
            return
        await state.set_state(EditItem.choose_item)
        await callback.message.edit_text(
            "Какой салат переименовать?",
            reply_markup=kb.simple_edit_keyboard_with_back(items, "edit_salad")
        )
    await callback.answer()


@router.callback_query(EditItem.choose_item, F.data.startswith("edit_meat:"))
async def edit_meat_item_chosen(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    item = await db.get_item_by_id(item_id)
    await state.update_data(item_id=item_id, item_name=item["name"], item_type="meat")

    action_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Переименовать", callback_data=f"rename_meat:{item_id}")],
            [InlineKeyboardButton(text="🔢 Изменить количество", callback_data=f"change_qty:{item_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        f"Что сделать с «{item['name']}»?",
        reply_markup=action_keyboard
    )
    await callback.answer()


@router.callback_query(EditItem.choose_item, F.data.startswith("edit_garnish:"))
async def edit_garnish_item_chosen(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    garnishes = await db.get_garnishes()
    item = next((g for g in garnishes if g["id"] == item_id), None)
    if not item:
        await callback.answer("Гарнир не найден", show_alert=True)
        return

    await state.update_data(item_id=item_id, item_name=item["name"], item_type="garnish")
    await state.set_state(EditItem.new_name)

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        f"Введи новое название для гарнира «{item['name']}»:",
        reply_markup=back_keyboard
    )
    await callback.answer()


@router.callback_query(EditItem.choose_item, F.data.startswith("edit_salad:"))
async def edit_salad_item_chosen(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    salads = await db.get_salads()
    item = next((s for s in salads if s["id"] == item_id), None)
    if not item:
        await callback.answer("Салат не найден", show_alert=True)
        return

    await state.update_data(item_id=item_id, item_name=item["name"], item_type="salad")
    await state.set_state(EditItem.new_name)

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        f"Введи новое название для салата «{item['name']}»:",
        reply_markup=back_keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rename_meat:"))
async def rename_meat_item(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    await state.update_data(item_id=item_id, item_type="meat")
    await state.set_state(EditItem.new_name)

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        "Введи новое название:",
        reply_markup=back_keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("change_qty:"))
async def change_quantity(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    await state.update_data(item_id=item_id)
    await state.set_state(EditItem.new_quantity)

    back_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=kb.BACK_CALLBACK)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)]
        ]
    )

    await callback.message.edit_text(
        "Сколько теперь в наличии? Введи число:",
        reply_markup=back_keyboard
    )
    await callback.answer()


@router.message(EditItem.new_name)
async def rename_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    item_id = data.get("item_id")
    item_type = data.get("item_type", "meat")
    new_name = message.text.strip()

    if not new_name:
        await message.answer("Название не может быть пустым. Попробуй снова:")
        return

    if item_type == "meat":
        await db.rename_item(item_id, new_name)
    elif item_type == "garnish":
        await db.rename_garnish(item_id, new_name)
    else:  # salad
        await db.rename_salad(item_id, new_name)

    await state.clear()
    await message.answer(f"Готово ✅ Переименовано в «{new_name}»")


@router.message(EditItem.new_quantity)
async def edit_quantity_entered(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Введи число, например: 3")
        return
    data = await state.get_data()
    await db.set_item_quantity(data["item_id"], int(message.text.strip()))
    await state.clear()
    await message.answer("Остаток обновлён ✅")


# ---------- /setgarnish ----------

@router.message(Command("setgarnish"))
async def cmd_setgarnish(message: Message, state: FSMContext):
    items = await db.get_all_items()
    if not items:
        await message.answer("Мясных заготовок пока нет — сначала добавь через /add.")
        return
    await state.set_state(EditGarnishes.choose_item)
    await message.answer(
        "Для какой заготовки изменить список гарниров?",
        reply_markup=kb.meat_edit_keyboard(items),
    )


@router.callback_query(EditGarnishes.choose_item, F.data.startswith("edit_garnish:"))
async def edit_garnish_item_chosen(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    item = await db.get_item_by_id(item_id)
    current_garnishes = await db.get_meat_garnishes(item_id)
    selected_ids = {g["id"] for g in current_garnishes}

    await state.update_data(meat_id=item_id, meat_name=item["name"])
    await state.set_state(EditGarnishes.choosing_garnishes)

    all_garnishes = await db.get_garnishes()
    if not all_garnishes:
        await callback.message.edit_text(
            "Гарниров в базе ещё нет — сначала добавь хотя бы один через /add → Гарнир."
        )
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Выбери гарниры для {item['name']} (можно несколько):",
        reply_markup=kb.garnishes_keyboard(all_garnishes, selected_ids),
    )
    await callback.answer()


@router.callback_query(EditGarnishes.choosing_garnishes, F.data == "garnish_done")
async def edit_garnish_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = list(data.get("selected_garnishes", set()))

    if not selected_ids:
        await callback.answer("Выбери хотя бы один гарнир!", show_alert=True)
        return

    await db.set_meat_garnishes(data["meat_id"], selected_ids)
    await state.clear()

    all_garnishes = await db.get_garnishes()
    garnish_names = [g["name"] for g in all_garnishes if g["id"] in selected_ids]

    await callback.message.edit_text(
        f"Готово ✅\n"
        f"Для {data['meat_name']} доступны гарниры: {', '.join(garnish_names)}"
    )
    await callback.answer()


@router.callback_query(EditGarnishes.choosing_garnishes, F.data.startswith("garnish_toggle:"))
async def edit_garnish_toggle(callback: CallbackQuery, state: FSMContext):
    garnish_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_garnishes", set())

    if garnish_id in selected:
        selected.remove(garnish_id)
    else:
        selected.add(garnish_id)

    await state.update_data(selected_garnishes=selected)

    all_garnishes = await db.get_garnishes()
    await callback.message.edit_reply_markup(
        reply_markup=kb.garnishes_keyboard(all_garnishes, selected)
    )
    await callback.answer()


# ---------- /delete (множественное удаление) ----------

# Хранилище для выбранных ID в процессе удаления
delete_selection = {}

@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext):
    await state.set_state("delete_category")
    await message.answer(
        "Что удаляем?",
        reply_markup=kb.category_keyboard(prefix="delcat", show_back=False)
    )


@router.callback_query(F.data.startswith("delcat:"))
async def delete_category_chosen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    chat_id = callback.from_user.id

    # Инициализируем выбор для этого пользователя
    if chat_id not in delete_selection:
        delete_selection[chat_id] = {"category": category, "selected": set(), "items": []}
    else:
        delete_selection[chat_id]["category"] = category
        delete_selection[chat_id]["selected"] = set()

    await state.update_data(delete_category=category)
    await state.set_state("delete_selecting")

    if category == "meat":
        items = await db.get_all_items()
        if not items:
            await callback.message.edit_text("Мясных заготовок пока нет.")
            await state.clear()
            await callback.answer()
            return
        delete_selection[chat_id]["items"] = items
        await callback.message.edit_text(
            "Выбери заготовки для удаления (можно несколько, потом нажми 🗑️ Удалить):",
            reply_markup=kb.delete_items_keyboard_with_back(items, set(), "del_meat")
        )
    elif category == "garnish":
        items = await db.get_garnishes()
        if not items:
            await callback.message.edit_text("Гарниров пока нет.")
            await state.clear()
            await callback.answer()
            return
        delete_selection[chat_id]["items"] = items
        await callback.message.edit_text(
            "Выбери гарниры для удаления (можно несколько, потом нажми 🗑️ Удалить):",
            reply_markup=kb.delete_items_keyboard_with_back(items, set(), "del_garnish")
        )
    else:  # salad
        items = await db.get_salads()
        if not items:
            await callback.message.edit_text("Салатов пока нет.")
            await state.clear()
            await callback.answer()
            return
        delete_selection[chat_id]["items"] = items
        await callback.message.edit_text(
            "Выбери салаты для удаления (можно несколько, потом нажми 🗑️ Удалить):",
            reply_markup=kb.delete_items_keyboard_with_back(items, set(), "del_salad")
        )
    await callback.answer()


@router.callback_query(F.data.startswith("del_meat:"))
async def delete_meat_toggle(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    chat_id = callback.from_user.id

    if chat_id not in delete_selection:
        await callback.answer("Ошибка, попробуй заново /delete", show_alert=True)
        return

    selected = delete_selection[chat_id]["selected"]
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.add(item_id)

    items = delete_selection[chat_id]["items"]
    await callback.message.edit_reply_markup(
        reply_markup=kb.delete_items_keyboard_with_back(items, selected, "del_meat")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_garnish:"))
async def delete_garnish_toggle(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    chat_id = callback.from_user.id

    if chat_id not in delete_selection:
        await callback.answer("Ошибка, попробуй заново /delete", show_alert=True)
        return

    selected = delete_selection[chat_id]["selected"]
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.add(item_id)

    items = delete_selection[chat_id]["items"]
    await callback.message.edit_reply_markup(
        reply_markup=kb.delete_items_keyboard_with_back(items, selected, "del_garnish")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_salad:"))
async def delete_salad_toggle(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    chat_id = callback.from_user.id

    if chat_id not in delete_selection:
        await callback.answer("Ошибка, попробуй заново /delete", show_alert=True)
        return

    selected = delete_selection[chat_id]["selected"]
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.add(item_id)

    items = delete_selection[chat_id]["items"]
    await callback.message.edit_reply_markup(
        reply_markup=kb.delete_items_keyboard_with_back(items, selected, "del_salad")
    )
    await callback.answer()


@router.callback_query(F.data == "delete_confirm")
async def delete_confirm(callback: CallbackQuery, state: FSMContext):
    chat_id = callback.from_user.id

    if chat_id not in delete_selection:
        await callback.answer("Ошибка, попробуй заново /delete", show_alert=True)
        return

    selected = delete_selection[chat_id]["selected"]
    category = delete_selection[chat_id]["category"]

    if not selected:
        await callback.answer("Выбери хотя бы один элемент!", show_alert=True)
        return

    # Удаляем выбранные элементы
    deleted_names = []
    if category == "meat":
        for item_id in selected:
            item = await db.get_item_by_id(item_id)
            if item:
                deleted_names.append(item["name"])
                await db.delete_item(item_id)
    elif category == "garnish":
        for item_id in selected:
            garnishes = await db.get_garnishes()
            garnish = next((g for g in garnishes if g["id"] == item_id), None)
            if garnish:
                deleted_names.append(garnish["name"])
                await db.delete_garnish(item_id)
    else:  # salad
        for item_id in selected:
            salads = await db.get_salads()
            salad = next((s for s in salads if s["id"] == item_id), None)
            if salad:
                deleted_names.append(salad["name"])
                await db.delete_salad(item_id)

    # Очищаем состояние и удаляем данные пользователя
    await state.clear()
    del delete_selection[chat_id]

    await callback.message.edit_text(
        f"Готово ✅ Удалено:\n" + "\n".join(f"• {name}" for name in deleted_names)
    )
    await callback.answer()


# ---------- /settime ----------

@router.message(Command("settime"))
async def cmd_settime(message: Message, state: FSMContext):
    await state.set_state(SetTime.waiting_time)
    await message.answer(
        "В какое время каждый день присылать мужу вопрос «Что едим сегодня?»?\n"
        "Введи в формате ЧЧ:ММ, например: 16:30"
    )


@router.message(SetTime.waiting_time)
async def settime_entered(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    parts = text.split(":")
    valid = (
        len(parts) == 2
        and parts[0].isdigit()
        and parts[1].isdigit()
        and 0 <= int(parts[0]) <= 23
        and 0 <= int(parts[1]) <= 59
    )
    if not valid:
        await message.answer("Не похоже на время. Введи в формате ЧЧ:ММ, например: 16:30")
        return

    await db.set_setting("schedule_time", text)
    await state.clear()

    from scheduler import reschedule_daily_job
    reschedule_daily_job(bot, text)

    await message.answer(f"Готово ✅ Теперь вопрос будет приходить каждый день в {text}")


# ---------- /ask ----------

@router.message(Command("ask"))
async def cmd_ask_now(message: Message, bot: Bot):
    from handlers.daily import send_daily_question_forced
    await send_daily_question_forced(bot)
    await message.answer("Отправила мужу вопрос прямо сейчас ✅")


# ---------- /start и /help ----------

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Это бот для планирования готовки 🍳\n\n"
        "Загружай сюда заготовки из морозилки, а мужу бот будет сам "
        "присылать вопрос, что приготовить.\n\n"
        "Список всех команд — /help"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Управление заготовками:</b>\n"
        "/add — добавить заготовку (мясо, гарнир или салат)\n"
        "/list — посмотреть все текущие остатки\n"
        "/edit — изменить количество или переименовать (мясо/гарнир/салат)\n"
        "/setgarnish — изменить список разрешённых гарниров для мяса\n"
        "/delete — удалить позиции (множественный выбор)\n\n"
        "<b>Рассылка мужу:</b>\n"
        "/settime — во сколько каждый день присылать вопрос «Что едим сегодня?»\n"
        "/ask — отправить этот вопрос прямо сейчас, не дожидаясь расписания\n\n"
        "<b>Прочее:</b>\n"
        "/start — приветственное сообщение\n"
        "/help — этот список команд"
    )