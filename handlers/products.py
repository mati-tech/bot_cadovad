from aiogram import Router, F
from aiogram.types import Message
from database import SessionLocal
from models import Product
from keyboards import product_actions

router = Router()

@router.message(F.text == "📦 All Products")
async def list_products(message: Message):
    async with SessionLocal() as session:
        result = await session.execute(Product.__table__.select())
        products = result.fetchall()
    if not products:
        await message.answer("No products found.")
        return
    for p in products:
        await message.answer(
            f"ID: {p.id}\n"
            f"Name: {p.name}\n"
            f"Quantity: {p.quantity}\n"
            f"Price: {p.price}\n"
            f"Size: {p.size} cm\n"
            f"Color: {p.color}\n"
            f"Material: {p.material}",
            reply_markup=product_actions(p.id)
        )
