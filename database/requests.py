from database.db import async_session
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Categories, Item, Basket, Order, BotSettings, SniperFilter, SupportTicket, Favorite, FoundItem, Rating, WTBItem
from sqlalchemy import select, delete, update, or_, func
from datetime import datetime, timedelta
from aiogram import Bot

async def set_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        if not user:
            session.add(User(tg_id=tg_id))
            await session.commit()

async def get_categories():
    async with async_session() as session:
        result = await session.scalars(select(Categories))
        return result.all()

async def get_items_by_category(category_id: int):
    async with async_session() as session:
        result = await session.scalars(select(Item).where(Item.category_id == category_id))
        return result.all()

async def get_item(item_id: int):
    async with async_session() as session:
        return await session.scalar(select(Item).where(Item.id == item_id))

async def add_to_basket(tg_id: int, item_id: int):
    async with async_session() as session:
        session.add(Basket(user_id=tg_id, item_id=item_id))
        await session.commit()

async def get_basket(tg_id: int):
    async with async_session() as session:
        result = await session.scalars(select(Basket).where(Basket.user_id == tg_id))
        return result.all()

async def delete_from_basket(user_id: int, item_id: int):
    async with async_session() as session:
        basket_item = await session.scalar(
            select(Basket).where(Basket.user_id == user_id, Basket.item_id == item_id)
        )
        if basket_item:
            await session.delete(basket_item)
            await session.commit()

async def clear_basket(tg_id: int):
    async with async_session() as session:
        await session.execute(delete(Basket).where(Basket.user_id == tg_id))
        await session.commit()

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАКАЗАМИ ---
async def create_order(user_id: int, user_name: str, phone: str, address: str, price: float):
    async with async_session() as session:
        order = Order(
            user_id=user_id,
            user_name=user_name,
            phone=phone,
            address=address,
            price=price
        )
        session.add(order)
        await session.commit()

async def get_all_orders():
    async with async_session() as session:
        result = await session.scalars(select(Order).order_by(Order.created_at.desc()))
        return result.all()

async def add_category(name: str):
    async with async_session() as session:
        session.add(Categories(name=name))
        await session.commit()

async def add_item(data: dict, owner_id: int, owner_username: str = None):
    async with async_session() as session:
        item = Item(
            title=data['title'],
            description=data['description'],
            size=data.get('size'),
            brand=data.get('brand'),
            price=float(data['price']),
            category_id=int(data['category_id']),
            photo=data.get('photo'),
            owner_id=owner_id,
            owner_username=owner_username,
            source="bot"
        )
        session.add(item)
        await session.commit()

async def get_users_items(owner_id: int):
    async with async_session() as session:
        result = await session.scalars(select(Item).where(Item.owner_id == owner_id))
        return result.all()

async def delete_item(item_id: int):
    async with async_session() as session:
        await session.execute(delete(Item).where(Item.id == item_id))
        await session.commit()

async def get_brands_by_category(category_id: int):
    async with async_session() as session:
        result = await session.scalars(
            select(Item.brand)
            .where(Item.category_id == category_id, Item.brand.isnot(None))
            .distinct()
        )
        return result.all()

async def get_items_by_category_and_brand(category_id: int, brand: str):
    async with async_session() as session:
        result = await session.scalars(
            select(Item).where(Item.category_id == category_id, Item.brand == brand)
        )
        return result.all()

async def get_user(tg_id: int):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))

async def update_user_profile(tg_id, country, city, full_name, phone):
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(
                country=country,
                city=city,
                full_name=full_name,
                phone=phone
            )
        )
        await session.commit()

async def get_all_users_items():
    async with async_session() as session:
        result = await session.execute(select(Item))
        return result.scalars().all()


async def get_watermark_setting() -> bool:
    async with async_session() as session:
        result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        settings = result.scalar_one_or_none()
        
        # Если запись найдена и watermark_enabled == True (или 1)
        if settings and settings.watermark_enabled:
            return True
        return False


