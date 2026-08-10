from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from states import AddWTB
from keyboards.builders import wtb_main_kb, wtb_card_kb, wtb_my_card_kb
from database.requests import add_wtb_item, get_wtb_items, delete_wtb_item

router = Router()


@router.message(F.text == "📌 Доска Спроса")
async def wishlist_handler(message: Message, state: FSMContext):
    await message.answer(
        text="Добро пожаловать в Доску Спроса! Выберите действие:",
        reply_markup=wtb_main_kb()  # 1. Добавили скобки ()
    )


@router.callback_query(F.data == "wtb_create")
async def create_wishlist_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddWTB.waiting_for_title)
    # 2. Отправляем сообщение в сам чат, а не во всплывающую плашку
    await callback.message.answer("Напишите название вещи и модель:")
    await callback.answer()


@router.message(AddWTB.waiting_for_title)
async def process_wishlist_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddWTB.waiting_for_size)
    await message.answer("Укажите размер (например: 43 EU, L, или '-'):")


@router.message(AddWTB.waiting_for_size)
async def process_wishlist_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text)
    await state.set_state(AddWTB.waiting_for_budget)
    await message.answer("Укажите ваш бюджет (только число):")


@router.message(AddWTB.waiting_for_budget)
async def final_wishlist(message: Message, state: FSMContext):
    raw_text = message.text.replace(",", ".")

    try:
        budget = float(raw_text)
        if budget <= 0:
            raise ValueError  
    except ValueError:
        await message.answer("Пожалуйста, введите корректный бюджет числом (например: 1500 или 2000.50):")
        return

    data = await state.get_data()

    # 3. Добавили await и передали уже проверенный float budget (вместо float(message.text))
    await add_wtb_item(
        user_id=message.from_user.id,
        user_username=message.from_user.username,
        title=data["title"],
        size=data["size"],
        budget=budget
    )

    await state.clear()
    await message.answer("✅ Заявка успешно опубликована!")


@router.callback_query(F.data == "wtb_view_all")
async def view_wishlist_handler(callback: CallbackQuery):
    items = await get_wtb_items()

    if not items:
        await callback.answer("Заявок пока нет", show_alert=True)
        return

    await callback.answer()  

    for item in items:
        text = (
            f"📌 **Ищу:** {item.title}\n"
            f"📏 **Размер:** {item.size}\n"
            f"💰 **Бюджет:** {item.budget} UAH"
        )
        
        await callback.message.answer(
            text=text,
            reply_markup=wtb_card_kb(username=item.user_username, user_id=item.user_id),
            parse_mode="Markdown"
        )


@router.callback_query(F.data == "wtb_my_items")
async def my_items_wishlist_handler(callback: CallbackQuery):
    # 4. Достаем заявки и фильтруем список по ID текущего пользователя
    items = await get_wtb_items()
    my_items = [item for item in items if item.user_id == callback.from_user.id]

    if not my_items:
        await callback.answer("У вас пока нет активных заявок", show_alert=True)
        return

    await callback.answer()

    for item in my_items:
        text = (
            f"📌 **Ищу:** {item.title}\n"
            f"📏 **Размер:** {item.size}\n"
            f"💰 **Бюджет:** {item.budget} UAH"
        )
        await callback.message.answer(
            text=text,
            reply_markup=wtb_my_card_kb(wtb_id=item.id),
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("wtb_delete:"))
async def delete_items_wishlist(callback: CallbackQuery):
    wtb_id = int(callback.data.split(":")[1])
    # 5. Исправлена опечатка callback.from.from_user.id -> callback.from_user.id
    await delete_wtb_item(wtb_id=wtb_id, user_id=callback.from_user.id)
    await callback.message.delete()
    await callback.answer("Заявка удалена!", show_alert=True)