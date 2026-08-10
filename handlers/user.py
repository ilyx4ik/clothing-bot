from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, InviteCode, Categories, Item, Favorite
from utils.watermark import add_watermark_on_photo
from datetime import datetime

# Импорты клавиатур
from keyboards.builders import (
    items_keyboard, categories_keyboard, item_details_keyboard, 
    basket_keyboard, my_items_keyboard, my_item_details_keyboard, 
    main_user_kb, catalog_type_kb, parser_menu_kb, item_card_keyboard, 
    brands_keyboard, account_keyboard, authenticity_kb, skip_tags_kb,
    favorite_keyboard, favorite_item_kb, get_platforms_kb, back_kb,
    get_categories_kb_parser, get_found_item_kb, get_my_filters_kb
)

# Импорты запросов к базе данных
from database.requests import (
    get_item, add_to_basket, get_basket, clear_basket, add_item, 
    get_items_by_category, get_users_items, delete_item, get_brands_by_category, 
    get_items_by_category_and_brand, get_user, update_user_profile, set_user,
    delete_from_basket, get_watermark_setting, get_sniper_filter_setting, add_sniper_filter, get_user,
    toggle_favorite, notify_price_drop, get_user_favorites, get_user_found_items, clear_user_found_items,
    delete_found_item_by_id, add_user_sniper_filter, delete_user_sniper_filter, get_user_sniper_filter,
    get_seller_rating, check_is_scam
)

from states import OrderForm, AddItem, UserProfile, RegistrationStates, AddSniper, SupportFSM, EditItem, GlobalParser, AddFilter
from database.db import async_session
from handlers.admin import admin_keyboard, ADMIN_ID

router = Router()

# Расширенный белый список доверенных брендов
TRUSTED_BRANDS = {
    "nike", "adidas", "reebok", "puma", "new balance", "asics", 
    "carhartt", "stussy", "the north face", "arc'teryx", "columbia", 
    "stone island", "levi's", "zara", "h&m", "ralph lauren", "lacoste", 
    "under armour", "rick owens", "rickowens", "recovens", "kedr"
}

# Временное хранилище данных товаров, ушедших на модерацию
PENDING_ITEMS = {}

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

@router.message(RegistrationStates.waiting_for_invite)
async def process_invite_code(message: Message, state: FSMContext, session: AsyncSession):
    code_text = message.text.strip()

    # Ищем инвайт-код в таблице инвайтов
    # (предполагается, что у тебя есть модель InviteCode)
    result = await session.execute(select(InviteCode).where(InviteCode.code == code_text, InviteCode.is_used == False))
    invite = result.scalar_one_or_none()

    if not invite:
        await message.answer("❌ Неверный или уже использованный инвайт-код. Попробуйте еще раз:")
        return

    # Код верный! Помечаем инвайт как использованный
    invite.is_used = True

    # Достаем referrer_id, который мы сохранили на шаге /start
    user_data = await state.get_data()
    referrer_id = user_data.get("referrer_id")

    # Если был реферал — увеличиваем ему счетчик
    if referrer_id:
        ref_result = await session.execute(select(User).where(User.tg_id == referrer_id))
        referrer = ref_result.scalar_one_or_none()
        if referrer:
            referrer.referrals_count += 1
            try:
                await message.bot.send_message(
                    chat_id=referrer.tg_id,
                    text="🎉 По вашей реферальной ссылке зарегистрировался новый бета-тестер!"
                )
            except Exception:
                pass

    # Создаем самого пользователя в БД
    new_user = User(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referrer_id=referrer_id
    )
    session.add(new_user)
    await session.commit()
    await state.clear()

    await message.answer("✅ Инвайт-код принят! Добро пожаловать в магазин!", reply_markup=main_user_kb())



async def show_item_card(message: Message, items, index: int, category_id: int, edit: bool = False, brand: str = None):
    item = items[index]
    
    seller_id = getattr(item, 'owner_id', None)
    
    if seller_id:
        avg_rating, count = await get_seller_rating(seller_id)
        is_scam = await check_is_scam(seller_id)
        
        if is_scam:
            seller_info = "\n\n🚨 <b>ВНИМАНИЕ: Продавец в ЧЁРНОМ СПИСКЕ (SCAM)!</b> 🚨"
        else:
            seller_info = f"\n\n⭐ <b>Рейтинг продавца:</b> {avg_rating}/10 ({count} отзывов)"
    else:
        seller_info = ""

    # --- ФОРМИРУЕМ ОПИСАНИЕ С УЧЕТОМ РЕЙТИНГА ---
    caption = (
        f"<b>{item.title}</b>\n\n"
        f"📝 <b>Описание:</b> {item.description}\n"
        f"📏 <b>Размер:</b> {item.size}\n"
        f"🏷 <b>Бренд:</b> {item.brand}\n"
        f"💰 <b>Цена:</b> {item.price} грн"
        f"{seller_info}"  
    )
    
    kb = item_card_keyboard(
        item_id=item.id, 
        index=index, 
        total_items=len(items), 
        category_id=category_id, 
        brand=brand
    )

    if edit and isinstance(message, Message):
        try:
            await message.edit_media(
                media=InputMediaPhoto(media=item.photo, caption=caption, parse_mode="HTML"),
                reply_markup=kb
            )
            return
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass
        
    await message.answer_photo(photo=item.photo, caption=caption, parse_mode="HTML", reply_markup=kb)

# --- 1. СТАРТ И АВТОРИЗАЦИЯ ---

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, state: FSMContext):
    args = command.args
    tg_id = message.from_user.id

    # Опредяем текущий username сразу
    raw_username = message.from_user.username
    current_username = raw_username.lower() if raw_username else None

    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    # Если пользователь уже существует в базе
    if user:
        # 1. Проверяем и обновляем username, если он изменился или был NULL
        if user.username != current_username:
            user.username = current_username
            await session.commit()

        # 2. Проверяем бан
        if user.is_banned:
            await message.answer("⛔ Вы заблокированы!")
            return

        # 3. Пускаем в главный магазин
        await message.answer("С возвращением в магазин!", reply_markup=main_user_kb())
        return

    # --- Если пользователь новый (нет в БД) ---

    # Запоминаем ID пригласившего (если есть реферальная ссылка)
    if args and args.isdigit() and int(args) != tg_id:
        await state.update_data(referrer_id=int(args))

    # Требуем инвайт-код для бета-теста
    await state.set_state(RegistrationStates.waiting_for_invite)
    await message.answer("🔒 **Бот находится в закрытом бета-тесте.**\n\nВведите ваш инвайт-код для доступа:")



