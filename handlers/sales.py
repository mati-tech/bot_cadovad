from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import SessionLocal
from models import Product, Sale, Debt
from keyboards import payment_type_kb, cash_card_kb
from states import SaleState

router = Router()

@router.callback_query(F.data.startswith("sold:"))
async def sold_product(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("Enter buyer name:")
    await state.set_state(SaleState.buyer_name)
    await callback.answer()

@router.message(SaleState.buyer_name)
async def buyer_name(message: Message, state: FSMContext):
    await state.update_data(buyer=message.text)
    await message.delete()
    data = await state.get_data()
    await message.answer(
        "Payment status?",
        reply_markup=payment_type_kb(data["product_id"])
    )

@router.callback_query(F.data.startswith("clear:"))
async def money_clear(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    async with SessionLocal() as session:
        product = await session.get(Product, product_id)
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=True
        )
        session.add(sale)
        product.status = "sold"
        await session.commit()
    await callback.message.answer(
        "Payment type?",
        reply_markup=cash_card_kb(sale.id)
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("borrow:"))
async def borrowed(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    async with SessionLocal() as session:
        product = await session.get(Product, product_id)
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=False,
            payment_type="borrowed"
        )
        session.add(sale)
        debt = Debt(
            sale_id=sale.id,
            total_amount=product.price,
            paid_amount=0,
            is_settled=False
        )
        session.add(debt)
        product.status = "borrowed"
        await session.commit()
    await callback.message.answer("Marked as borrowed.")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith(("cash:", "card:")))
async def set_payment(callback: CallbackQuery):
    sale_id = int(callback.data.split(":")[1])
    pay_type = callback.data.split(":")[0]
    async with SessionLocal() as session:
        sale = await session.get(Sale, sale_id)
        sale.payment_type = pay_type
        await session.commit()
    await callback.message.answer("Sale completed ✔")
    await callback.answer()
