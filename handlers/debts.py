from aiogram import Router, F
from aiogram.types import Message
from database import SessionLocal
from models import Debt

router = Router()

@router.message(F.text == "🕒 Uncleared Products")
async def uncleared(message: Message):
    async with SessionLocal() as session:
        result = await session.execute(Debt.__table__.select().where(Debt.is_settled == False))
        debts = result.fetchall()
    if not debts:
        await message.answer("No uncleared products.")
        return
    for d in debts:
        await message.answer(
            f"Sale ID: {d.sale_id}\nOwed: {d.total_amount}\nPaid: {d.paid_amount}\nReply with payment amount for Sale ID {d.sale_id}"
        )

@router.message()
async def pay_debt(message: Message):
    try:
        amount = float(message.text)
    except ValueError:
        return
    async with SessionLocal() as session:
        result = await session.execute(Debt.__table__.select().where(Debt.is_settled == False))
        debt = result.first()
        if not debt:
            return
        debt = debt[0]
        debt.paid_amount += amount
        if debt.paid_amount >= debt.total_amount:
            debt.is_settled = True
        await session.commit()
    await message.delete()
    await message.answer("Payment updated ✔")