# --- ФУНКЦИИ ДЛЯ СНАЙПЕРА ---


async def add_sniper_filter(user_id: int, url: str, brand=None, size=None, price=None):
    async with async_session() as session:
        sniper_filter = SniperFilter(
            user_id = user_id,
            url = url,
            brand = brand,
            size = size,
            price = price
        )
        session.add(sniper_filter)
        await session.commit()


async def get_user_sniper_filters(user_id: int):
    async with async_session() as session:
        result = await session.scalars(select(SniperFilter).where(SniperFilter.user_id == user_id))
        return result.all()


async def delete_sniper_filters(filter_id: int):
    async with async_session() as session:
        await session.execute(delete(SniperFilter).where(SniperFilter.id == filter_id))
        await session.commit()


async def get_sniper_filter_setting() -> bool:
    async with async_session() as session:
        result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        settings = result.scalar_one_or_none()
        
        if settings is None:
            return False  
            
        return bool(settings.sniper_enabled)


async def give_vip_status(tg_id: int, days: int):
    async with async_session() as session:
        until_date = datetime.now() + timedelta(days=days)

        await session.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(
                is_vip=True,
                vip_until=until_date
            )
        )
        await session.commit()






async def create_support_ticket(user_tg_id: int, text: str, file_id: int):
    async with async_session() as session:

        new_ticket = SupportTicket(
            user_id=user_tg_id,
            message_text=text,  
            file_id=file_id
        )

        session.add(new_ticket)
        await session.commit()
        await session.refresh(new_ticket)
        return new_ticket.id




async def get_ticket_by_id(ticket_id:int):
    async with async_session() as session:
        result = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        return result.scalar_one_or_none()


async def close_ticket(ticket_id: int):
    async with async_session() as session:
        ticket = await session.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id))

        if ticket:
            ticket.status = "resolved"
            await session.commit()



async def toggle_favorite(user_id: int, item_id: int):
    async with async_session() as session:

       user_id = user_id
       item_id = item_id
       
       favorite = await session.scalar(
           select(Favorite).where(
               Favorite.user_tg_id == user_id,
               Favorite.item_id == item_id
           )
       )

       if favorite:
           await session.delete(favorite)
           await session.commit()
           return False

       else:
           new_fav = Favorite(user_tg_id=user_id, item_id=item_id)
           session.add(new_fav)
           await session.commit()
           return True


async def get_user_favorites(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Item)
            .join(Favorite, Favorite.item_id == Item.id)
            .where(Favorite.user_tg_id == user_id)
        )
        return result.scalars().all()


async def get_users_who_favorited(item_id: int):
    async with async_session() as session:
        result = await session.execute(select(Favorite).where(Favorite.item_tg_id == item_id))
        return result.scalars().all()



async def notify_price_drop(bot: Bot, item_id: int, item_title: str, old_price: float, new_price: float):

    if new_price >= old_price:
        return


    favorite_records = await get_users_who_favorited(item_id)

    if not favorite_records:
        return

    discount = int(old_price - new_price)

    text= (
        f"🔥 <b>Снижение цены на товар из Избранного!</b>\n\n"
        f"🏷 <b>{item_title}</b>\n"
        f"💰 Старая цена: <s>{int(old_price)} грн</s>\n"
        f"💥 Новая цена: <b>{int(new_price)} грн</b> (дешевле на {discount} грн!)"
    )

    for favorite in favorite_records:
        try:
            await bot.send_message(
                chat_id=favorite.user_id,
                text=text,
                parse_mode="HTML"
            )
        except Exception:
            pass


async def get_active_sniper_filters():
    async with async_session() as session:
        result = await session.scalars(select(SniperFilter).where(SniperFilter.is_active == True))
        return result.all()

async def update_sniper_last_id(filter_id: int, new_id: int):
    async with async_session() as session:
        filter = await session.scalar(select(SniperFilter).where(SniperFilter.id == filter_id))

        if filter:
            filter.last_item_id = str(new_id)
            await session.commit()


