from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from states import Evaluator
from services.evaluator import get_full_evaluation

router = Router()

@router.message(F.text == "📊 AI-Оценщик")
async def evaluator_handler(message: Message, state: FSMContext):
    await state.set_state(Evaluator.waiting_for_query)
    await message.answer(
        "📊 **AI-Оценщик стоимости**\n\n"
        "Введите название вещи (например, `Nike Air Force` или `Stone Island Sweatshirt`):",
        parse_mode="Markdown"
    )

@router.message(Evaluator.waiting_for_query)
async def process_evaluation(message: Message, state: FSMContext, session: AsyncSession):
    query = message.text or ""
    wait_msg = await message.answer("🔄 *Сканируем базу бота и рынок OLX...*", parse_mode="Markdown")

    res = await get_full_evaluation(session, query)

    if res["status"] == "not_found":
        await wait_msg.edit_text("❌ К сожалению, ничего не найдено ни в нашей базе, ни на открытом рынке OLX.")
        await state.clear()
        return

    # Формируем отчет
    text_lines = [f"📊 **Аналитика рынка для:** `{res['query']}`\n"]

    # Данные из нашего бота
    if res["internal"]:
        text_lines.append(
            f"🏠 **В нашем боте:**\n"
            f"├ Найдено: **{res['internal']['count']} шт.**\n"
            f"└ Средняя цена: **{res['internal']['avg']} грн**\n"
        )
    else:
        text_lines.append("🏠 **В нашем боте:** Лотов пока нет\n")

    # Данные с OLX
    if res["olx"]:
        text_lines.append(
            f"🌐 **Рынок OLX (Украина):**\n"
            f"├ Найдено лотов: **{res['olx']['count']} шт.**\n"
            f"├ Диапазон: **{res['olx']['min']} - {res['olx']['max']} грн**\n"
            f"└ Средняя цена: **{res['olx']['avg']} грн**\n"
        )
    else:
        text_lines.append("🌐 **Рынок OLX:** Совпадений не найдено\n")

    # Итоговый AI-вердикт
    text_lines.append(
        f"💡 **Рекомендация AI:**\n"
        f"🎯 Рыночная цена: **~{res['recommended_price']} грн**\n"
        f"⚡️ Для быстрой продажи: **~{res['fast_sale_price']} грн**"
    )

    await wait_msg.edit_text("\n".join(text_lines), parse_mode="Markdown")
    await state.clear()