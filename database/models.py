from datetime import datetime
from sqlalchemy import BigInteger, Integer, ForeignKey, String, Float, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    is_admin: Mapped[int] = mapped_column(Integer, default=0)
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(25), nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    vip_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    strikes: Mapped[int] = mapped_column(Integer, default=0)
    card_number: Mapped[str] = mapped_column(String, nullable=True)
    is_scam: Mapped[bool] = mapped_column(Boolean, default=False)

class Categories(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

class Item(Base):
    __tablename__ = 'items'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    size: Mapped[str] = mapped_column(String, nullable=True)        
    price: Mapped[float] = mapped_column(Float)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    photo: Mapped[str] = mapped_column(String, nullable=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=True)

    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=True)    
    owner_username: Mapped[str] = mapped_column(String, nullable=True) 

    source: Mapped[str] = mapped_column(String, default="bot")

class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    user_name: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    address: Mapped[str] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now) 

class Basket(Base):
    __tablename__ = 'basket'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))

class InviteCode(Base):
    __tablename__ = 'invite_codes'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

class BotSettings(Base):
    __tablename__ = 'bot_settings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    watermark_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sniper_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Settings(Base):
    __tablename__ = 'settings'

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)

class SniperFilter(Base):
    __tablename__ = 'sniper_filter'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size: Mapped[str | None] = mapped_column(String, nullable=True)  
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)  
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_item_id: Mapped[str | None] = mapped_column(String, nullable=True)

class SupportTicket(Base):
    __tablename__ = 'support_ticket'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    message_text: Mapped[str] = mapped_column(String, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Favorite(Base):
    __tablename__ = 'favorite'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))  
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey('items.id'))

    __table_args__ = (
        UniqueConstraint('user_tg_id', 'item_id', name='unique_user_item'),
    )


class FoundItem(Base):
    __tablename__ = 'found_items'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  
    title: Mapped[str] = mapped_column(String(255))
    price: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Rating(Base):
    __tablename__ = 'ratings'

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WTBItem(Base):
    __tablename__ = 'wtbitem'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.tg_id'))
    user_username: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    size: Mapped[str | None] = mapped_column(String, nullable=True)
    budget: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())