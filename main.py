import asyncio
import logging
import os
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin import router as admin_router
from handlers.user import router as user_router
from handlers.sniper import router as sniper_router
from handlers.cards import router as cards_router

from support import router as support_router
from handlers.reviews import router as reviews_router
from handlers.calculator import router as calculator_router
from handlers.wtb import router as wtb_router
from handlers.legit_checker import router as legit_check_router
from handlers.evaluator_h import router as evaluator_h_router

from database.db import db_main, DbSessionMiddleware, async_session

from parser import start_sniper_worker
# 1. Импортируем наш VIP-воркер проверки цен
from services.price_checker import start_vip_price_checker

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Один универсальный мидлварь для сессии БД и автоматического бана
dp.update.middleware(DbSessionMiddleware(session_pool=async_session))

# Регистрируем роутеры
dp.include_router(admin_router)
dp.include_router(support_router)
dp.include_router(sniper_router)
dp.include_router(cards_router)
dp.include_router(reviews_router)
dp.include_router(calculator_router)
dp.include_router(wtb_router)
dp.include_router(legit_check_router)
dp.include_router(evaluator_h_router)
dp.include_router(user_router)


async def handle_healthcheck(request):
    return web.Response(text="Bot is active 24/7!")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    await start_health_server()
    logging.basicConfig(level=logging.INFO)
    await db_main()
    print("🚀 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 2. Запускаем фоновый снайпер (поиск новых лотов)
    asyncio.create_task(start_sniper_worker(bot))
    
    # 3. Запускаем фоновый отслеживатель скидок для VIP
    asyncio.create_task(start_vip_price_checker(bot, async_session))
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())