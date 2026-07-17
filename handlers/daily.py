"""
Флоу для мужа (HUSBAND_CHAT_ID):
1. Бот присылает вопрос "Что едим сегодня?" с кнопками мяса + "Доставка"
2а. Если у мяса есть разрешённые гарниры — показываем только их
2б. Если у мяса нет разрешённых гарниров — показываем все гарниры
2в. Если выбрана "Доставка" — спрашиваем текст заказа -> пересылаем жене, остатки не трогаем
3. После подтверждения: вычитаем 1 из остатка мяса, логируем, шлём жене итоговое сообщение
"""

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime

import database as db
import keyboards as kb
from states import DailyMeal
from config import HUSBAND_CHAT_ID, WIFE_CHAT_ID

router = Router()
router.message.filter(F.from_user.id == HUSBAND_CHAT_ID)
router.callback_query.filter(F.from_user.id == HUSBAND_CHAT_ID)


async def send_daily_question(bot: Bot):
    """Вызывается планировщиком (или вручную через /ask жены)."""
    meats = await db.get_meats_in_stock()
    if not meats:
        await bot.send_message(
            HUSBAND_CHAT_ID,
            "Мясного в запасах не осталось 😅 Выбирай сам, что готовить, "
            "либо жми сюда, если хочется заказать что-то на стороне.",
            reply_markup=kb.meats_keyboard([]),
        )
        return
    await bot.send_message(
        HUSBAND_CHAT_ID, "Че едим сегодня?)", reply_markup=kb.meats_keyboard(meats)
    )


async def send_daily_question_forced(bot: Bot):
    """Принудительно отправляет вопрос (без проверки на сегодняшний выбор)."""
    meats = await db.get_meats_in_stock()
    if not meats:
        await bot.send_message(
            HUSBAND_CHAT_ID,
            "Мясного в запасах не осталось 😅 Выбирай сам, что готовить, "
            "либо жми сюда, если хочется заказать что-то на стороне.",
            reply_markup=kb.meats_keyboard([]),
        )
        return
    await bot.send_message(
        HUSBAND_CHAT_ID, "Че едим сегодня?)", reply_markup=kb.meats_keyboard(meats)
    )


async def cancel_dialog(message_or_callback, state: FSMContext):
    """Универсальная функция отмены диалога."""
    current_state = await state.get_state()
    if current_state is None:
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.answer("Нет активных действий")
        else:
            await message_or_callback.answer("У тебя нет активных действий 😊")
        return

    await state.clear()

    if hasattr(message_or_callback, 'message'):
        await message_or_callback.message.delete()
        await message_or_callback.answer()
        await message_or_callback.message.answer("Отменено ✅")
    else:
        await message_or_callback.answer("Отменено ✅", reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data == kb.CANCEL_CALLBACK)
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена через кнопку."""
    await cancel_dialog(callback, state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена через команду."""
    await cancel_dialog(message, state)


@router.message(Command("food"))
async def cmd_food(message: Message, state: FSMContext, bot: Bot):
    """Принудительный запрос выбора блюда."""
    current_state = await state.get_state()

    if current_state:
        await message.answer(
            "Пожалуйста, используй кнопки для выбора 👆\n"
            "Или нажми ❌ Отмена"
        )
        await resend_current_question(message, state)
    else:
        await send_daily_question_forced(bot)


@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    await message.answer(
        "Привет! Я буду каждый день спрашивать, что приготовить 🍳",
        reply_markup=kb.start_keyboard()
    )


@router.callback_query(F.data == "start_choose")
async def start_choose_callback(callback: CallbackQuery, bot: Bot):
    """Обработка кнопки 'Выбрать сейчас' из приветствия."""
    await callback.answer()
    await callback.message.delete()
    await send_daily_question(bot)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "/food — выбрать блюдо прямо сейчас\n"
        "/cancel — отменить текущий выбор\n"
        "/start — приветственное сообщение"
    )


# ---------- Кнопка "Назад" ----------