# --- 2. ГЛАВНОЕ МЕНЮ (КАТАЛОГ И ИСТОЧНИКИ) ---

@router.message(F.text == "🛒 Каталог")
async def catalog_cmd(message: Message):
    await message.answer("Выберите раздел каталога:", reply_markup=catalog_type_kb())


@router.callback_query(F.data == "cat_source_bot")
async def cat_source_bot_handler(callback: CallbackQuery):
    await callback.message.edit_text( 
        text="📁 Выберите категорию:",
        reply_markup=await categories_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cat_source_parsed")
async def cat_source_parse_handler(callback: CallbackQuery):
    await callback.answer(
        "Раздел со спаршенными товарами пока в разработке! 🚀",
        show_alert=True
    )


@router.callback_query(F.data == "catalog_users")
async def catalog_users_handler(callback: CallbackQuery):
    kb = await categories_keyboard()  
    text = "📁 Выберите категорию товаров:"

    try:
        await callback.message.edit_text(text=text, reply_markup=kb)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text=text, reply_markup=kb)
    
    await callback.answer()


@router.callback_query(F.data == "catalog_parser")
async def catalog_parser_handler(callback: CallbackQuery):
    text = (
        "🔍 <b>Раздел «Парсер»</b>\n\n"
        "Здесь вы можете отслеживать появление нужных товаров в реальном времени.\n\n"
        "• 🌐 <b>Общие ссылки</b> — готовые подборки и фильтры от нашей команды.\n"
        "• 🔗 <b>Моя ссылка</b> — ваша персональная ссылка для индивидуального мониторинга.\n\n"
        "Выберите нужный раздел ниже:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=parser_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "parser_global_links")
async def global_parser_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(GlobalParser.select_platform)
    await callback.message.edit_text(
        text="Выберите площадку",
        reply_markup=get_platforms_kb(),
        parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("platform_"))
async def process_global_parser_handler(callback: CallbackQuery, state: FSMContext):

    text=(
            "✍️ Введите бренд или название товара\n\n"
            "Напишите словами то, что хотите искать.\n\n"
            "Примеры:\n\n"
            "• Rick Owens\n\n"
            "• Nike Air Max\n\n"
            "• Chrome Hearts Ring\n\n"

            "Бот сам отформатирует ваш запрос под выбранный сайт!"
        )

    platform_name = callback.data.split("_")[1]
    await state.update_data(platform=platform_name)
    await state.set_state(GlobalParser.enter_query)
    await callback.message.edit_text(
        text=text,
        reply_markup=back_kb(),
        parse_mode="HTML"
)


@router.message(GlobalParser.enter_query)
async def query_global_parser_handler(message: Message, state: FSMContext):
    user_query = message.text.strip()

    if len(user_query) < 2:
        await message.answer("Запрос слишком короткий. Пожалуйста, введите название нормально (минимум 2 символа).")
        return
    elif len(user_query) > 50:
        await message.answer("Запрос слишком длинный. Пожалуйста, введите название нормально (максимум 50 символов).")
        return

    await state.update_data(query=user_query)
    await state.set_state(GlobalParser.select_category)
    await message.answer("Отлично! Теперь выберите категорию:", reply_markup=get_categories_kb_parser())


@router.callback_query(F.data.startswith("category_"), GlobalParser.select_category)
async def final_global_parser_hanlder(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()

    data = await state.get_data()
    platform = data.get("platform")
    query = data.get("query")
    category = callback.data.split("_")[1]

    if platform == "olx":
        formatted_query = query.replace(' ', '-')
        url = f"https://www.olx.ua/d/list/q-{formatted_query}/"
    elif platform == "grailed":
        formatted_query = query.replace(' ', '%20')
        url = f"https://www.grailed.com/shop?query={formatted_query}"
    else:
        url = "https://www.olx.ua/"


    await add_sniper_filter(session=session, user_id=callback.from_user.id, url=url)

    await state.clear()


    text = (
        "✅ <b>Ссылка успешно создана и добавлена в парсер!</b>\n\n"
        f"🔗 <b>Ваша ссылка:</b>\n<code>{url}</code>"
    )

    await callback.message.delete()

    await callback.message.answer(
        text=text,
        reply_markup=main_user_kb(),
        parse_mode="HTML"
    )


def format_item_text(item, index: int, total: int) -> str:
    return (
        f"📦 <b>{item.title}</b>\n\n"
        f"💰 <b>Цена:</b> {item.price}\n"
        f"📅 <b>Найдено:</b> {item.created_at.strftime('%d.%m %H:%M')}\n"
    )

@router.message(F.text == "📦 Найденные лоты")
async def show_found_items_handler(message: Message):
    items = await get_user_found_items(message.from_user.id)

    if not items:
        await message.answer("📭 <b>У вас пока нет найденных лотов.</b>\nСнайпер ищет нон-стоп!", parse_mode="HTML")
        return

    item = items[0]
    text = format_item_text(item, 0, len(items))
    # Передаем item.id в клавиатуру 👇
    reply_markup = get_found_item_kb(0, len(items), item.url, item.id)

    if item.photo:
        await message.answer_photo(photo=item.photo, caption=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.answer(text=text, reply_markup=reply_markup, parse_mode="HTML")


# --- 2. При листании страниц (обнови вызов get_found_item_kb) ---
@router.callback_query(F.data.startswith("found_page_"))
async def process_found_page_callback(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split("_")[2])
    
    items = await get_user_found_items(callback.from_user.id)
    if not items or page >= len(items):
        return

    item = items[page]
    text = format_item_text(item, page, len(items))
    # Передаем item.id в клавиатуру 👇
    reply_markup = get_found_item_kb(page, len(items), item.url, item.id)

    if item.photo and callback.message.photo:
        from aiogram.types import InputMediaPhoto
        await callback.message.edit_media(
            media=InputMediaPhoto(media=item.photo, caption=text, parse_mode="HTML"),
            reply_markup=reply_markup
        )
    else:
        await callback.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")


# --- 3. ХЭНДЛЕР УДАЛЕНИЯ ОДНОГО ЛОТА ---
@router.callback_query(F.data.startswith("delete_item_"))
async def delete_single_item_callback(callback: CallbackQuery):
    _, _, item_id, page = callback.data.split("_")
    item_id, page = int(item_id), int(page)

    # Удаляем лот из БД
    await delete_found_item_by_id(item_id, callback.from_user.id)
    await callback.answer("❌ Лот удалён!")

    # Получаем обновленный список
    items = await get_user_found_items(callback.from_user.id)

    # Если лотов больше не осталось
    if not items:
        await callback.message.delete()
        await callback.message.answer("📭 <b>Вы удалили все лоты. Список пуст!</b>", parse_mode="HTML")
        return

    # Корректируем индекс страницы, если удалили самый последний элемент
    if page >= len(items):
        page = len(items) - 1

    item = items[page]
    text = format_item_text(item, page, len(items))
    reply_markup = get_found_item_kb(page, len(items), item.url, item.id)

    if item.photo and callback.message.photo:
        from aiogram.types import InputMediaPhoto
        await callback.message.edit_media(
            media=InputMediaPhoto(media=item.photo, caption=text, parse_mode="HTML"),
            reply_markup=reply_markup
        )
    else:
        await callback.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")


@router.callback_query(F.data == "parser_custom_link")
async def add_custom_link_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddFilter.waiting_for_url)

    await callback.message.answer("🔗 <b>Отправьте вашу ссылку:</b>", parse_mode="HTML")

    await callback.answer()


@router.message(F.text == "➕ Добавить ссылку")
async def add_url_user_handler(message: Message, state: FSMContext):
    await state.set_state(AddFilter.waiting_for_url)
    await message.answer("Отправьте вашу ссылку")
    return

@router.message(AddFilter.waiting_for_url)
async def proccess_url_user(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовую ссылку!")
    url = message.text.strip()
    if url.startswith("http"):
        await add_user_sniper_filter(message.from_user.id, url)
        await state.clear()
        await message.answer("Ссылка успешно добавлена!")
    else:
        await message.answer("Введите корректную ссылку")


@router.callback_query(F.data.startswith("delete_filter_"))
async def delete_url_user(callback: CallbackQuery):
    filter_id = int(callback.data.split("_")[2])
    await delete_user_sniper_filter(filter_id, callback.from_user.id)
    await callback.answer("❌ Ссылка удалена!")
    await callback.message.delete()


@router.message(F.text == "🎯 Мои ссылки")
async def user_url_handler(message: Message):
    filters = await get_user_sniper_filter(message.from_user.id)
    if not filters:
        await message.answer("📭 У вас нет сохранённых ссылок.")
        return
    await message.answer("Ваши активные ссылки для отслеживания:", reply_markup=get_my_filters_kb(filters))



# 4. Очистить список лотов
@router.callback_query(F.data == "clear_found_items")
async def clear_items_callback(callback: CallbackQuery):
    await clear_user_found_items(callback.from_user.id)
    await callback.answer("🗑 Список найденных лотов очищен!")
    await callback.message.delete()
    await callback.message.answer("📭 <b>Список очищен.</b> Снайпер продолжит присылать новые находки сюда!")


# --- 3. КАТЕГОРИИ, БРЕНДЫ И ПАГИНАЦИЯ ТОВАРОВ ---

@router.callback_query(F.data.startswith('category_'))
async def category_click_handler(callback: CallbackQuery, state: FSMContext):
    current_state_name = await state.get_state()
    category_id = int(callback.data.split('_')[1])

    if current_state_name == AddItem.category_id.state:
        await state.update_data(category_id=category_id)
        
        # 1. Меняем состояние на ПОДЛИННОСТЬ (вместо AddItem.title)
        await state.set_state(AddItem.authenticity)
        
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        # 2. Отправляем запрос подлинности с клавиатурой
        await callback.message.answer(
            "🛡 **Укажите степень подлинности товара:**", 
            reply_markup=authenticity_kb(), 
            parse_mode="Markdown"
        )
        await callback.answer()
        return 

    # Просмотр каталога вне выкладки (оставляем без изменений)
    brands = await get_brands_by_category(category_id)
    kb = brands_keyboard(category_id, brands)
    text = "📁 Выберите бренд или просмотрите все товары категории:"

    try:
        await callback.message.edit_text(text=text, reply_markup=kb)
    except Exception:
        await callback.message.delete()
        await callback.message.answer(text=text, reply_markup=kb)
        
    await callback.answer()


@router.callback_query(F.data.startswith('brand_'))
async def show_brands_items(callback: CallbackQuery):
    try:
        data_without_prefix = callback.data.removeprefix('brand_')
        category_id_str, brand = data_without_prefix.split('_', 1)
        category_id = int(category_id_str)
    except ValueError:
        await callback.answer("Ошибка обработки бренда 😔", show_alert=True)
        return

    items = await get_items_by_category_and_brand(category_id, brand)

    if not items:
        await callback.answer(f"Товаров бренда {brand} пока нет 😔", show_alert=True)
        return

    await show_item_card(callback.message, items, 0, category_id, edit=True, brand=brand)
    await callback.answer()


@router.callback_query(F.data.startswith('show_all'))
async def show_all_in_category(callback: CallbackQuery):
    category_id = int(callback.data.split('_')[2])
    items = await get_items_by_category(category_id)

    if not items:
        await callback.answer("Товары не найдены 😔", show_alert=True)
        return

    await show_item_card(callback.message, items, 0, category_id, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith('page_'))
async def catalog_pagination_handler(callback: CallbackQuery):
    data_parts = callback.data.split('_')
    
    category_id = int(data_parts[1])
    index = int(data_parts[2])
    brand = data_parts[3] if len(data_parts) > 3 else None

    if brand:
        items = await get_items_by_category_and_brand(category_id, brand)
    else:
        items = await get_items_by_category(category_id)

    if not items or index >= len(items):
        await callback.answer("Товары закончились", show_alert=True)
        return

    await show_item_card(callback.message, items, index, category_id, edit=True, brand=brand)
    await callback.answer()


@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(callback: CallbackQuery):
    kb = await categories_keyboard()
    text = "📁 Выберите категорию:"

    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(text=text, reply_markup=kb)
    await callback.answer()




@router.callback_query(F.data.startswith('favorite:'))
async def farorite_items_handler(callback: CallbackQuery, state: FSMContext):
    item = state.get_data(Favorite.item_id)
    await toggle_favorite(item)

    await callback.message.edit_reply_markup(favorite_keyboard)
    await callback.message.answer("Добавлено!")


# --- 4. КОРЗИНА И ОФОРМЛЕНИЕ ЗАКАЗА ---

@router.message(F.text == "🛒 Корзина")
async def basket_msg_handler(message: Message):
    tg_id = message.from_user.id
    basket = await get_basket(tg_id)

    if not basket:
        await message.answer("Ваша корзина пуста 🛒")
        return
    
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total_price = 0

    items_list = []
    for item in basket:
        item_data = await get_item(item.item_id)
        if item_data:
            text += f"• {item_data.title} — <b>{item_data.price} грн</b>\n"
            total_price += item_data.price
            items_list.append(item_data)

    text += f"\n💰 Итого к оплате: <b>{total_price} грн</b>"

    await message.answer(
        text=text, 
        parse_mode="HTML",
        reply_markup=await basket_keyboard(items_list)
    )


@router.callback_query(F.data.startswith('buy_'))
async def add_to_basket_handler(callback: CallbackQuery):
    item_id = int(callback.data.split('_')[1])
    tg_id = callback.from_user.id
    await add_to_basket(tg_id, item_id)
    await callback.answer("Товар добавлен в корзину!", show_alert=True)


@router.callback_query(F.data == "basket")
async def basket_handler(callback: CallbackQuery):
    tg_id = callback.from_user.id
    basket = await get_basket(tg_id)

    if not basket:
        try:
            await callback.message.edit_text("Ваша корзина пуста 🛒")
        except Exception:
            await callback.message.delete()
            await callback.message.answer("Ваша корзина пуста 🛒")
        await callback.answer() 
        return
    
    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total_price = 0

    items_list = []
    for item in basket:
        item_data = await get_item(item.item_id)
        if item_data:
            text += f"• {item_data.title} — <b>{item_data.price} грн</b>\n"
            total_price += item_data.price
            items_list.append(item_data)

    text += f"\n💰 Итого к оплате: <b>{total_price} грн</b>"

    try:
        await callback.message.edit_text(
            text=text, 
            parse_mode="HTML",
            reply_markup=await basket_keyboard(items_list)
        )
    except Exception:
        await callback.message.delete()
        await callback.message.answer(
            text=text, 
            parse_mode="HTML",
            reply_markup=await basket_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data.startswith('delete_cart_item_'))
async def delete_single_cart_item_handler(callback: CallbackQuery):
    try:
        item_id = int(callback.data.split('_')[3])
    except (IndexError, ValueError):
        await callback.answer("Ошибка удаления товара", show_alert=True)
        return

    user_id = callback.from_user.id
    await delete_from_basket(user_id=user_id, item_id=item_id)
    await callback.answer("Товар удален из корзины!")

    basket = await get_basket(user_id)

    if not basket:
        await callback.message.edit_text("🛒 Ваша корзина пуста.")
        return

    text = "🛒 <b>Ваша корзина:</b>\n\n"
    total_price = 0

    items_list = []
    for item in basket:
        item_data = await get_item(item.item_id)
        if item_data:
            text += f"• {item_data.title} — <b>{item_data.price} грн</b>\n"
            total_price += item_data.price
            items_list.append(item_data)

    text += f"\n💰 Итого к оплате: <b>{total_price} грн</b>"
    
    await callback.message.edit_text(text, reply_markup=await basket_keyboard(items_list), parse_mode="HTML")


@router.callback_query(F.data == 'clear_basket')
async def clear_basket_handler(callback: CallbackQuery):
    tg_id = callback.from_user.id
    await clear_basket(tg_id)
    await callback.message.edit_text(
        "Ваша корзина очищена 🛒",
        reply_markup=await categories_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == 'checkout')
async def checkout_start_handler(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    user = await get_user(tg_id)

    user_name = user.full_name if (user and user.full_name) else None
    user_phone = user.phone if (user and user.phone) else None
    if user and user.city:
        if user.country:
            user_address = f"{user.country}, {user.city}"
        else:
            user_address = user.city
    else:
        user_address = None
        await callback.answer()

    await state.update_data(name = user_name, phone = user_phone, address = user_address)

    if not user_name:
        await state.set_state(OrderForm.name)
        await callback.message.answer("Введите ваше Имя и Фамилию для оформления заказа:")
        await callback.answer()
    elif not user_phone:
        await state.set_state(OrderForm.phone)
        await callback.message.answer("Введите ваш телефон для оформления заказа:")
        await callback.answer()
    elif not user_address:
        await state.set_state(OrderForm.address)
        await callback.message.answer("Введите ваш адрес для оформления заказа:")
        await callback.answer()
    else:
        await process_order_final(callback.message, state, name=user_name, phone=user_phone, address=user_address)


@router.message(OrderForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()
    if not data.get('phone'):
        await state.set_state(OrderForm.phone)
        await message.answer("Введите ваш номер телефона для оформления заказа:")
    elif not data.get('address'):
        await state.set_state(OrderForm.address)
        await message.answer("Введите ваш адрес для оформления заказа:")
    else:
        await process_order_final(message, state, name=data['name'], phone=data['phone'], address=data['address'])


@router.message(OrderForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    if not data.get('address'):
        await state.set_state(OrderForm.address)
        await message.answer("Укажите ваш город и номер отделения (или адрес доставки):")
    else:
        await process_order_final(message, state, name=data['name'], phone=data['phone'], address=data['address'])


@router.message(OrderForm.address)
async def process_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    data = await state.get_data()
    await process_order_final(message, state, name=data['name'], phone=data['phone'], address=message.text)


async def process_order_final(message: Message, state: FSMContext, name: str, phone: str, address: str):
    tg_id = message.chat.id
    basket = await get_basket(tg_id)
    items_text = ""
    total_price = 0
    buyer_username = message.chat.username
    telegram_contact = f"@{buyer_username}" if buyer_username else "Юзернейм скрыт (пишите по номеру)"

    for item in basket:
        item_data = await get_item(item.item_id)
        if item_data:
            items_text += f"• {item_data.title} — <b>{item_data.price} грн</b>\n"
            total_price += item_data.price

            if item_data.owner_id:
                seller_text = (
                    f"🎉 <b>У вас купили товар!</b>\n\n"
                    f"📦 Товар: <b>{item_data.title}</b> ({item_data.price} грн)\n\n"
                    f"👤 <b>Покупатель:</b>\n"
                    f"• Имя: <b>{name}</b>\n"
                    f"• Телефон: <b>{phone}</b>\n"
                    f"• Доставка: <b>{address}</b>\n"
                    f"• Telegram: {telegram_contact}"
                    f"• ID пользователя: <code>{message.chat.id}</code>"
                )
                try:
                    await message.bot.send_message(chat_id=item_data.owner_id, text=seller_text, parse_mode="HTML")
                except Exception as e:
                    print(f"Не удалось отправить сообщение продавцу {item_data.owner_id}: {e}")

    text = (
        f"🎉 <b>Спасибо за заказ!</b>\n"
        f"Продавец уже получил ваше оформление и свяжется с вами в ближайшее время.\n\n"
        f"📋 <b>Ваш заказ:</b>\n"
        f"{items_text}\n"
        f"💰 Итого к оплате: <b>{total_price} грн</b>\n\n"
        f"👤 <b>Данные получателя:</b>\n"
        f"• Имя: <b>{name}</b>\n"
        f"• Телефон: <b>{phone}</b>\n"
        f"• Адрес доставки: <b>{address}</b>"
    )

    await message.answer(text, parse_mode="HTML")
    await clear_basket(tg_id)
    await state.clear()


@router.message(F.text.in_({"👤 Профиль", "👤 Мой аккаунт", "Мой аккаунт"}))
async def my_account(message: Message):
    # Получаем юзера твоей функцией
    user = await get_user(message.from_user.id)

    if user is None:
        await set_user(message.from_user.id)
        user = await get_user(message.from_user.id)

    if user is None:
        await message.answer("Произошла ошибка при получении профиля. Попробуйте ввести /start")
        return

    # Логика VIP
    now = datetime.now()
    if user.is_vip and (user.vip_until is None or user.vip_until > now):
        if user.vip_until:
            date_str = user.vip_until.strftime('%d.%m.%Y %H:%M')
            vip_status = f"👑 Активен (до {date_str})"
        else:
            vip_status = "👑 Навсегда"
    else:
        vip_status = "❌ Отсутствует"

    # Твоя проверка на None для данных доставки
    country = user.country if user.country else "Не указано"
    city = user.city if user.city else "Не указано"
    full_name = user.full_name if user.full_name else "Не указано"
    phone = user.phone if user.phone else "Не указано"

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user.tg_id}"

    # Красивый совмещенный текст
    text = (
        f"👤 <b>Ваш аккаунт:</b>\n\n"
        f"🆔 ID: <code>{user.tg_id}</code>\n"
        f"💎 VIP-статус: <b>{vip_status}</b>\n"
        f"👥 Приглашено друзей: <b>{user.referrals_count}</b>\n\n"
        f"📝 <b>Данные для доставки:</b>\n"
        f"👤 ФИО: <b>{full_name}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n"
        f"🌍 Страна: <b>{country}</b>\n"
        f"🏙 Город: <b>{city}</b>\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"<i>Делитесь ссылкой с друзьями, чтобы получать бонусы!</i>"
    )

    # Вызываем твою клавиатуру account_keyboard()
    await message.answer(text, reply_markup=account_keyboard(), parse_mode="HTML")


# --- 5. ДОБАВЛЕНИЕ И МОДЕРАЦИЯ ТОВАРОВ ---

@router.message(F.text == "➕ Продать вещь")
async def sell_handler(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddItem.category_id)
    await message.answer("Выберите категорию:", reply_markup=await categories_keyboard())


# --- 2. ОБРАБОТКА ВЫБОРА КАТЕГОРИИ И ПЕРЕХОД К ПОДЛИННОСТИ ---
# (Замени или добавь этот хэндлер, чтобы после категории бот спрашивал подлинность)
@router.callback_query(AddItem.category_id)
async def category_chosen(call: CallbackQuery, state: FSMContext):
    # Сохраняем ID категории (в зависимости от твоей логики callback_data)
    await state.update_data(category_id=call.data)
    
    # Переводим на шаг выбора подлинности с красивой клавиатурой
    await state.set_state(AddItem.authenticity)
    await call.message.answer(
        "🛡 **Укажите степень подлинности товара:**", 
        reply_markup=authenticity_kb(), 
        parse_mode="Markdown"
    )
    await call.answer()


# --- 3. ШАГ: ПОДЛИННОСТЬ ---
@router.callback_query(AddItem.authenticity)
async def authenticity_sale(call: CallbackQuery, state: FSMContext):
    auth_map = {
        "auth_original": "💎 Оригинал",
        "auth_hq": "✨ High Quality",
        "auth_replica": "🏷 Реплика"
    }
    await state.update_data(authenticity=auth_map.get(call.data, "Не указано"))
    await state.set_state(AddItem.title)
    await call.message.answer("Введите название товара:")
    await call.answer()


# --- 4. ШАГ: НАЗВАНИЕ ---
@router.message(AddItem.title)
async def title_sale(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddItem.description)
    await message.answer("Введите описание товара:")


# --- 5. ШАГ: ОПИСАНИЕ ---
@router.message(AddItem.description)
async def description_sale(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddItem.brand)
    await message.answer("Укажите бренд (например, Nike, Adidas, Rick Owens или Нет бренда):")


# --- 6. ШАГ: БРЕНД ---
@router.message(AddItem.brand)
async def brand_sale(message: Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await state.set_state(AddItem.size)
    await message.answer("Введите размер и замеры (например: L, 43 или XL / 72х55):")


# --- 7. ШАГ: РАЗМЕР ---
@router.message(AddItem.size)
async def size_sale(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await state.set_state(AddItem.price)
    await message.answer("Введите цену товара (только число, например: 1200):")


# --- 8. ШАГ: ЦЕНА ---
@router.message(AddItem.price)
async def price_sale(message: Message, state: FSMContext):
    try:
        price_val = float(message.text)
        await state.update_data(price=price_val)
        await state.set_state(AddItem.photo)
        await message.answer("Скиньте фотографии товара:")
    except ValueError:
        await message.answer("Введите цену числом! (например: 1200 или 250.50)")


# --- 9. ШАГ: ФОТО ТОВАРА -> ЗАПРОС БИРОК ---
@router.message(AddItem.photo, F.photo)
async def photo_sale(message: Message, state: FSMContext):
    original_file_id = message.photo[-1].file_id
    await state.update_data(photo=original_file_id)
    
    await state.set_state(AddItem.tags_photo)
    await message.answer(
        "🏷 Отправьте фото бирок / QR-кода / Certilogo (или нажмите «Пропустить»):", 
        reply_markup=skip_tags_kb()
    )


# --- 10. ШАГ: ПОЛУЧЕНО ФОТО БИРКИ -> ФИНИШ ---
@router.message(AddItem.tags_photo, F.photo)
async def tags_photo_sale(message: Message, state: FSMContext):
    await state.update_data(tags_photo=message.photo[-1].file_id)
    await finalize_item_publishing(message, state, message.from_user)


# --- 11. ШАГ: ПРОПУЩЕНО ФОТО БИРКИ -> ФИНИШ ---
@router.callback_query(AddItem.tags_photo, F.data == "skip_tags")
async def skip_tags_sale(call: CallbackQuery, state: FSMContext):
    await state.update_data(tags_photo=None)
    await finalize_item_publishing(call.message, state, call.from_user)
    await call.answer()


# --- 12. ФУНКЦИЯ ФИНАЛИЗАЦИИ, МОДЕРАЦИИ И ВОТЕРМАРОК ---
async def finalize_item_publishing(message: Message, state: FSMContext, from_user):
    data = await state.get_data()
    await state.clear()

    brand_clean = str(data.get("brand", "")).strip().lower()
    original_file_id = data.get("photo")
    tags_photo_id = data.get("tags_photo")
    
    watermark_active = await get_watermark_setting() 
    print(f"[DEBUG] Статус вотермарки из БД: {watermark_active}")

    if watermark_active:
        print("[DEBUG] Начинаю накладывать вотермарку...")
        try:
            photo_to_send = await add_watermark_on_photo(message.bot, original_file_id)
            print("[DEBUG] Вотермарка наложена успешно!")
        except Exception as e:
            print(f"[DEBUG] Ошибка при наложении: {e}")
            photo_to_send = original_file_id
    else:
        photo_to_send = original_file_id

    # ВЕТВЛЕНИЕ: Доверенный бренд или нет
    if brand_clean in TRUSTED_BRANDS:
        async with async_session() as session:
            result = await session.execute(select(User).where(User.tg_id == from_user.id))
            user = result.scalar_one_or_none()

        if user and getattr(user, 'is_admin', False):
            sent_msg = await message.answer_photo(photo=photo_to_send, caption="✅ Объявление успешно выложено!", reply_markup=admin_keyboard())
        else:
            sent_msg = await message.answer_photo(photo=photo_to_send, caption="✅ Ваше объявление успешно выложено!", reply_markup=main_user_kb())

        final_file_id = sent_msg.photo[-1].file_id
        data["photo"] = final_file_id
        await add_item(data=data, owner_id=from_user.id, owner_username=from_user.username)

    else:
        item_key = f"{from_user.id}_{data.get('title')}"
        mod_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"mod_approve_{item_key}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod_reject_{item_key}")
            ]
        ])


        avg_rating, count = await get_seller_rating(from_user.id)
        is_scam = await check_is_scam(from_user.id)

        if is_scam:
            seller_status = "🚨 <b>ВНИМАНИЕ: Продавец в ЧЁРНОМ СПИСКЕ (SCAM)!</b> 🚨"
        else:
            seller_status = f"⭐ Рейтинг продавца: {avg_rating}/10 ({count} отзывов)"


        
        
        caption = (
            f"⚠️ <b>Новый товар на модерацию!</b>\n\n"
            f"<b>{data.get('title')}</b>\n"
            f"📝 {data.get('description')}\n"
            f"🛡 Подлинность: <b>{data.get('authenticity', 'Не указано')}</b>\n"
            f"🏷 Бренд: {data.get('brand')} (Неизвестный!)\n"
            f"📏 Размер: {data.get('size')}\n"
            f"💰 Цена: {data.get('price')} грн\n"
            f"🏷 Фото бирок: <b>{'✅ Прикреплено к базе' if tags_photo_id else '❌ Отсутствует'}</b>\n\n"
            f"👤 Продавец: @{from_user.username or 'без юзернейма'} (ID: <code>{from_user.id}</code>)\n"
            f"{seller_status}"  # <--- ДОБАВЛЯЕМ СЮДА
        )

        try:
            sent_msg = await message.bot.send_photo(chat_id=ADMIN_ID, photo=photo_to_send, caption=caption, parse_mode="HTML", reply_markup=mod_kb)
            final_file_id = sent_msg.photo[-1].file_id

            data["photo"] = final_file_id
            PENDING_ITEMS[item_key] = {
                "data": data,
                "owner_id": from_user.id,
                "owner_username": from_user.username
            }
            await message.answer("⏳ Ваше объявление отправлено на модерацию администратору из-за неузнанного бренда.")
            
        except Exception:
            data["photo"] = original_file_id
            await add_item(data=data, owner_id=from_user.id, owner_username=from_user.username)
            await message.answer("✅ Ваше объявление успешно выложено (модератор недоступен)!")


@router.callback_query(F.data.startswith("mod_reject_"))
async def moderation_reject(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав ⛔", show_alert=True)
        return
    
    item_key = callback.data.replace("mod_reject_", "")
    PENDING_ITEMS.pop(item_key, None)

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ <b>СТАТУС: Отклонено модератором</b>", parse_mode="HTML")
    await callback.answer("Товар отклонен.")


@router.callback_query(F.data.startswith("mod_approve_"))
async def moderation_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав ⛔", show_alert=True)
        return

    item_key = callback.data.replace("mod_approve_", "")
    item_info = PENDING_ITEMS.pop(item_key, None)

    if item_info:
        await add_item(
            data=item_info["data"], 
            owner_id=item_info["owner_id"], 
            owner_username=item_info["owner_username"]
        )

    await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ <b>СТАТУС: Одобрено и опубликовано в каталог</b>", parse_mode="HTML")
    await callback.answer("Товар успешно одобрен и добавлен в каталог!")

@router.message(F.text == '🎯 Снайпер')
async def sniper_filter_handler(message: Message, state: FSMContext):
    is_sniper_active = await get_sniper_filter_setting()

    if not is_sniper_active:
        await message.answer("⚠️ Функция «Снайпер» временно отключена администратором.")
        return

    user = await get_user(message.from_user.id)

    now = datetime.now()
    is_vip_active = user and user.is_vip and (user.vip_until is None or user.vip_until > now)

    if not is_vip_active:
        await message.answer(
            "👑 **Функция доступна только VIP-пользователям!**\n\n"
            "Снайпер позволяет мгновенно получать уведомления о новых товарах. "
            "Приобретите VIP-статус, чтобы открыть доступ к этой функции."
        )
        return


    await state.set_state(AddSniper.link)
    await message.answer("🎯 **Настройка Снайпера**\n\nОтправьте ссылку на поиск OLX с выставленными фильтрами (цена, город и т.д.):")


@router.message(AddSniper.link)
async def process_sniper_filter_link(message: Message, state: FSMContext):
    link_text = message.text.strip()
    
    if link_text.startswith("http://") or link_text.startswith("https://") or link_text.startswith("www"):
        await add_sniper_filter(user_id=message.from_user.id, url=link_text)
        await state.clear()
        await message.answer("✅ Ссылка успешно добавлена! Снайпер начал отслеживание.")
    else:
        await message.answer("⚠️ Пожалуйста, введите корректный адрес ссылки (начинающийся с http:// или https://).")

    


# --- 6. МОИ ОБЪЯВЛЕНИЯ ---

@router.message(F.text == "📦 Мои объявления")
async def my_items_cmd(message: Message):
    items = await get_users_items(message.from_user.id)
    if not items:
        await message.answer("У вас пока нет выложенных объявлений 📦")
        return
    await message.answer("📦 Ваши объявления:", reply_markup=await my_items_keyboard(items))


@router.callback_query(F.data == "my_items")
async def my_items_callback(callback: CallbackQuery):
    items = await get_users_items(callback.from_user.id)
    await callback.message.delete()
    if not items:
        await callback.message.answer("У вас пока нет выложенных объявлений 📦")
        await callback.answer()
        return
    await callback.message.answer("📦 Ваши объявления:", reply_markup=await my_items_keyboard(items))
    await callback.answer()


@router.callback_query(F.data.startswith('myitem_'))
async def my_item_detail(callback: CallbackQuery):
    item_id = int(callback.data.split('_')[1])
    item = await get_item(item_id)
    
    if not item:
        await callback.answer("Товар не найден или уже был удален.", show_alert=True)
        return

    text = (
        f"<b>{item.title}</b>\n\n"
        f"{item.description}\n\n"
        f"📏 Размер: {item.size if item.size else 'Не указан'}\n"
        f"💰 Цена: <b>{item.price} грн</b>"
    )

    if item.photo:
        await callback.message.answer_photo(
            photo=item.photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=await my_item_details_keyboard(item_id)
        )
    else:
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=await my_item_details_keyboard(item_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith('delitem_'))
async def delete_item_handler_real(callback: CallbackQuery):
    item_id = int(callback.data.split('_')[1])
    await delete_item(item_id)
    await callback.answer("Объявление успешно удалено! ❌", show_alert=True)
    
    items = await get_users_items(callback.from_user.id)
    await callback.message.delete()
    
    if not items:
        await callback.message.answer("У вас больше нет активных объявлений 📦")
    else:
        await callback.message.answer("📦 Ваши объявления:", reply_markup=await my_items_keyboard(items))

# --- 7. ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ---

@router.message(F.text.contains("Мой аккаунт"))
async def my_account(message: Message):
    user = await get_user(message.from_user.id)

    if user is None:
        await set_user(message.from_user.id)
        user = await get_user(message.from_user.id)

    if user is None:
        await message.answer("Произошла ошибка при получении профиля. Попробуйте ввести /start")
        return

    country = user.country if user.country else "Не указано"
    city = user.city if user.city else "Не указано"
    full_name = user.full_name if user.full_name else "Не указано"
    phone = user.phone if user.phone else "Не указано"

    text = (
        f"👤 <b>Ваш профиль:</b>\n\n"
        f"🌍 <b>Страна:</b> {country}\n"
        f"🏙 <b>Город:</b> {city}\n"
        f"📛 <b>ФИО:</b> {full_name}\n"
        f"📞 <b>Телефон:</b> {phone}"
    )

    await message.answer(text, reply_markup=account_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "edit_profile")
async def edit_my_profile(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserProfile.country)
    await callback.message.answer("Введите вашу страну:")
    await callback.answer()


@router.message(UserProfile.country)
async def user_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text)
    await state.set_state(UserProfile.city)
    await message.answer("Введите ваш город:")


@router.message(UserProfile.city)
async def user_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(UserProfile.full_name)
    await message.answer("Введите ваше ФИО:")


@router.message(UserProfile.full_name)
async def user_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(UserProfile.phone)
    await message.answer("Введите ваш номер телефона:")


@router.message(UserProfile.phone)
async def user_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()

    await update_user_profile(
        tg_id=message.from_user.id,
        country=data.get('country'),
        city=data.get('city'),
        full_name=data.get('full_name'),
        phone=data.get('phone')
    )

    await state.clear()
    await message.answer("✅ Ваш профиль успешно обновлен!", reply_markup=main_user_kb())





@router.callback_query(F.data.startswith("toggle_fav:"))
async def toggle_fav_handler(call: CallbackQuery):
    item_id = int(call.data.split(":")[1])
    user_id = call.from_user.id

    is_added = await toggle_favorite(user_id=user_id, item_id=item_id)

    if is_added:
        await call.answer("❤️ Товар добавлен в Избранное!", show_alert=False)
    else:
        await call.answer("💔 Товар удален из Избранного", show_alert=False)

    kb = item_card_keyboard(item_id=item_id, is_fav=is_added)
    await call.message.edit_reply_markup(reply_markup=kb)



@router.message(F.text == "⭐ Избранное")
async def show_favorites_handler(message: Message, session: AsyncSession):
   items = await get_user_favorites(message.from_user.id)

   if not items:
        await message.answer("Ваш список избранного пуст 💔")
        return

   await message.answer(f"⭐ Ваши избранные товары ({len(items)}):")


   for item in items:
        caption_text = (
            f"<b>{item.title}</b>\n\n"
            f"Размер: {item.size}\n"
            f"Цена: {item.price} ₽\n"
            f"{item.description}"
        )


        kb = favorite_item_kb(item.id)
        
        # Если у товара есть фото:
        if item.photo:
            await message.answer_photo(
                photo=item.photo,
                caption=caption_text,
                parse_mode="HTML",
                reply_markup=kb
            )
        else:
            await message.answer(
                text=caption_text,
                parse_mode="HTML",
                reply_markup=kb
            )

@router.callback_query(F.data.startswith("remove_fav_"))
async def remove_from_favorite_handler(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    
    await toggle_favorite(user_id=user_id, item_id=item_id)

    try:
        await callback.message.delete()
    except Exception:
        pass
    
    # Показываем всплывающее уведомление
    await callback.answer("Товар удалён из избранного!", show_alert=False)


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[3])
    user_id = callback.from_user.id

    # Вызываем функцию добавления в корзину
    await add_to_basket(user_id=user_id, item_id=item_id)

    # Всплывающее окно сверху экрана
    await callback.answer("🛒 Товар успешно добавлен в корзину!", show_alert=True)



@router.callback_query(F.data.startswith("edit_price:"))
async def start_edit_price(call: CallbackQuery, state: FSMContext):
    item_id = int(call.data.split(":")[1])

    await state.update_data(item_id=item_id)
    await state.set_state(EditItem.price)
    
    await call.message.answer("✏️ Введите новую цену для товара (в грн):")
    await call.answer()




@router.message(EditItem.price)
async def process_new_price(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("❌ Введите корректное число!")
        return

    new_price = float(message.text)
    data = await state.get_data()
    item_id = data["item_id"]

    # Достаем товар из БД
    item = await session.get(Item, item_id)
    if not item:
        await message.answer("❌ Товар не найден.")
        await state.clear()
        return

    old_price = item.price
    item.price = new_price
    await session.commit()

    await message.answer(f"✅ Цена успешно изменена с {int(old_price)} на {int(new_price)} грн!")
    await state.clear()

    # Запускаем алерт о скидке
    await notify_price_drop(
        bot=message.bot,
        item_id=item.id,
        item_title=item.title,
        old_price=old_price,
        new_price=new_price
    )


# --- 8. СЛУЖЕБНЫЕ И УНИВЕРСАЛЬНЫЕ ЛОВУШКИ (СТРОГО В КОНЦЕ) ---

@router.message(F.text == "🔍 ДЕБАГ БАЗЫ")
async def debug_database_handler(message: Message):
    async with async_session() as session:
        cats = (await session.scalars(select(Categories))).all()
        items = (await session.scalars(select(Item))).all()
        
        print(f"\n--- ДЕБАГ БАЗЫ ДАННЫХ ---")
        print(f"Категории в БД ({len(cats)} шт):")
        for c in cats:
            print(f"ID: {c.id} | Название: {c.name}")
            
        print(f"\nТовары в БД ({len(items)} шт):")
        for i in items:
            print(f"ID: {i.id} | Название: {i.title} | Category_ID: {i.category_id} | Бренд: {i.brand}")
        print(f"--------------------------\n")
        
    await message.answer("✅ Дебаг-информация выведена в терминал (консоль)! Посмотри туда.")


@router.message(F.text)
async def text_handler(message: Message):
    user = await get_user(message.from_user.id)
    if user:
        return

    await process_invite_code(message, message.text.strip())


@router.callback_query(F.data == "ignore")
async def ignore_click_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query()
async def catch_all_callbacks(callback: CallbackQuery):
    print(f"⚠️ НЕПЕРЕХВАЧЕННЫЙ CALLBACK: data='{callback.data}'")
    await callback.answer()