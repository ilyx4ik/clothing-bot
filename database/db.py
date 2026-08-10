from typing import Callable, Awaitable, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import User, Base
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3", echo=True)
async_session = async_sessionmaker(engine)

async def db_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        event_user = data.get("event_from_user")

        if not event_user and hasattr(event, "from_user"):
            event_user = event.from_user
        elif not event_user and hasattr(event, "message") and event.message:
            event_user = event.message.from_user

        async with self.session_pool() as session:
            data["session"] = session

            if event_user:
                result = await session.execute(
                    select(User.is_banned).where(User.tg_id == event_user.id)
                )
                is_banned = result.scalar_one_or_none()

                if is_banned:
                    actual_event = getattr(event, "message", None) or getattr(event, "callback_query", None) or event

                    if isinstance(actual_event, Message):
                        await actual_event.answer("⛔ Вы заблокированы и не можете использовать бота.")
                    elif isinstance(actual_event, CallbackQuery):
                        await actual_event.answer("⛔ Вы заблокированы.", show_alert=True)
                    
                    return  

            return await handler(event, data)