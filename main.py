# import asyncio
# from aiogram import Bot, Dispatcher
# from config import BOT_TOKEN
# from database import init_db
# from handlers import start, products, sales, debts, reports, settings

# async def main():
#     print("🔹 Initializing database...")
#     # Initialize database (sync)
#     init_db()  # <-- no await
#     print("✅ Database initialized.")

#     print("🔹 Starting bot...")
#     # Initialize bot
#     bot = Bot(token=BOT_TOKEN)
#     dp = Dispatcher()

#     # Register routers
#     dp.include_router(start.router)
#     dp.include_router(products.router)
#     dp.include_router(sales.router)
#     dp.include_router(debts.router)
#     dp.include_router(reports.router)
#     dp.include_router(settings.router)
    
#     print("✅ Handlers registered.")

#     # Start polling
#     print("🔹 Bot is now running. Press Ctrl+C to stop.")
#     await dp.start_polling(bot)

# if __name__ == "__main__":
#     asyncio.run(main())


#!----------------

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import start, products, sales, debts, reports, settings
import uvicorn

# Global variables to store bot instances
bot = None
dp = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager for FastAPI application.
    Handles startup and shutdown events.
    """
    global bot, dp
    
    print("🚀 Starting Bot System...")
    
    # Initialize database (sync)
    print("🔹 Initializing database...")
    init_db()
    print("✅ Database initialized.")
    
    # Initialize bot with default properties
    print("🔹 Initializing bot...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(start.router)
    dp.include_router(products.router)
    dp.include_router(sales.router)
    dp.include_router(debts.router)
    dp.include_router(reports.router)
    dp.include_router(settings.router)
    
    print("✅ Handlers registered.")
    
    # Start bot polling (non-blocking)
    print("🔹 Starting bot polling...")
    
    # Create a task for bot polling
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    print("✅ Bot is now running via FastAPI.")
    print("🌐 Web server is available at http://0.0.0.0:8000")
    
    yield  # Application runs here
    
    # Shutdown
    print("🛑 Stopping System...")
    
    # Stop bot polling
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    # Close bot session
    if bot:
        await bot.session.close()
    
    print("✅ System stopped.")

# Create FastAPI app with lifespan
api = FastAPI(
    title="QuickSell Bot API",
    description="Telegram Bot for Inventory & Sales Management",
    version="2.0.0",
    lifespan=lifespan
)

# Health check endpoints
@api.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Root endpoint for health checks."""
    return {
        "status": "running",
        "service": "QuickSell Telegram Bot",
        "version": "2.0.0"
    }

@api.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "initialized",
        "bot": "running" if bot else "stopped"
    }

@api.get("/stats")
async def get_stats():
    """Get bot statistics (placeholder - you can add real stats)."""
    return {
        "bot_status": "active",
        "service": "QuickSell Inventory Management",
        "features": [
            "Product Management",
            "Sales Tracking",
            "Debt Management",
            "Advanced Reporting",
            "Multi-Shop Support"
        ]
    }

# Webhook endpoint (optional - if you want to use webhooks instead of polling)
@api.post("/webhook")
async def webhook(update: dict):
    """
    Webhook endpoint for receiving Telegram updates.
    Note: You need to configure webhook with Telegram API.
    """
    telegram_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)
    return {"status": "ok"}

# Admin API endpoints (optional - for managing bot via REST API)
@api.get("/admin/status")
async def admin_status():
    """Admin endpoint to check bot status."""
    return {
        "bot_token_set": bool(BOT_TOKEN),
        "bot_instance": "initialized" if bot else "not initialized",
        "dispatcher": "initialized" if dp else "not initialized"
    }

if __name__ == "__main__":
    # Get port from environment variable (for Heroku/Render compatibility)
    port = int(os.environ.get("PORT", 8000))
    
    # Run FastAPI with uvicorn
    uvicorn.run(
        api,
        host="0.0.0.0",  # Listen on all interfaces
        port=port,
        reload=False,    # Set to True for development, False for production
        log_level="info"
    )