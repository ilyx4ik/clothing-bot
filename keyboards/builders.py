from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardBuilder
from database.requests import get_categories, get_items_by_category, toggle_favorite
from aiogram.types import KeyboardButton, InlineKeyboardButton
from database.models import Item, Favorite

async def categories_keyboard():
    categories = await get_categories()
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(text=category.name, callback_data=f"category_{category.id}")

    builder.adjust(2)
    return builder.as_markup()

async def items_keyboard(category_id: int):
    items = await get_items_by_category(category_id)
    builder = InlineKeyboardBuilder()

    for item in items:
        builder.button(text=item.title, callback_data=f"item_{item.id}")

    builder.button(text=" Назад", callback_data="back_to_categories")
    builder.adjust(1)
    return builder.as_markup()

async def item_details_keyboard(category_id: int, item_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(text=" Добавить в корзину", callback_data=f"buy_{item_id}")
    builder.button(text=" Назад", callback_data=f"category_{category_id}")
    builder.adjust(1)
    return builder.as_markup()

async def basket_keyboard(basket_items=None):
    builder = InlineKeyboardBuilder()

    if basket_items:
        for item in basket_items:
            builder.button(
                text=f"❌ {item.title}", 
                callback_data=f"delete_cart_item_{item.id}"
            )

    builder.button(text="💳 Оформить заказ", callback_data="checkout")
    builder.button(text="🗑 Очистить корзину", callback_data="clear_basket")
    builder.button(text="🔙 Назад в категории", callback_data="back_to_categories")
    builder.adjust(1)
    return builder.as_markup()

async def admin_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 История заказов", callback_data="admin_orders_history")],
            [InlineKeyboardButton(text="⚙️ Настройки бота", callback_data="admin_settings_menu")], 
            [InlineKeyboardButton(text="👤 Поиск пользователя", callback_data="admin_search_user")],
            [InlineKeyboardButton(text="👑 Выдать VIP", callback_data="admin_give_vip")],
            [InlineKeyboardButton(text="📢 Автопостинг ТГ", callback_data="admin_autopost_settings")],
            [InlineKeyboardButton(text="➕ Добавить категорию", callback_data="add_category")],
            [InlineKeyboardButton(text="📊 Экспресс-статистика", callback_data="stats_handler")],
            [InlineKeyboardButton(text="📁 Выгрузка Excel", callback_data="admin_stats_excel")],
            [InlineKeyboardButton(text="📢 Массовая рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🔑 Сгенерировать инвайт", callback_data="generate_invite")]
            ]
    )
    return keyboard

def ban_user_keyboard(target_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    button_text = "🔓 Разблокировать" if is_banned else "🔒 Заблокировать"
    button_textt = "Выдать страйк"

    keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"toggle_ban:{target_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=button_textt,
                        callback_data=f"strike:{target_id}"
                    )
                ]
            ]
        )

    return keyboard

def admin_user_manage_kb(target_id: int, is_banned: bool, is_vip: bool) -> InlineKeyboardMarkup:
    ban_btn_text = "🔓 Разблокировать" if is_banned else "🔒 Заблокировать"
    vip_btn_text = "❌ Забрать VIP" if is_vip else "👑 Выдать VIP"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=ban_btn_text, callback_data=f"toggle_ban:{target_id}"),
                InlineKeyboardButton(text=vip_btn_text, callback_data=f"toggle_vip:{target_id}")
            ]
        ]
    )

    return keyboard


def admin_settings_kb(watermark_enabled: bool, sniper_enabled: bool) -> InlineKeyboardMarkup:
    watermark_status = "🌊 Watermark: ✅ ВКЛ" if watermark_enabled else "🌊 Watermark: ❌ ВЫКЛ"
    sniper_status = "🎯 Снайпер: ✅ ВКЛ" if sniper_enabled else "🎯 Снайпер: ❌ ВЫКЛ"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=watermark_status, callback_data="toggle_setting:watermark"),
                InlineKeyboardButton(text=sniper_status, callback_data="toggle_setting:sniper")
            ]
        ]
    )

    return keyboard


