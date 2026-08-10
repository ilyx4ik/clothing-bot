from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, InviteCode, Categories, Item, SupportTicket
from utils.watermark import add_watermark_on_photo
from datetime import datetime

# Импорты клавиатур
from keyboards.builders import (
    items_keyboard, categories_keyboard, item_details_keyboard, 
    basket_keyboard, my_items_keyboard, my_item_details_keyboard, 
    main_user_kb, catalog_type_kb, parser_menu_kb, item_card_keyboard, 
    brands_keyboard, account_keyboard, authenticity_kb, skip_tags_kb, support_keyboard,
    get_admin_reply_keyboard
)

# Импорты запросов к базе данных
from database.requests import (
    get_item, add_to_basket, get_basket, clear_basket, add_item, 
    get_items_by_category, get_users_items, delete_item, get_brands_by_category, 
    get_items_by_category_and_brand, get_user, update_user_profile, set_user,
    delete_from_basket, get_watermark_setting, get_sniper_filter_setting, add_sniper_filter, get_user, close_ticket, 
    create_support_ticket, get_ticket_by_id
)

from states import OrderForm, AddItem, UserProfile, RegistrationStates, AddSniper, SupportFSM
from database.db import async_session
from handlers.admin import admin_keyboard, ADMIN_ID

router = Router()


@router.message(Command("support"))
@router.message(F.text == "🆘 Поддержка")
async def support_user(message: Message, state: FSMContext):
    await state.set_state(SupportFSM.waiting_for_user_issue)
    await message.answer("Опишите вашу проблему или отправьте скриншот:")


# 2. Прием обращения от юзера
@router.message(SupportFSM.waiting_for_user_issue)
async def process_support_user(message: Message, state: FSMContext):
    # Достаем данные
    user_text = message.text or message.caption or "Без описания"
    photo_id = message.photo[-1].file_id if message.photo else None

    # Создаем тикет в БД
    ticket_id = await create_support_ticket(
        user_tg_id=message.from_user.id, 
        text=user_text, 
        file_id=photo_id
    )

    # Текст для админа
    text_for_admin = (
        f"🆘 \bНовый тикет №{ticket_id}!\b\n\n"
        f"👤 От: @{message.from_user.username or 'без_юзернейма'} (ID: <code>{message.from_user.id}</code>)\n"
        f"📝 Текст: {user_text}"
    )

    # Отправляем админу с кнопкой ответа
    await message.bot.send_message(
        chat_id=ADMIN_ID, 
        text=text_for_admin, 
        reply_markup=get_admin_reply_keyboard(ticket_id),
        parse_mode="HTML"
    )

    await state.clear()
    await message.answer(f"✅ Ваш тикет №{ticket_id} принят! Ожидайте ответа.")


# 3. Нажатие Админа на «Ответить»
@router.callback_query(F.data.startswith("reply_ticket:"))
async def reply_admin(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split(":")[1])
    ticket = await get_ticket_by_id(ticket_id)

    if not ticket:
        await callback.answer("❌ Тикет не найден в базе!", show_alert=True)
        return

    # Сохраняем ID целевого юзера и номер тикета в FSM админа
    await state.update_data(target_user_id=ticket.user_id, ticket_id=ticket.id)
    await state.set_state(SupportFSM.waiting_for_admin_reply)

    await callback.message.answer(f"✍️ Введите ответ для пользователя по тикету №{ticket_id}:")
    await callback.answer()




@router.message(SupportFSM.waiting_for_admin_reply)
async def final_admin_reply(message: Message, state: FSMContext):
    # 1. Извлекаем данные
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    ticket_id = data.get("ticket_id")

    # 2. Отправляем ответ юзеру
    await message.bot.send_message(
        chat_id=target_user_id,
        text=f"📩 **Ответ от службы поддержки (Тикет №{ticket_id}):**\n\n{message.text}",
        parse_mode="Markdown"
    )

    # 3. Обновляем статус в БД
    await close_ticket(ticket_id)

    # 4. Финализируем
    await message.answer("✅ Ответ успешно доставлен пользователю!")
    await state.clear()