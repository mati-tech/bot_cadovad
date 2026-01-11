import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db
from handlers import start, products, sales, debts, reports, settings

async def main():
    print("🔹 Initializing database...")
    # Initialize database (sync)
    init_db()  # <-- no await
    print("✅ Database initialized.")

    print("🔹 Starting bot...")
    # Initialize bot
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)
    dp.include_router(products.router)
    dp.include_router(sales.router)
    dp.include_router(debts.router)
    dp.include_router(reports.router)
    dp.include_router(settings.router)
    
    print("✅ Handlers registered.")

    # Start polling
    print("🔹 Bot is now running. Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