@router.callback_query(F.data == kb.BACK_CALLBACK)
async def back_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка кнопки "Назад"."""
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == DailyMeal.choosing_garnish:
        await state.clear()
        await callback.answer()
        await callback.message.delete()
        await send_daily_question(bot)

    elif current_state == DailyMeal.choosing_salad:
        meat_id = data.get("meat_id")
        meat_name = data.get("meat_name", "Блюдо")

        if not meat_id:
            await state.clear()
            await send_daily_question(bot)
            await callback.answer()
            await callback.message.delete()
            return

        meat_garnishes = await db.get_meat_garnishes(meat_id)

        if meat_garnishes:
            await state.set_state(DailyMeal.choosing_garnish)
            await callback.message.edit_text(
                f"{meat_name}. Какой гарнир? (доступны только разрешённые)",
                reply_markup=kb.garnishes_simple_keyboard(meat_garnishes, show_back=True),
            )
        else:
            all_garnishes = await db.get_garnishes()
            if all_garnishes:
                await state.set_state(DailyMeal.choosing_garnish)
                await callback.message.edit_text(
                    f"{meat_name}. Какой гарнир?",
                    reply_markup=kb.garnishes_simple_keyboard(all_garnishes, show_back=True),
                )
            else:
                await state.clear()
                await send_daily_question(bot)

        await callback.answer()

    else:
        await state.clear()
        await send_daily_question(bot)
        await callback.answer()
        await callback.message.delete()


# ---------- Доставка ----------

@router.callback_query(F.data == kb.DELIVERY_CALLBACK)
async def delivery_chosen(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DailyMeal.delivery_request)

    cancel_markup = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)
        ]]
    )

    await callback.message.edit_text(
        "Что хочешь заказать? Напиши прямо сюда 🚚\n"
        "Или нажми ❌ Отмена, чтобы отменить",
        reply_markup=cancel_markup
    )
    await callback.answer()


@router.message(DailyMeal.delivery_request)
async def delivery_text_entered(message: Message, state: FSMContext, bot: Bot):
    """Обработка текста заказа."""
    if not message.text:
        await message.answer(
            "Пожалуйста, напиши текстом, что хочешь заказать 📝\n"
            "Или нажми ❌ Отмена"
        )
        return

    request_text = message.text.strip()
    await db.log_meal(is_delivery=True, delivery_request=request_text)
    await state.clear()
    await message.answer("Заказ передал ✅")
    await bot.send_message(
        WIFE_CHAT_ID, f"🚚 Муж хочет заказать доставку:\n«{request_text}»"
    )


# ---------- Выбор мяса ----------

@router.callback_query(F.data.startswith("meat:"))
async def meat_chosen(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state and current_state != DailyMeal.choosing_garnish.state:
        await callback.answer("Сначала заверши текущий выбор", show_alert=True)
        return

    item_id = int(callback.data.split(":")[1])
    item = await db.get_item_by_id(item_id)
    if not item:
        await callback.answer("Эта позиция уже недоступна, выбери другую", show_alert=True)
        return

    # Получаем время отмены из БД
    cancel_minutes = await db.get_cancel_window_minutes()

    # Проверяем последний незафиксированный выбор
    last_choice = await db.get_last_unfinalized_choice()

    if last_choice and last_choice["meat_id"] != item_id:
        minutes_passed = (datetime.now() - datetime.fromisoformat(last_choice["selected_at"])).total_seconds() / 60

        if minutes_passed < cancel_minutes:
            await db.cancel_choice(last_choice["id"])
            await callback.message.answer(
                f"✅ Предыдущий выбор «{last_choice['meat_name']}» отменён, остатки возвращены"
            )
        else:
            await callback.message.answer(
                f"⏰ Время на изменение выбора истекло. «{last_choice['meat_name']}» уже зафиксирован."
            )

    await state.update_data(meat_id=item["id"], meat_name=item["name"])

    meat_garnishes = await db.get_meat_garnishes(item_id)

    if meat_garnishes:
        await state.set_state(DailyMeal.choosing_garnish)
        await callback.message.edit_text(
            f"{item['name']}. Какой гарнир? (доступны только разрешённые)",
            reply_markup=kb.garnishes_simple_keyboard(meat_garnishes, show_back=True),
        )
        await callback.answer()
        return

    all_garnishes = await db.get_garnishes()
    if not all_garnishes:
        await state.update_data(garnish_name=None)
        salads = await db.get_salads()
        if not salads:
            await callback.message.edit_text(
                "Салатов в базе нет — попроси жену добавить хотя бы один через /add."
            )
            await state.clear()
            await callback.answer()
            return
        await state.set_state(DailyMeal.choosing_salad)
        await callback.message.edit_text(
            f"{item['name']}. Какой салат?",
            reply_markup=kb.salads_keyboard(salads, show_back=True),
        )
        await callback.answer()
        return

    await state.set_state(DailyMeal.choosing_garnish)
    await callback.message.edit_text(
        f"{item['name']}. Какой гарнир?",
        reply_markup=kb.garnishes_simple_keyboard(all_garnishes, show_back=True),
    )
    await callback.answer()


# ---------- Выбор гарнира ----------

@router.callback_query(DailyMeal.choosing_garnish, F.data.startswith("garnish:"))
async def garnish_chosen(callback: CallbackQuery, state: FSMContext):
    garnish_id = int(callback.data.split(":")[1])
    garnishes = await db.get_garnishes()
    garnish = next((g for g in garnishes if g["id"] == garnish_id), None)

    if not garnish:
        await callback.answer("Гарнир не найден, попробуй снова", show_alert=True)
        return

    await state.update_data(garnish_name=garnish["name"])

    salads = await db.get_salads()
    if not salads:
        await callback.message.edit_text(
            "Салатов в базе нет — попроси жену добавить хотя бы один через /add."
        )
        await state.clear()
        await callback.answer()
        return

    await state.set_state(DailyMeal.choosing_salad)
    await callback.message.edit_text(
        "Какой салат?",
        reply_markup=kb.salads_keyboard(salads, show_back=True)
    )
    await callback.answer()


# ---------- Выбор салата ----------

@router.callback_query(DailyMeal.choosing_salad, F.data.startswith("salad:"))
async def salad_chosen(callback: CallbackQuery, state: FSMContext):
    salad_id = int(callback.data.split(":")[1])
    salads = await db.get_salads()
    salad = next((s for s in salads if s["id"] == salad_id), None)
    await state.update_data(salad_name=salad["name"] if salad else None)

    data = await state.get_data()
    await state.set_state(DailyMeal.confirming)

    if data.get("garnish_name"):
        confirm_text = f"{data['meat_name']} + {data['garnish_name']} + {data['salad_name']} — точно?"
    else:
        confirm_text = f"{data['meat_name']} + {data['salad_name']} (без гарнира) — точно?"

    await callback.message.edit_text(
        confirm_text,
        reply_markup=kb.confirm_keyboard(),
    )
    await callback.answer()


# ---------- Подтверждение ----------

@router.callback_query(DailyMeal.confirming, F.data == "confirm:no")
async def confirm_no(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    await state.clear()
    await callback.answer()
    await send_daily_question(bot)


@router.callback_query(DailyMeal.confirming, F.data == "confirm:yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    if not data or "meat_id" not in data:
        await callback.answer("Этот выбор уже обработан", show_alert=True)
        await callback.message.delete()
        return

    # Получаем время отмены из БД
    cancel_minutes = await db.get_cancel_window_minutes()
    hours = cancel_minutes // 60
    minutes = cancel_minutes % 60

    if hours > 0 and minutes > 0:
        time_text = f"{hours} ч {minutes} мин"
    elif hours > 0:
        time_text = f"{hours} ч"
    else:
        time_text = f"{minutes} мин"

    # Проверяем ещё раз последний незафиксированный выбор
    last_choice = await db.get_last_unfinalized_choice()

    if last_choice and last_choice["meat_id"] != data["meat_id"]:
        minutes_passed = (datetime.now() - datetime.fromisoformat(last_choice["selected_at"])).total_seconds() / 60

        if minutes_passed < cancel_minutes:
            await db.cancel_choice(last_choice["id"])
            await callback.message.answer(
                f"✅ Предыдущий выбор «{last_choice['meat_name']}» отменён, остатки возвращены"
            )
        else:
            await callback.message.answer(
                f"⏰ Время на изменение выбора истекло. «{last_choice['meat_name']}» уже зафиксирован."
            )

    # Списываем текущее мясо
    await db.decrement_item(data["meat_id"], amount=1)

    # Сохраняем выбор в лог с meat_id для возможности возврата
    await db.save_choice_with_meat_id(
        meat_id=data["meat_id"],
        meat_name=data["meat_name"],
        garnish_name=data.get("garnish_name"),
        salad_name=data["salad_name"],
    )

    item = await db.get_item_by_id(data["meat_id"])
    await state.clear()

    await callback.message.delete()
    await callback.answer()

    # Формируем сообщение для мужа
    if data.get("garnish_name"):
        meal_text = f"{data['meat_name']} + {data['garnish_name']} + {data['salad_name']}"
    else:
        meal_text = f"{data['meat_name']} + {data['salad_name']} (без гарнира)"

    change_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✏️ Изменить выбор", callback_data="change_choice")
        ]]
    )

    await callback.message.answer(
        f"Вы выбрали {meal_text}, приятного аппетита! 🍽️\n\n"
        f"У вас есть {time_text}, чтобы изменить выбор.\n"
        f"Если вы передумали, нажмите кнопку ниже",
        reply_markup=change_keyboard
    )

    # Отправляем жене
    if data.get("garnish_name"):
        summary = (
            f"🍽 Сегодня муж выбрал:\n"
            f"{data['meat_name']} + {data['garnish_name']} + {data['salad_name']}"
        )
    else:
        summary = (
            f"🍽 Сегодня муж выбрал:\n"
            f"{data['meat_name']} + {data['salad_name']} (без гарнира)"
        )

    if item and item["quantity"] == 0:
        summary += f"\n\n⚠️ {data['meat_name']} закончились — пора докупить."

    summary += f"\n\n⏰ У мужа есть {time_text} на изменение выбора."

    await bot.send_message(WIFE_CHAT_ID, summary)


# ---------- Кнопка "Изменить выбор" ----------

@router.callback_query(F.data == "change_choice")
async def change_choice_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка кнопки 'Изменить выбор'."""
    last_choice = await db.get_last_unfinalized_choice()

    if last_choice:
        cancel_minutes = await db.get_cancel_window_minutes()
        minutes_passed = (datetime.now() - datetime.fromisoformat(last_choice["selected_at"])).total_seconds() / 60

        if minutes_passed >= cancel_minutes:
            hours = cancel_minutes // 60
            minutes = cancel_minutes % 60
            if hours > 0 and minutes > 0:
                time_text = f"{hours} ч {minutes} мин"
            elif hours > 0:
                time_text = f"{hours} ч"
            else:
                time_text = f"{minutes} мин"

            await callback.answer(
                f"⏰ Время на изменение выбора истекло (прошло {time_text}).",
                show_alert=True
            )
            await callback.message.edit_reply_markup(reply_markup=None)
            return

    await callback.answer()
    await callback.message.delete()
    await state.clear()
    await send_daily_question_forced(bot)