async def add_sniper_filter(session: AsyncSession, user_id: int, url: str):
    new_filter = SniperFilter(
        user_id=user_id,
        url=url,
        is_active=True
    )
    session.add(new_filter)
    await session.commit()


async def save_found_item(user_id: int, title: str, price: str, url: str, photo: str = None):
    async with async_session() as session:
        item = FoundItem(
            user_id=user_id,
            title=title,
            price=price,
            url=url,
            photo=photo
        )
        session.add(item)
        await session.commit()



async def get_user_found_items(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(FoundItem).where(FoundItem.user_id == user_id).order_by(FoundItem.created_at.desc())
        )
        return result.scalars().all()

async def clear_user_found_items(user_id: int):
    async with async_session() as session:
        await session.execute(
            delete(FoundItem).where(FoundItem.user_id == user_id)
        )
        await session.commit()


async def delete_found_item_by_id(item_id: int, user_id: int):
    async with async_session() as session:
        await session.execute(
            delete(FoundItem).where(FoundItem.id == item_id, FoundItem.user_id == user_id)
        )
        await session.commit()



async def add_user_sniper_filter(user_id: int, url: str):
    async with async_session() as session:
        usf = SniperFilter(user_id=user_id, url=url, is_active=1)
        session.add(usf)
        await session.commit()


async def get_user_sniper_filter(user_id: int):
    async with async_session() as session:
        result = await session.scalars(select(SniperFilter).where(SniperFilter.user_id == user_id, SniperFilter.is_active == 1))
        return result.all()


async def delete_user_sniper_filter(filter_id: int, user_id: int):
    async with async_session() as session:
        await session.execute(delete(SniperFilter).where(SniperFilter.id == filter_id, SniperFilter.user_id==user_id))
        await session.commit()



async def issue_strike(target_tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == target_tg_id))
        if not user:
            return None
        user.strikes += 1 
        if user.strikes >= 3:
            user.is_banned = True
        await session.commit()
        return user.strikes, user.is_banned


async def check_scam_credentials(phone: str, card_number: str):
    async with async_session() as session:

        conditions = []
        if phone:
            conditions.append(User.phone == phone)
        if card_number:
            conditions.append(User.card_number == card_number)
        
        if not conditions:
            return False

        scammer = await session.scalar(
    select(User).where(
        User.is_banned == True,
        or_(*conditions)
    )
)

        return scammer is not None



async def add_review(seller_id: int, buyer_id: int, rating: int, comment: str | None = None):
    async with async_session() as session:
     
     new_rating = Rating(
        seller_id=seller_id,
        buyer_id=buyer_id,
        rating=rating,
        comment=comment
    )
     session.add(new_rating)
     await session.commit()


async def get_seller_rating(seller_id: int):
    async with async_session() as session:
       stmt = select(func.avg(Rating.rating), func.count(Rating.id)).where(Rating.seller_id == seller_id)

       result = await session.execute(stmt)

       avg_rating, count = result.first()
       return round(avg_rating or 0.0, 1), count or 0


async def check_is_scam(user_id: int):
    async with async_session() as session:
        res = await session.scalar(select(User.is_scam).where(User.tg_id == user_id))

        return res if res is not None else False



async def add_wtb_item(user_id: int, user_username: str | None, title: str, size: str | None, budget: float):
    async with async_session() as session:
        wishlist = WTBItem(
            user_id=user_id,
            user_username=user_username,
            title=title,
            size=size,
            budget=budget
        )

        session.add(wishlist)
        await session.commit()

async def get_wtb_items():
    async with async_session() as session:
        result = await session.scalars(select(WTBItem).order_by(WTBItem.id.desc()))

        return result.all()



async def delete_wtb_item(wtb_id: int, user_id: int):
    async with async_session() as session:
        await session.execute(delete(WTBItem).where(WTBItem.id == wtb_id, WTBItem.user_id == user_id))
        await session.commit()