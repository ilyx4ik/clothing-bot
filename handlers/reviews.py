from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from database.requests import add_review
from keyboards.builders import skip_comment_kb
from states import AddReview 

router = Router()


@router.callback_query(F.data.startswith("rate:"))
async def reviews_handler(callback: CallbackQuery, state: FSMContext):
    _, seller_id, score = callback.data.split(":")

    await state.update_data(seller_id=int(seller_id), score=int(score))
    await state.set_state(AddReview.waiting_for_comment)

    await callback.message.edit_text(
        text="Напишите текстовый отзыв о продавце или нажмите кнопку ниже:",
        reply_markup=skip_comment_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "skip_comment", AddReview.waiting_for_comment)
async def skip_comment_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Записываем в БД без комментария
    await add_review(
        seller_id=data["seller_id"],
        buyer_id=callback.from_user.id,
        rating=data["score"],
        comment=None,
    )

    await state.clear()
    await callback.message.edit_text("Спасибо! Ваш отзыв сохранен 👍")
    await callback.answer()


@router.message(F.text, AddReview.waiting_for_comment)
async def process_reviews_handler(message: Message, state: FSMContext):
    data = await state.get_data()

    # Записываем в БД с текстом сообщения как comment
    await add_review(
        seller_id=data["seller_id"],
        buyer_id=message.from_user.id,
        rating=data["score"],
        comment=message.text,
    )

    await state.clear()
    await message.answer("Спасибо! Ваш отзыв и комментарий сохранены 👍")