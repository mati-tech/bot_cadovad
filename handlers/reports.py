from aiogram import Router, F
from aiogram.types import Message
from database import SessionLocal
from models import Sale
from datetime import datetime, timedelta

router = Router()

@router.message(F.text == "📊 Sold Items")
async def sold_items(message: Message):
    today = datetime.utcnow() - timedelta(days=1)
    async with SessionLocal() as session:
        result = await session.execute(Sale.__table__.select().where(Sale.created_at >= today))
        sales = result.fetchall()
    cleared = [s for s in sales if s.is_cleared]
    uncleared = [s for s in sales if not s.is_cleared]

    text = "✅ Cleared:\n"
    for s in cleared:
        text += f"{s.buyer_name} - {s.price}\n"
    text += "\n🕒 Uncleared:\n"
    for s in uncleared:
        text += f"{s.buyer_name} - {s.price}\n"

    await message.answer(text)
