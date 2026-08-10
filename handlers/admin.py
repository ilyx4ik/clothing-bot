from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from states import AddCategory, Broadcast, AdminUserSearch
from keyboards.builders import admin_keyboard, get_admin_back_keyboard, autopost_toggle_keyboard, my_items_keyboard, ban_user_keyboard, admin_user_manage_kb, admin_settings_kb
from database.requests import add_category, get_all_users_items, give_vip_status, issue_strike
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Order, InviteCode, BotSettings
from datetime import datetime, timedelta
import os
import pandas as pd
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import secrets
from states import GiveVip

ADMIN_ID = 1794385161

# Глобальный флаг автопостинга (включатель/выключатель)
IS_AUTOPOST_ENABLED = True

router = Router()


@router.message(Command('admin'))
async def admin_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к панели администратора ⛔")
        return
    
    await message.answer(
        text="⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=await admin_keyboard()
    )

@router.callback_query(F.data == 'admin_main')
async def admin_main_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    await callback.message.edit_text(
        text="⚙️ <b>Панель администратора</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=await admin_keyboard()
    )
    await callback.answer()

@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа ⛔")
        return

    if not command.args or not command.args.split()[0].isdigit():
        await message.answer("⚠️ Использование: <code>/ban Telegram_ID</code>", parse_mode="HTML")
        return

    target_id = int(command.args.split()[0])
    result = await session.execute(select(User).where(User.tg_id == target_id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь с таким Telegram ID не найден.")
        return

    user.is_banned = True
    await session.commit()
    await message.answer(f"🔒 Пользователь <b>{target_id}</b> успешно заблокирован!", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа ⛔")
        return

    if not command.args or not command.args.split()[0].isdigit():
        await message.answer("⚠️ Использование: <code>/unban Telegram_ID</code>", parse_mode="HTML")
        return

    target_id = int(command.args.split()[0])
    result = await session.execute(select(User).where(User.tg_id == target_id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь с таким Telegram ID не найден.")
        return

    user.is_banned = False
    await session.commit()
    await message.answer(f"🔓 Пользователь <b>{target_id}</b> разблокирован!", parse_mode="HTML")


@router.message(Command("givevip"))
async def give_vip_handler(message: Message):
    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Использование команды: `/givevip <tg_id> <дни>`\nПример: `/givevip 123456789 30`", parse_mode="Markdown")
        return

    try:
        target_id = int(args[1])
        days = int(args[2])

        await give_vip_status(tg_id=target_id, days=days)
        await message.answer(f"✅ Пользователю `{target_id}` успешно выдан VIP на {days} дней!", parse_mode="Markdown")

        try:
            await message.bot.send_message(target_id, f"🎉 Вам выдан VIP-статус на {days} дней! Теперь вам доступен «Снайпер».")
        except Exception:
            pass

    except ValueError:
        await message.answer("❌ ID и количество дней должны быть числами!")



@router.callback_query(F.data.startswith("strike:"))
async def strike_handler(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return
    target_id = int(callback.data.split(":")[1])

    result = await issue_strike(target_id)
    if not result:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    
    await callback.answer("⚠️ Страйк выдан!", show_alert=True)

    user = await session.scalar(select(User).where(User.tg_id == target_id))

    kb = ban_user_keyboard(target_id=user.tg_id, is_banned=user.is_banned)

    username_str = f"@{user.username}" if user.username else "Нет"

    await callback.message.edit_text(
        text=(
        f"👤 <b>Информация о пользователе:</b>\n\n"
        f"Telegram ID: <code>{user.tg_id}</code>\n"
        f"Username: {username_str}\n"
        f"Полное имя: {user.full_name or 'Нет'}\n"
        f"Телефон: {user.phone or 'Нет'}\n"
        f"Страна: {user.country or 'Нет'}\n"
        f"Город: {user.city or 'Нет'}\n"
        f"Страйки: {user.strikes}\n"
        f"Заблокирован: {'Да 🔴' if user.is_banned else 'Нет 🟢'}\n"
    ),
    reply_markup=kb,
    parse_mode="HTML"
    )




@router.callback_query(F.data == "admin_settings_menu")
async def admin_settings_menu_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
            await callback.answer("У вас нет доступа ⛔", show_alert=True)
            return

    
    result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
    settings = result.scalar_one_or_none()

    if settings is None:
        settings = BotSettings()
        session.add(settings)
        await session.commit()
        await session.refresh(settings)

    kb = admin_settings_kb(
        watermark_enabled=settings.watermark_enabled,
        sniper_enabled=settings.sniper_enabled
    )

    await callback.message.edit_text("⚙️ **Настройки бота:**", reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("toggle_setting:"))
async def toggle_setting_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
            await callback.answer("У вас нет доступа ⛔", show_alert=True)
            return

    setting_name = callback.data.split(":")[1]

    result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
    settings = result.scalar_one_or_none()

    if settings is None:
            settings = BotSettings()
            session.add(settings)
            await session.commit()
            await session.refresh(settings)

    if setting_name == "watermark":
        settings.watermark_enabled = not settings.watermark_enabled

    elif setting_name == "sniper":
        settings.sniper_enabled = not settings.sniper_enabled

    await session.commit()
    await session.refresh(settings)

    kb = admin_settings_kb(settings.watermark_enabled, settings.sniper_enabled)

    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("✅ Настройка изменена!", show_alert=False)


@router.callback_query(F.data.startswith("toggle_vip:"))
async def toggle_vip_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    target_id = int(callback.data.split(":")[1])
    result = await session.execute(select(User).where(User.tg_id == target_id))
    user = result.scalar_one_or_none()

    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return

    user.is_vip = not user.is_vip
    await session.commit()

    await callback.answer(
        f"VIP-статус {'выдан' if user.is_vip else 'забран'}!", 
        show_alert=True
    )

    kb = await admin_user_manage_kb(target_id=user.tg_id, is_banned=user.is_banned, is_vip=user.is_vip)

    user_info = (
        f"👤 <b>Информация о пользователе:</b>\n\n"
        f"Telegram ID: <code>{user.tg_id}</code>\n"
        f"Username: @{user.username if user.username else 'Нет'}\n"
        f"Полное имя: {user.full_name if user.full_name else 'Нет'}\n"
        f"VIP-статус: {'👑 Да' if user.is_vip else 'Нет'}\n"
        f"Рефералов: {user.referrals_count}\n"
        f"Заблокирован: {'Да' if user.is_banned else 'Нет'}\n"
    )

    await callback.message.edit_text(user_info, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "admin_search_user")  
async def search_user_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    await callback.answer()  
    await state.set_state(AdminUserSearch.waiting_for_user_input)
    await callback.message.answer("Введите Telegram ID пользователя или @username для поиска:")


@router.message(AdminUserSearch.waiting_for_user_input)
async def process_search_user(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа ⛔")
        return

    # 1. Очищаем ввод от пробелов и убираем '@' в начале (если ввели @username)
    query_text = message.text.strip().lstrip('@')

    if not query_text:
        await message.answer("⚠️ Введите числовой Telegram ID или username.")
        return

    # 2. Определяем тип поиска (по ID или по Username)
    if query_text.isdigit():
        stmt = select(User).where(User.tg_id == int(query_text))
    else:
        stmt = select(User).where(func.lower(User.username) == query_text.lower())

    # 3. Выполняем один запрос к базе
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    # 4. Проверяем, найден ли пользователь
    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return

    await state.clear()

    # 5. Формируем и отправляем карточку
    username_str = f"@{user.username}" if user.username else "Нет"
    
    user_info = (
        f"👤 <b>Информация о пользователе:</b>\n\n"
        f"Telegram ID: <code>{user.tg_id}</code>\n"
        f"Username: {username_str}\n"
        f"Полное имя: {user.full_name or 'Нет'}\n"
        f"Телефон: {user.phone or 'Нет'}\n"
        f"Страна: {user.country or 'Нет'}\n"
        f"Город: {user.city or 'Нет'}\n"
        f"Страйки: {user.strikes}\n"
        f"Заблокирован: {'Да 🔴' if user.is_banned else 'Нет 🟢'}\n"
    )

    kb = ban_user_keyboard(target_id=user.tg_id, is_banned=user.is_banned)
    await message.answer(user_info, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("toggle_ban:"))
async def toggle_ban_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
            await callback.answer("У вас нет доступа ⛔")
            return

    target_id = int(callback.data.split(":")[1])
    result = await session.execute(select(User).where(User.tg_id == target_id))
    user = result.scalar_one_or_none()

    user.is_banned = not user.is_banned
    await session.commit()

    kb = ban_user_keyboard(target_id=user.tg_id, is_banned=user.is_banned)

    await callback.message.edit_text(
        text=(
            f"👤 <b>Информация о пользователе:</b>\n\n"
            f"Telegram ID: <code>{user.tg_id}</code>\n"
            f"Username: @{user.username if user.username else 'Нет'}\n"
            f"Полное имя: {user.full_name if user.full_name else 'Нет'}\n"
            f"Телефон: {user.phone if user.phone else 'Нет'}\n"
            f"Страна: {user.country if user.country else 'Нет'}\n"
            f"Город: {user.city if user.city else 'Нет'}\n"
            f"Страйки: {user.strikes}\n"
            f"Заблокирован: {'Да' if user.is_banned else 'Нет'}\n"
        ),
        parse_mode="HTML",
        reply_markup=kb
    )

    await callback.answer()




@router.callback_query(F.data == 'admin_give_vip')
async def give_vip_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GiveVip.tg_id)
    await callback.message.answer("📥 Введите Telegram ID пользователя, которому нужно выдать VIP:")
    await callback.answer()


@router.message(GiveVip.tg_id)
async def process_give_vip_status(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ ID должен состоять только из цифр. Попробуйте ещё раз:")
        return

    await state.update_data(tg_id=int(message.text))
    await state.set_state(GiveVip.days)
    await message.answer("⏳ На сколько дней выдать VIP-статус? (Введите число):")


@router.message(GiveVip.days)
async def process_vip_days(message: Message, state: FSMContext):
    # Если юзер нажал обычную кнопку меню вместо ввода числа — сбрасываем стейт
    if message.text in ["👤 Профиль", "👤 Мой аккаунт", "Отмена", "/start"]:
        await state.clear()
        # Перенаправлять не нужно, aiogram сам перехватит хэндлером профиля,
        # но для надежности можно просто очистить стейт и вернуть управление.
        await message.answer("❌ Выдача VIP отменена.")
        return

    if not message.text.isdigit():
        await message.answer("❌ Количество дней должно быть числом. Попробуйте ещё раз:")
        return

    days = int(message.text)
    data = await state.get_data()
    target_id = data["tg_id"]

    await give_vip_status(target_id, days)
    await state.clear()

    await message.answer(f"✅ Пользователю <code>{target_id}</code> успешно выдан VIP на <b>{days}</b> дней!", parse_mode="HTML")

    try:
        await message.bot.send_message(
            target_id, 
            f"🎉 Вам выдан VIP-статус на <b>{days}</b> дней! Теперь вам доступен «Снайпер».", 
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    


@router.callback_query(F.data == 'add_category')
async def add_category_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.title)
    await callback.message.answer("Введите название новой категории:")
    await callback.answer()

@router.message(AddCategory.title)
async def process_category_title(message: Message, state: FSMContext):
    await add_category(message.text)
    await message.answer(
        f"Категория <b>{message.text}</b> успешно добавлена! 🎉", 
        parse_mode="HTML",
        reply_markup=get_admin_back_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == 'stats_handler')
async def stats_callback_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    query = select(func.count(User.id))
    result = await session.execute(query)
    users_count = result.scalar() or 0

    time_24h_ago = datetime.now() - timedelta(days=1)
    query_24h = select(func.count(Order.id)).where(Order.created_at >= time_24h_ago)
    result_24h = await session.execute(query_24h)
    orders_24h = result_24h.scalar() or 0

    query_sum = select(func.sum(Order.price))
    result_sum = await session.execute(query_sum)
    total_revenue = result_sum.scalar() or 0

    text = (
        f"📊 <b>Экспресс-статистика:</b>\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"🛒 Заказов за 24ч: {orders_24h}\n"
        f"💰 Общая выручка: {total_revenue} грн"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer()

@router.message(Command("stats"))
async def stats_handler(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой функции ⛔")
        return

    query = select(func.count(User.id))
    result = await session.execute(query)
    users_count = result.scalar() or 0

    time_24h_ago = datetime.now() - timedelta(days=1)
    query_24h = select(func.count(Order.id)).where(Order.created_at >= time_24h_ago)
    result_24h = await session.execute(query_24h)
    orders_24h = result_24h.scalar() or 0

    query_sum = select(func.sum(Order.price))
    result_sum = await session.execute(query_sum)
    total_revenue = result_sum.scalar() or 0

    text = (
        f"📊 <b>Экспресс-статистика:</b>\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"🛒 Заказов за 24ч: {orders_24h}\n"
        f"💰 Общая выручка: {total_revenue} грн"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())

@router.callback_query(F.data == "admin_stats_excel")
async def stats_excel_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    await callback.answer("Готовлю Excel-отчёт... ⏳")

    result = await session.execute(select(User))
    users = result.scalars().all()

    data = []
    for user in users:
        data.append({
            "ID": user.id,
            "Telegram_ID": user.tg_id,
            "Username": getattr(user, "username", None) or "Нет юзернейма",
            "Имя": getattr(user, "full_name", None) or "—",
            "Телефон": getattr(user, "phone", None) or "—"
        })

    df = pd.DataFrame(data)
    file_path = "users_report.xlsx"
    df.to_excel(file_path, index=False)

    await callback.message.answer_document(
        FSInputFile(file_path), 
        caption="📊 Отчёт по пользователям готов!",
        reply_markup=get_admin_back_keyboard()
    )

    if os.path.exists(file_path):
        os.remove(file_path)

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    await state.set_state(Broadcast.message)
    await callback.message.answer("📢 Отправьте сообщение (текст, фото или видео), которое уйдёт всем пользователям:")
    await callback.answer()

@router.message(Broadcast.message)
async def process_broadcast(message: Message, state: FSMContext, session: AsyncSession):
    result = await session.execute(select(User.tg_id))
    users = result.scalars().all()

    if not users:
        await message.answer("⚠️ В базе данных пока нет пользователей для рассылки.", reply_markup=get_admin_back_keyboard())
        await state.clear()
        return

    await message.answer(f"⏳ Начинаю рассылку на {len(users)} пользователей...")

    success_count = 0
    blocked_count = 0

    for tg_id in users:
        try:
            await message.copy_to(chat_id=tg_id)
            success_count += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            blocked_count += 1
        except Exception:
            blocked_count += 1

    await state.clear()
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📨 Успешно доставлено: <b>{success_count}</b>\n"
        f"🚫 Не доставлено: <b>{blocked_count}</b>",
        parse_mode="HTML",
        reply_markup=get_admin_back_keyboard()
    )

@router.callback_query(F.data == "generate_invite")
async def generate_invite_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    raw_code = secrets.token_hex(3).upper()
    invite_code = f"BETA-{raw_code}"

    new_code = InviteCode(code=invite_code)
    session.add(new_code)
    await session.commit()

    bot_info = await callback.bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={invite_code}"

    text = (
        f"🔑 <b>Сгенерирован новый инвайт-код:</b>\n\n"
        f"Код: <code>{invite_code}</code>\n"
        f"Прямая ссылка: {deep_link}"
    )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_orders_history")
async def admin_orders_history_handler(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    query = select(Order).order_by(Order.created_at.desc()).limit(10)
    result = await session.execute(query)
    orders = result.scalars().all()

    if not orders:
        await callback.answer("История заказов пока пуста.", show_alert=True)
        return

    text = "📋 <b>Последние 10 заказов в магазине:</b>\n\n"
    for order in orders:
        buyer_info = order.user_name or f"TG ID: {order.user_id}"
        phone_info = order.phone or "—"
        address_info = order.address or "—"
        created_date = order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else "—"

        text += (
            f"🔹 <b>Заказ #{order.id}</b>\n"
            f"👤 Покупатель: {buyer_info}\n"
            f"📞 Телефон: {phone_info}\n"
            f"📍 Адрес: {address_info}\n"
            f"💰 Сумма: {order.price} грн\n"
            f"📅 Дата: {created_date}\n"
            f"------------------------------\n"
        )

    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_admin_back_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_autopost_settings")
async def autopost_settings_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>Управление автопостингом объявлений</b>\n\n"
        "Здесь вы можете включить или отключить автопубликацию объявлений пользователей в ТГ-канал.",
        parse_mode="HTML",
        reply_markup=autopost_toggle_keyboard(IS_AUTOPOST_ENABLED)
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_autopost_state")
async def toggle_autopost_handler(callback: CallbackQuery):
    global IS_AUTOPOST_ENABLED
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа ⛔", show_alert=True)
        return

    IS_AUTOPOST_ENABLED = not IS_AUTOPOST_ENABLED
    status_msg = "включен 🟢" if IS_AUTOPOST_ENABLED else "отключен 🔴"

    await callback.message.edit_reply_markup(
        reply_markup=autopost_toggle_keyboard(IS_AUTOPOST_ENABLED)
    )
    await callback.answer(f"Автопостинг {status_msg}", show_alert=True)


@router.message(Command("strike"))
async def cmd_strike(message: Message, command: CommandObject, bot: Bot):
    args = command.args

    if not args or not args.isdigit():
        await message.answer("Использование: /strike <tg_id>")
        return

    target_id = int(args)
    result = await issue_strike(target_id)

    if result is None:
        await message.answer("❌ Пользователь не найден в базе.")
        return

    strikes, is_banned = result 

    if is_banned:
        await message.answer("🚫 Выдан 3-й страйк! Пользователь автоматически забанен.")
        try:
            await bot.send_message(
            chat_id=target_id, 
            text="🚫 Вы получили 3-й страйк и были автоматически забанены!"
        )
        except Exception:
            pass
        return
    else:
        await message.answer(f"⚠️ Пользователю выдан страйк (получено {strikes}/3)")
        try:
            await bot.send_message(
            chat_id=target_id, 
            text=f"⚠️ Вы получили страйк от администрации ({strikes}/3)!"
        )
        except Exception:
            pass