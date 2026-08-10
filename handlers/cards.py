from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile
from database.requests import get_item
from services.card_generator import generate_item_card

router = Router()


@router.callback_query(F.data.startswith("gen_card:"))
async def card_handler(callback: CallbackQuery, bot: Bot):
    item_id = int(callback.data.split(":")[1])

    await callback.answer("⏳ Генерируем карточку...")

    item = await get_item(item_id)

    if item and item.photo:
        photo_buffer = await bot.download(item.photo)
        photo_bytes = photo_buffer.read()

    card_io = await generate_item_card(
    image_bytes=photo_bytes,
    title=item.title,
    price=str(item.price),
    size=str(item.size),
    brand=str(item.brand)
    )

    photo_file = BufferedInputFile(card_io.getvalue(), filename="card.png")

    await callback.message.answer_photo(photo=photo_file, caption="🎨 Ваша карточка готова!")