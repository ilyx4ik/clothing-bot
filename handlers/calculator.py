from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import CurrencyCalcState
from keyboards.builders import currency_kb
from services.calculator import calculate_total

router = Router()


# 1. Запуск калькулятора (по кнопке меню или команде)
@router.message(F.text == "🧮 Калькулятор валют")
async def start_calc(message: Message, state: FSMContext):
    await state.set_state(CurrencyCalcState.waiting_for_currency)
    await message.answer("Выберите валюту, в которой указана цена товара:", reply_markup=currency_kb())


# 2. Обработка выбора валюты
@router.callback_query(F.data.startswith("calc_curr:"), CurrencyCalcState.waiting_for_currency)
async def process_currency(call: CallbackQuery, state: FSMContext):
    currency = call.data.split(":")[1]
    await state.update_data(currency=currency)
    await state.set_state(CurrencyCalcState.waiting_for_price)
    
    await call.message.edit_text(
        f"Введите цену товара в **{currency}** (например: `120` или `49.99`):", 
        parse_mode="Markdown"
    )
    await call.answer()


# 3. Обработка ввода цены
@router.message(CurrencyCalcState.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму числом (например: `150`):", parse_mode="Markdown")
        return

    await state.update_data(price=price)
    await state.set_state(CurrencyCalcState.waiting_for_weight)
    
    await message.answer(
        "Укажите примерный вес вещи в кг\n*(например, `0.5` для худи/футболки или `1.2` для кроссовок)*:",
        parse_mode="Markdown"
    )


# 4. Обработка ввода веса и вывод чека
@router.message(CurrencyCalcState.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(",", "."))
        if weight <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите вес числом в килограммах (например: `0.5` или `1`):", parse_mode="Markdown")
        return

    data = await state.get_data()
    res = await calculate_total(price=data["price"], currency=data["currency"], weight_kg=weight)
    
    receipt = (
        f"🧾 **Расчёт стоимости доставки в UAH:**\n\n"
        f"💰 Цена товара: `{res['price_orig']} {res['currency']}` (~`{res['item_cost_uah']} UAH` по курсу `{res['rate']}`)\n"
        f"📦 Доставка ({weight} кг): ~`{res['shipping_cost_uah']} UAH`\n"
        f"-----------------------------------\n"
        f"💳 **Итого к оплате:** ~`{res['total_uah']} UAH`"
    )
    
    await state.clear()
    await message.answer(receipt, parse_mode="Markdown")