# ---------- Обработчики для всего остального ----------

async def resend_current_question(message: Message, state: FSMContext):
    """Повторно отправляет текущий вопрос с актуальными кнопками."""
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == DailyMeal.choosing_garnish:
        meat_name = data.get("meat_name", "Блюдо")
        meat_id = data.get("meat_id")
        if meat_id:
            meat_garnishes = await db.get_meat_garnishes(meat_id)
            if meat_garnishes:
                await message.answer(
                    f"{meat_name}. Какой гарнир? (доступны только разрешённые)",
                    reply_markup=kb.garnishes_simple_keyboard(meat_garnishes, show_back=True),
                )
                return

        all_garnishes = await db.get_garnishes()
        if all_garnishes:
            await message.answer(
                f"{meat_name}. Какой гарнир?",
                reply_markup=kb.garnishes_simple_keyboard(all_garnishes, show_back=True),
            )
        else:
            salads = await db.get_salads()
            if salads:
                await state.set_state(DailyMeal.choosing_salad)
                await message.answer(
                    f"{meat_name}. Какой салат?",
                    reply_markup=kb.salads_keyboard(salads, show_back=True),
                )
            else:
                await state.clear()
                await message.answer("Извини, что-то пошло не так. Начни заново через /food")

    elif current_state == DailyMeal.choosing_salad:
        meat_name = data.get("meat_name", "Блюдо")
        salads = await db.get_salads()
        if salads:
            await message.answer(
                f"{meat_name}. Какой салат?",
                reply_markup=kb.salads_keyboard(salads, show_back=True),
            )
        else:
            await state.clear()
            await message.answer("Салатов нет в базе. Начни заново через /food")

    elif current_state == DailyMeal.confirming:
        meat_name = data.get("meat_name", "")
        garnish_name = data.get("garnish_name")
        salad_name = data.get("salad_name", "")

        if garnish_name:
            confirm_text = f"{meat_name} + {garnish_name} + {salad_name} — точно?"
        else:
            confirm_text = f"{meat_name} + {salad_name} (без гарнира) — точно?"

        await message.answer(
            confirm_text,
            reply_markup=kb.confirm_keyboard(),
        )

    elif current_state == DailyMeal.delivery_request:
        cancel_markup = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отмена", callback_data=kb.CANCEL_CALLBACK)
            ]]
        )
        await message.answer(
            "Что хочешь заказать? Напиши прямо сюда 🚚\n"
            "Или нажми ❌ Отмена, чтобы отменить",
            reply_markup=cancel_markup
        )
    else:
        await state.clear()
        await send_daily_question(message.bot)


@router.message()
async def handle_unknown(message: Message, state: FSMContext, bot: Bot):
    """Обработчик для всего, что не попадёт в другие хендлеры."""
    current_state = await state.get_state()

    if current_state:
        await message.answer(
            "Пожалуйста, используй кнопки для выбора 👆\n"
            "Или нажми ❌ Отмена"
        )
        await resend_current_question(message, state)
    else:
        pass