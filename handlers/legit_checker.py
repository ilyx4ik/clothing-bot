from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import LegitCheck
from keyboards.builders import get_legit_check_kb
from services.style_codes import get_guide
from services.legit_check import check_item_code
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

# 1. Нажатие на кнопку "Legit Check" в главном меню
@router.message(F.text == "🛡 Legit Check")
async def show_legit_menu(message: Message):
    await message.answer(
        "Выберите нужный инструмент для проверки оригинальности:",
        reply_markup=get_legit_check_kb()
    )

# 2. Выбор "Проверить CLG-код"
@router.callback_query(F.data == "lc_clg")
async def start_clg_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LegitCheck.waiting_for_clg)
    await callback.message.answer(
        "Введите 12-значный CLG-код либо Style Code (например, `123456789012` либо же 'CW2288-111'):",
        parse_mode="Markdown"
    )
    await callback.answer()

# 3. Выбор "Гайды по брендам"
@router.callback_query(F.data == "lc_guides")
async def start_guides_check(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LegitCheck.waiting_for_brand)
    await callback.message.answer(
        "Введите название бренда (например, `nike` или `arcteryx`):"
    )
    await callback.answer()

# 4. Обработка ввода CLG-кода
@router.message(LegitCheck.waiting_for_clg)
async def process_clg(message: Message, state: FSMContext):
    raw_text = message.text or ""
    result = check_item_code(raw_text)

    # 1. Вариант для Certilogo (12 цифр)
    if result["type"] == "clg":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🌐 Открыть сайт Certilogo", url=result["url"])]
            ]
        )
        await message.answer(
            result["message"],
            reply_markup=kb,
            parse_mode="Markdown"
        )
        await state.clear()

    # 2. Вариант для Nike / Jordan Style Code
    elif result["type"] == "nike":
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔎 Искать на StockX", url=result["stockx_url"])],
                [InlineKeyboardButton(text="🌐 Искать в Google", url=result["google_url"])]
            ]
        )
        await message.answer(
            result["message"],
            reply_markup=kb,
            parse_mode="Markdown"
        )
        await state.clear()

    # 3. Всё остальное (если формат не подошёл)
    else:
        await message.answer(
            result["message"],
            parse_mode="Markdown"
        )

# 5. Обработка ввода названия бренда
@router.message(LegitCheck.waiting_for_brand)
async def process_brand_guide(message: Message, state: FSMContext):
    brand_name = message.text or ""
    guide = get_guide(brand_name)
    
    if guide:
        await message.answer(
            f"📌 **{guide['title']}**\n\n"
            f"{guide['info']}",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Гайд для этого бренда пока отсутствует.\n"
            "Попробуйте ввести: `nike` или `arcteryx`",
            parse_mode="Markdown"
        )