def autopost_toggle_keyboard(is_enabled: bool) -> InlineKeyboardMarkup:
    status_text = "🟢 Включен" if is_enabled else "🔴 Выключен"
    action_text = "Отключить 🔴" if is_enabled else "Включить 🟢"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"Статус: {status_text}", callback_data="ignore"))
    builder.row(InlineKeyboardButton(text=f"Переключить: {action_text}", callback_data="toggle_autopost_state"))
    builder.row(InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_main"))
    return builder.as_markup()

def main_user_kb():
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="🛒 Каталог"),
        KeyboardButton(text="➕ Продать вещь")
    )
    builder.row(
        KeyboardButton(text="🛒 Корзина"),
        KeyboardButton(text="⭐ Избранное"),
        KeyboardButton(text="📦 Мои объявления")
    )
    builder.row(
        KeyboardButton(text="🛡 Legit Check"),
        KeyboardButton(text="📊 AI-Оценщик")
    )
    builder.row(
        KeyboardButton(text="🎯 Снайпер"),
        KeyboardButton(text="📦 Найденные лоты"),
        KeyboardButton(text="🎯 Мои ссылки")
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="🆘 Поддержка")
    )
    
    return builder.as_markup(resize_keyboard=True)

def authenticity_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оригинал", callback_data="auth_original")],
            [InlineKeyboardButton(text="✨ High Quality / Топ-реплика", callback_data="auth_hq")],
            [InlineKeyboardButton(text="🏷 Бюджетная реплика", callback_data="auth_replica")]
        ]
    )


def skip_tags_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_tags")]
        ]
    )


def catalog_type_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Объявления пользователей", callback_data="catalog_users")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Парсер (OLX / Grailed)", callback_data="catalog_parser")
    )
    return builder.as_markup()

def parser_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 Общие ссылки (OLX/Grailed)", callback_data="parser_global_links")
    )
    builder.row(
        InlineKeyboardButton(text="🔗 Парсинг по моей ссылке", callback_data="parser_custom_link")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="catalog_main")
    )
    return builder.as_markup()

async def my_items_keyboard(items):
    builder = InlineKeyboardBuilder()

    for item in items:
        builder.button(text=item.title, callback_data=f"myitem_{item.id}")

    builder.adjust(1)
    return builder.as_markup()

async def my_item_details_keyboard(item_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить объявление", callback_data=f"delitem_{item_id}")
    builder.button(text="🎨 Создать карточку", callback_data=f"gen_card:{item_id}")
    builder.button(text="✏️ Изменить цену", callback_data=f"edit_price:{item_id}")
    builder.button(text="⬅️ Назад к моим товарам", callback_data="my_items")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_main")]
        ]
    )

def post_success_kb(is_admin: bool = False):
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.button(text="⬅️ В админ-панель", callback_data="admin_panel")
    builder.button(text="📦 Мои объявления", callback_data="my_items")
    return builder.as_markup()

def item_card_keyboard(item_id: int, index: int, total_items: int, category_id: int, brand: str = None, is_favorite: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()


    favorite_text = "💔 Удалить из избранного" if is_favorite else "❤️ В избранное"
    
    brand_suffix = f"_{brand}" if brand else ""

    if index > 0:
        builder.button(
            text="⬅️", 
            callback_data=f"page_{category_id}_{index - 1}{brand_suffix}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")

    builder.button(text=f"{index + 1}/{total_items}", callback_data="ignore")

    if index < total_items - 1:
        builder.button(
            text="➡️", 
            callback_data=f"page_{category_id}_{index + 1}{brand_suffix}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")

    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="🛒 В корзину", callback_data=f"buy_{item_id}")
    )
    builder.row(
        InlineKeyboardButton(text=favorite_text, callback_data=f"toggle_fav:{item_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к брендам", callback_data=f"category_{category_id}")
    )

    return builder.as_markup()

def brands_keyboard(category_id: int, brands: list):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👀 Показать всё подряд", callback_data=f"show_all_{category_id}"))

    for brand in brands:
        if brand:  
            builder.add(InlineKeyboardButton(text=f"🏷 {brand}", callback_data=f"brand_{category_id}_{brand}"))

    builder.adjust(1, 2)
    builder.row(InlineKeyboardButton(text="🔙 К категориям", callback_data="back_to_categories"))
    return builder.as_markup()

def account_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать профиль", callback_data="edit_profile")
    builder.adjust(1)
    return builder.as_markup()

def cart_keyboard(cart_items: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for item in cart_items:
        builder.row(
            InlineKeyboardButton(text=f"📦 {item.title} ({item.price} грн)", callback_data=f"show_item_{item.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"delete_cart_item_{item.id}")
        )

    builder.row(
        InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout_order")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить всё", callback_data="clear_basket"),
        InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")
    )

    return builder.as_markup()



def support_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆘 Написать в поддержку", callback_data="contact_support")
    )
    return builder.as_markup()


def get_admin_reply_keyboard(ticket_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="💬 Ответить", 
            callback_data=f"reply_ticket:{ticket_id}"  
        )
    )
    return builder.as_markup()


