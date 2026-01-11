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
        # Проверка существования товара
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Товар не найден.")
            await callback.answer()
            return
        
        # Проверка, не продан ли уже товар
        if product.status in ["sold", "borrowed"]:
            status_ru = "продан" if product.status == "sold" else "в долгу"
            await callback.message.answer(f"❌ Товар уже {status_ru}.")
            await callback.answer()
            return
    
    await state.update_data(product_id=product_id)
    await callback.message.answer("Введите имя покупателя:")
    await state.set_state(SaleState.buyer_name)
    await callback.answer()

@router.message(SaleState.buyer_name)
async def buyer_name(message: Message, state: FSMContext):
    buyer = message.text.strip()
    if not buyer:
        await message.answer("❌ Имя покупателя не может быть пустым. Введите имя:")
        return
    
    await state.update_data(buyer=buyer)
    
    data = await state.get_data()
    product_id = data.get("product_id")
    
    with SessionLocal() as session:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await message.answer("❌ Товар не найден. Пожалуйста, начните заново.")
            await state.clear()
            return
        
        await message.answer(
            f"🛍️ Продажа: {product.name}\n"
            f"💰 Цена: {product.price:.2f}\n"
            f"👤 Покупатель: {buyer}\n\n"
            f"Статус оплаты?",
            reply_markup=payment_type_kb(product_id)
        )

@router.callback_query(F.data.startswith("clear:"))
async def money_clear(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    with SessionLocal() as session:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Товар не найден.")
            await callback.answer()
            return
        
        # Создание записи о продаже
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=True,
            payment_type="pending"  # Будет обновлено позже
        )
        session.add(sale)
        session.commit()
        session.refresh(sale)
        
        # Обновление статуса товара
        product.status = "sold"
        product.quantity -= 1  # Уменьшаем количество на 1
        
        session.commit()
    
    await callback.message.answer(
        f"✅ Оплачено: {product.price:.2f}\n"
        f"👤 Покупатель: {data['buyer']}\n"
        f"📦 Товар: {product.name}\n\n"
        f"Тип оплаты?",
        reply_markup=cash_card_kb(sale.id)
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("borrow:"))
async def borrowed(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    
    with SessionLocal() as session:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            await callback.message.answer("❌ Товар не найден.")
            await callback.answer()
            return
        
        # Создание записи о продаже (в долг)
        sale = Sale(
            product_id=product.id,
            buyer_name=data["buyer"],
            price=product.price,
            is_cleared=False,
            payment_type="borrowed"
        )
        session.add(sale)
        session.commit()
        session.refresh(sale)
        
        # Создание записи о долге
        debt = Debt(
            sale_id=sale.id,
            total_amount=product.price,
            paid_amount=0,
            is_settled=False
        )
        session.add(debt)
        
        # Обновление статуса товара
        product.status = "borrowed"
        product.quantity -= 1
        
        session.commit()
    
    await callback.message.answer(
        f"📝 Отмечено как долг:\n"
        f"👤 Покупатель: {data['buyer']}\n"
        f"📦 Товар: {product.name}\n"
        f"💰 Сумма: {product.price:.2f}\n"
        f"💳 Долг зафиксирован."
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith(("cash:", "card:")))
async def set_payment(callback: CallbackQuery):
    parts = callback.data.split(":")
    pay_type = parts[0]  # "cash" или "card"
    sale_id = int(parts[1])
    
    pay_type_ru = "НАЛИЧНЫЕ" if pay_type == "cash" else "КАРТА"
    
    with SessionLocal() as session:
        sale = session.query(Sale).filter_by(id=sale_id).first()
        if not sale:
            await callback.message.answer("❌ Запись о продаже не найдена.")
            await callback.answer()
            return
        
        sale.payment_type = pay_type
        session.commit()
        
        product = session.query(Product).filter_by(id=sale.product_id).first()
        
        await callback.message.answer(
            f"✅ Продажа завершена!\n"
            f"📦 Товар: {product.name if product else 'Н/Д'}\n"
            f"👤 Покупатель: {sale.buyer_name}\n"
            f"💰 Сумма: {sale.price:.2f}\n"
            f"💳 Оплата: {pay_type_ru}\n"
            f"📅 Дата: {sale.created_at.strftime('%Y-%m-%d %H:%M') if sale.created_at else 'Сейчас'}"
        )
    
    await callback.answer()