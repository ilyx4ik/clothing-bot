from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def notify_price_drop(
    bot: Bot, 
    user_id: int, 
    title: str, 
    old_price: int, 
    new_price: int, 
    url: str
):
    discount = old_price - new_price
    percent = int((discount / old_price) * 100)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Открыть лот на OLX", url=url)]
    ])
    
    text = (
        f"👑 **VIP-УВЕДОМЛЕНИЕ: СНИЖЕНИЕ ЦЕНЫ!**\n\n"
        f"📦 **Товар:** {title}\n"
        f"📉 **Старая цена:** `{old_price} грн`\n"
        f"🏷 **Новая цена:** `{new_price} грн`\n"
        f"💰 **Вы экономите:** `{discount} грн` (-{percent}%)\n\n"
        f"⚡ *Успей забрать, пока цена упала!*"
    )
    
    try:
        await bot.send_message(
            chat_id=user_id, 
            text=text, 
            parse_mode="Markdown", 
            reply_markup=kb
        )
    except Exception as e:
        print(f"⚠️ Не удалось отправить VIP-уведомление пользователю {user_id}: {e}")