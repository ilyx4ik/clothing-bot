import asyncio
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import FoundItem, User
from services.notifications import notify_price_drop


async def fetch_olx_price(url: str, session: aiohttp.ClientSession) -> int | None:
    """Парсит актуальную цену с карточки товара OLX."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status != 200:
                return None
            
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            
            # Ищем блок с ценой на OLX
            price_elem = soup.find("h3", {"data-testid": "ad-price-container"})
            if not price_elem:
                price_elem = soup.find("h2", {"class": lambda c: c and "css-" in c})
            
            if price_elem:
                # Извлекаем только цифры из текста "1 500 грн." -> 1500
                digits = "".join(filter(str.isdigit, price_elem.get_text()))
                return int(digits) if digits else None
    except Exception as e:
        print(f"⚠️ Ошибка парсинга цены по ссылке {url}: {e}")
    
    return None


async def start_vip_price_checker(bot, async_session_maker):
    """Фоновый процесс отслеживания скидок для VIP-пользователей."""
    print("👑 Воркер VIP Price Drop запущен!")
    
    while True:
        try:
            async with async_session_maker() as session:
                # Выбираем товары, принадлежащие пользователям со статусом is_vip = True
                stmt = (
                    select(FoundItem, User)
                    .join(User, FoundItem.user_id == User.tg_id)
                    .where(User.is_vip == True)
                )
                result = await session.execute(stmt)
                vip_items = result.all()

                if vip_items:
                    print(f"🔍 [VIP CHECKER]: Найдено товаров для проверки: {len(vip_items)}")
                    
                    async with aiohttp.ClientSession() as http_session:
                        for item, user in vip_items:
                            new_price = await fetch_olx_price(item.url, http_session)
                            
                            # Если цена найдена и она НИЖЕ сохранённой в базе
                            if new_price and new_price < item.price:
                                old_price = item.price
                                
                                # 1. Обновляем цену в БД
                                item.price = new_price
                                await session.commit()
                                
                                # 2. Отправляем алерты о снижении цены
                                await notify_price_drop(
                                    bot=bot,
                                    user_id=user.tg_id,
                                    title=item.title,
                                    old_price=old_price,
                                    new_price=new_price,
                                    url=item.url
                                )
                            
                            # Небольшая пауза между запросами к OLX, чтобы не забанили IP
                            await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Ошибка в VIP-воркере: {e}")

        # Проверяем цены каждые 30 минут (1800 секунд)
        await asyncio.sleep(1800)