def favorite_keyboard(item_id: int, is_favorite: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    text = "💔 Убрать из избранного" if is_favorite else "❤️ В избранное"
    builder.button(text=text, callback_data=f"toggle_fav:{item_id}")
    return builder.as_markup()




def favorite_item_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 В корзину", callback_data=f"add_to_cart_{item_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Удалить из избранного", callback_data=f"remove_fav_{item_id}")
            ]
        ]
    )


def get_platforms_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="OLX", callback_data="platform_olx")
            ],
            [
                InlineKeyboardButton(text="Grailed", callback_data="platform_grailed")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="parser_back")
            ]
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="main_user_kb")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="parser_back")
            ]
        ]
    )


def get_categories_kb_parser() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👟 Обувь", callback_data="category_shoes")
            ],
            [
                InlineKeyboardButton(text="👕 Одежда", callback_data="category_clothes")
            ],
            [
                InlineKeyboardButton(text="💍 Аксессуары", callback_data="category_acc")
            ],
            [
                InlineKeyboardButton(text="🌐 Все категории", callback_data="category_all")
            ]
        ]
    )



def get_found_item_kb(index: int, total: int, url: str, item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # 1. Ссылка на OLX
    builder.row(
        InlineKeyboardButton(text="🔗 Открыть объявление", url=url)
    )

    # 2. Навигация (Назад / Счётчик / Вперёд)
    nav_buttons = []
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"found_page_{index - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔️", callback_data="ignore"))

    nav_buttons.append(InlineKeyboardButton(text=f"📍 {index + 1}/{total}", callback_data="ignore"))

    if index < total - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"found_page_{index + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔️", callback_data="ignore"))

    builder.row(*nav_buttons)

    # 3. Кнопка удаления этого лота и полная очистка
    builder.row(
        InlineKeyboardButton(text="❌ Удалить этот лот", callback_data=f"delete_item_{item_id}_{index}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить весь список", callback_data="clear_found_items")
    )

    return builder.as_markup()


def get_my_filters_kb(filters: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for i, filter in enumerate(filters, start=1):
        builder.button(text=f"🔗 Ссылка №{i}", url = filter.url)
        builder.button(text="❌ Удалить", callback_data=f"delete_filter_{filter.id}")
    builder.adjust(2)
    return builder.as_markup()



def get_condition_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✨ Новое", callback_data="cond_new"),
                InlineKeyboardButton(text="👌 Б/У (Отличное)", callback_data="cond_used")
            ],
            [
                InlineKeyboardButton(text="⏩ Любое", callback_data="skip_condition")  # 👈 Кнопка пропуска!
            ]
        ]
    )


def get_size_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="S", callback_data="size_S"),
                InlineKeyboardButton(text="M", callback_data="size_M"),
                InlineKeyboardButton(text="L", callback_data="size_L"),
                InlineKeyboardButton(text="XL", callback_data="size_XL"),
            ],
            [
                InlineKeyboardButton(text="⏩ Любое", callback_data="skip_size")
            ]
        ]
    )


def get_skip_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data=callback_data)]
        ]
    )



def get_rating_keyboard(seller_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"rate:{seller_id}:{i}")

    builder.adjust(5, 5)
    return builder.as_markup()

def skip_comment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить ⏩", callback_data="skip_comment")]
        ]
    )


def currency_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💵 USD", callback_data="calc_curr:USD"),
                InlineKeyboardButton(text="💶 EUR", callback_data="calc_curr:EUR")
            ],
            [
                InlineKeyboardButton(text="🇵🇱 PLN", callback_data="calc_curr:PLN"),
                InlineKeyboardButton(text="🇨🇳 CNY", callback_data="calc_curr:CNY")
            ]
        ]
    )



def wtb_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Все заявки", callback_data="wtb_view_all")
            ],
            [
                InlineKeyboardButton(text="➕ Создать заявку", callback_data="wtb_create")
            ],
            [
                InlineKeyboardButton(text="👤 Мои заявки", callback_data="wtb_my_items")
            ]
        ]
    )


def wtb_card_kb(username: str | None, user_id: int) -> InlineKeyboardMarkup:
    if username:
        user_url = f"https://t.me/{username}"
    else:
        user_url = f"tg://user?id={user_id}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📩 Написать покупателю", url=user_url)
            ]
        ]
    )


def wtb_my_card_kb(wtb_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Удалить заявку", callback_data=f"wtb_delete:{wtb_id}")
            ]
        ]
    )


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_legit_check_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛡 Проверить CLG-код", callback_data="lc_clg"),
                InlineKeyboardButton(text="📚 Гайды по брендам", callback_data="lc_guides")
            ]
        ]
    )
    return kb