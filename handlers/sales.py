# from aiogram import Router, F
# from aiogram.types import Message, CallbackQuery
# from aiogram.fsm.context import FSMContext
# from database import SessionLocal
# from models import Product, Sale, Debt
# from keyboards import payment_type_kb, cash_card_kb
# from states import SaleState

# router = Router()

# @router.callback_query(F.data.startswith("sold:"))
# async def sold_product(callback: CallbackQuery, state: FSMContext):
#     product_id = int(callback.data.split(":")[1])
#     await state.update_data(product_id=product_id)
#     await callback.message.answer("Enter buyer name:")
#     await state.set_state(SaleState.buyer_name)
#     await callback.answer()

# @router.message(SaleState.buyer_name)
# async def buyer_name(message: Message, state: FSMContext):
#     await state.update_data(buyer=message.text)
#     await message.delete()
#     data = await state.get_data()
#     await message.answer(
#         "Payment status?",
#         reply_markup=payment_type_kb(data["product_id"])
#     )

# @router.callback_query(F.data.startswith("clear:"))
# async def money_clear(callback: CallbackQuery, state: FSMContext):
#     product_id = int(callback.data.split(":")[1])
#     data = await state.get_data()
#     async with SessionLocal() as session:
#         product = await session.get(Product, product_id)
#         sale = Sale(
#             product_id=product.id,
#             buyer_name=data["buyer"],
#             price=product.price,
#             is_cleared=True
#         )
#         session.add(sale)
#         product.status = "sold"
#         await session.commit()
#     await callback.message.answer(
#         "Payment type?",
#         reply_markup=cash_card_kb(sale.id)
#     )
#     await state.clear()
#     await callback.answer()

# @router.callback_query(F.data.startswith("borrow:"))
# async def borrowed(callback: CallbackQuery, state: FSMContext):
#     product_id = int(callback.data.split(":")[1])
#     data = await state.get_data()
#     async with SessionLocal() as session:
#         product = await session.get(Product, product_id)
#         sale = Sale(
#             product_id=product.id,
#             buyer_name=data["buyer"],
#             price=product.price,
#             is_cleared=False,
#             payment_type="borrowed"
#         )
#         session.add(sale)
#         debt = Debt(
#             sale_id=sale.id,
#             total_amount=product.price,
#             paid_amount=0,
#             is_settled=False
#         )
#         session.add(debt)
#         product.status = "borrowed"
#         await session.commit()
#     await callback.message.answer("Marked as borrowed.")
#     await state.clear()
#     await callback.answer()

# @router.callback_query(F.data.startswith(("cash:", "card:")))
# async def set_payment(callback: CallbackQuery):
#     sale_id = int(callback.data.split(":")[1])
#     pay_type = callback.data.split(":")[0]
#     async with SessionLocal() as session:
#         sale = await session.get(Sale, sale_id)
#         sale.payment_type = pay_type
#         await session.commit()
#     await callback.message.answer("Sale completed ✔")
#     await callback.answer()


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
    
    with SessionLocal() as session:
        # Check if product exists
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Product not found.")
            await callback.answer()
            return
        
        # Check if product is already sold/borrowed
        if product.status in ["sold", "borrowed"]:
            await callback.message.answer(f"❌ Product is already {product.status}.")
            await callback.answer()
            return
    
    await state.update_data(product_id=product_id)
    await callback.message.answer("Enter buyer name:")
    await state.set_state(SaleState.buyer_name)
    await callback.answer()

@router.message(SaleState.buyer_name)
async def buyer_name(message: Message, state: FSMContext):
    buyer = message.text.strip()
    if not buyer:
        await message.answer("❌ Buyer name cannot be empty. Enter buyer name:")
        return
    
    await state.update_data(buyer=buyer)
    
    # Get product info to show details
    data = await state.get_data()
    product_id = data.get("product_id")
    
    with SessionLocal() as session:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await message.answer("❌ Product not found. Please start over.")
            await state.clear()
            return
        
        await message.answer(
            f"🛍️ Selling: {product.name}\n"
            f"💰 Price: ${product.price:.2f}\n"
            f"👤 Buyer: {buyer}\n\n"
            f"Payment status?",
            reply_markup=payment_type_kb(product_id)
        )
    
    # Don't delete the message - it's not necessary

@router.callback_query(F.data.startswith("clear:"))
async def money_clear(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    with SessionLocal() as session:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Product not found.")
            await callback.answer()
            return
        
        # Create sale record
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=True,
            payment_type="pending"  # Will be updated later
        )
        session.add(sale)
        session.commit()  # Commit to get sale.id
        session.refresh(sale)
        
        # Update product status
        product.status = "sold"
        product.quantity -= 1  # Reduce quantity by 1
        
        session.commit()
    
    await callback.message.answer(
        f"✅ Paid: ${product.price:.2f}\n"
        f"👤 Buyer: {data['buyer']}\n"
        f"📦 Product: {product.name}\n\n"
        f"Payment type?",
        reply_markup=cash_card_kb(sale.id)
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("borrow:"))
async def borrowed(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    with SessionLocal() as session:
        # Get product
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Product not found.")
            await callback.answer()
            return
        
        # Create sale record (borrowed)
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=False,
            payment_type="borrowed"
        )
        session.add(sale)
        session.commit()  # Commit to get sale.id
        session.refresh(sale)
        
        # Create debt record
        debt = Debt(
            sale_id=sale.id,
            total_amount=product.price,
            paid_amount=0,
            is_settled=False
        )
        session.add(debt)
        
        # Update product status
        product.status = "borrowed"
        product.quantity -= 1  # Reduce quantity by 1
        
        session.commit()
    
    await callback.message.answer(
        f"📝 Marked as borrowed:\n"
        f"👤 Buyer: {data['buyer']}\n"
        f"📦 Product: {product.name}\n"
        f"💰 Amount: ${product.price:.2f}\n"
        f"💳 Debt recorded."
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith(("cash:", "card:")))
async def set_payment(callback: CallbackQuery):
    parts = callback.data.split(":")
    pay_type = parts[0]  # "cash" or "card"
    sale_id = int(parts[1])
    
    with SessionLocal() as session:
        # Get sale
        sale = session.query(Sale).filter_by(id=sale_id).first()
        if not sale:
            await callback.message.answer("❌ Sale record not found.")
            await callback.answer()
            return
        
        # Update payment type
        sale.payment_type = pay_type
        session.commit()
        
        # Get product info for confirmation
        product = session.query(Product).filter_by(id=sale.product_id).first()
        
        await callback.message.answer(
            f"✅ Sale completed!\n"
            f"📦 Product: {product.name if product else 'N/A'}\n"
            f"👤 Buyer: {sale.buyer_name}\n"
            f"💰 Amount: ${sale.price:.2f}\n"
            f"💳 Payment: {pay_type.upper()}\n"
            f"📅 Date: {sale.created_at.strftime('%Y-%m-%d %H:%M') if sale.sale_date else 'Now'}"
        )
    
    await callback.answer()