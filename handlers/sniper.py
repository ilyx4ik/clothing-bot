from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

# 1. Импорт вашей модели БД (укажи правильный путь к файлу с моделями, если он отличается)
from database.models import SniperFilter 

# 2. Импорт клавиатур (укажи правильный путь к твоему файлу с клавиатурами)
from keyboards.builders import (
    get_skip_keyboard,
    get_size_keyboard,
    get_condition_keyboard
)

from states import AddFilter

# 3. Инициализация роутера
router = Router()



# 1. ВВОД ССЫЛКИ
@router.message(AddFilter.waiting_for_url)
async def process_sniper_url(message: Message, state: FSMContext):
    url = message.text.strip()
    await state.update_data(url=url)
    
    await state.set_state(AddFilter.waiting_for_brand)
    await message.answer(
        "Укажите бренд (например: Nike, Stone Island) или нажмите «Пропустить»:",
        reply_markup=get_skip_keyboard(callback_data="skip_brand")
    )


# 2. ВВОД ИЛИ ПРОПУСК БРЕНДА
@router.message(AddFilter.waiting_for_brand)
async def process_sniper_brand_text(message: Message, state: FSMContext):
    await state.update_data(brand=message.text.strip())
    await state.set_state(AddFilter.waiting_for_size)
    await message.answer(
        "Выберите или введите размер (S, M, L, 42...):",
        reply_markup=get_size_keyboard()
    )

@router.callback_query(AddFilter.waiting_for_brand, F.data == "skip_brand")
async def process_sniper_brand_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(brand=None)
    await callback.answer()
    await state.set_state(AddFilter.waiting_for_size)
    await callback.message.edit_text(
        "Выберите или введите размер (S, M, L, 42...):",
        reply_markup=get_size_keyboard()
    )


# 3. ВВОД ИЛИ ПРОПУСК РАЗМЕРА
@router.message(AddFilter.waiting_for_size)
async def process_size_text(message: Message, state: FSMContext):
    await state.update_data(size=message.text.strip())
    await state.set_state(AddFilter.waiting_for_condition)
    await message.answer(
        "Выберите состояние или нажмите «Пропустить»:",
        reply_markup=get_condition_keyboard()
    )

@router.callback_query(AddFilter.waiting_for_size, F.data.startswith("size_"))
async def process_size_callback(callback: CallbackQuery, state: FSMContext):
    size_value = callback.data.split("_")[1]  # Например, 'M' из 'size_M'
    await state.update_data(size=size_value)
    await callback.answer()
    await state.set_state(AddFilter.waiting_for_condition)
    await callback.message.edit_text(
        "Выберите состояние или нажмите «Пропустить»:",
        reply_markup=get_condition_keyboard()
    )

@router.callback_query(AddFilter.waiting_for_size, F.data == "skip_size")
async def process_size_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(size=None)
    await callback.answer()
    await state.set_state(AddFilter.waiting_for_condition)
    await callback.message.edit_text(
        "Выберите состояние или нажмите «Пропустить»:",
        reply_markup=get_condition_keyboard()
    )


# 4. ВВОД ИЛИ ПРОПУСК СОСТОЯНИЯ
@router.message(AddFilter.waiting_for_condition)
async def process_condition_text(message: Message, state: FSMContext):
    await state.update_data(condition=message.text.strip())
    await state.set_state(AddFilter.waiting_for_price)
    await message.answer(
        "Введите максимальную цену в $ (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard(callback_data="skip_price")
    )

@router.callback_query(AddFilter.waiting_for_condition, F.data.startswith("cond_"))
async def process_condition_callback(callback: CallbackQuery, state: FSMContext):
    cond_value = callback.data.split("_")[1]
    await state.update_data(condition=cond_value)
    await callback.answer()
    await state.set_state(AddFilter.waiting_for_price)
    await callback.message.edit_text(
        "Введите максимальную цену (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard(callback_data="skip_price")
    )

@router.callback_query(AddFilter.waiting_for_condition, F.data == "skip_condition")
async def process_condition_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(condition=None)
    await callback.answer()
    await state.set_state(AddFilter.waiting_for_price)
    await callback.message.edit_text(
        "Введите максимальную цену (или нажмите «Пропустить»):",
        reply_markup=get_skip_keyboard(callback_data="skip_price")
    )


# 5. ВВОД ИЛИ ПРОПУСК ЦЕНЫ И СОХРАНЕНИЕ В БАЗУ
@router.message(AddFilter.waiting_for_price)
async def process_price_text(message: Message, state: FSMContext, session: AsyncSession):
    raw_price = message.text.strip().replace(",", ".")
    
    # Проверка, что введено корректное число
    try:
        price_val = float(raw_price)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите корректную сумму числом (например: 1500 или 49.99):")
        return

    await save_sniper_filter(user_id=message.from_user.id, price=price_val, state=state, session=session)
    await message.answer("🎯 **Снайпер-фильтр успешно настроен и запущен!**", parse_mode="Markdown")

@router.callback_query(AddFilter.waiting_for_price, F.data == "skip_price")
async def process_price_skip(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    await save_sniper_filter(user_id=callback.from_user.id, price=None, state=state, session=session)
    await callback.message.edit_text("🎯 **Снайпер-фильтр успешно настроен и запущен!**", parse_mode="Markdown")


# 🛠 Вспомогательная функция сохранения в БД
async def save_sniper_filter(user_id: int, price: float | None, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
    new_filter = SniperFilter(
        user_id=user_id,
        url=data.get("url"),
        brand=data.get("brand"),
        size=data.get("size"),
        condition=data.get("condition"),
        price=price,
        is_active=True
    )
    
    session.add(new_filter)
    await session.commit()
    await state.clear()