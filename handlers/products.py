from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Product, User, Shop
from keyboards import main_menu, product_actions
from states import ProductState

router = Router()

# Список товаров (List products)
@router.message(F.text == "📦 Все товары")
async def list_products(message: Message):
    with SessionLocal() as session:
        result = session.execute(Product.__table__.select())
        products = result.fetchall()

    if not products:
        await message.answer("Товары не найдены.")
        return

    for p in products:
        await message.answer(
            f"ID: {p.id}\n"
            f"Название: {p.name}\n"
            f"Количество: {p.quantity}\n"
            f"Цена: {p.price}\n"
            f"Размер: {p.size_cm} см\n"
            f"Цвет: {p.color}\n"
            f"Материал: {p.material}",
            reply_markup=product_actions(p.id)
        )

# Начало добавления товара (Start adding product)
@router.message(F.text == "➕ Добавить товар")
async def add_product(message: Message, state: FSMContext):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("❌ Пользователь не найден. Пожалуйста, введите /start.")
            return
        
        shops = session.query(Shop).filter_by(owner_id=user.id).all()
        
        if not shops:
            await message.answer("❌ Магазины не найдены. Сначала создайте магазин.")
            return
        
        if len(shops) == 1:
            await state.update_data(shop_id=shops[0].id)
            await state.set_state(ProductState.name)
            await message.answer(
                f"Добавление товара в Магазин №{shops[0].shop_number} ({shops[0].location})\n"
                f"Введите название товара:"
            )
            return
        
        shop_buttons = []
        for shop in shops:
            shop_buttons.append([
                KeyboardButton(text=f"Магазин №{shop.shop_number} - {shop.location}")
            ])
        
        shop_buttons.append([KeyboardButton(text="❌ Отмена")])
        
        shop_keyboard = ReplyKeyboardMarkup(
            keyboard=shop_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        shop_data = {f"Магазин №{shop.shop_number} - {shop.location}": shop.id for shop in shops}
        await state.update_data(shops=shop_data)
        await state.set_state("waiting_for_shop_selection")
        
        await message.answer(
            "🏪 Выберите магазин для добавления товара:",
            reply_markup=shop_keyboard
        )

# Выбор магазина (Shop selection)
@router.message(F.text.startswith("Магазин №"))
async def select_shop(message: Message, state: FSMContext):
    data = await state.get_data()
    shops = data.get("shops", {})
    
    shop_id = shops.get(message.text)
    
    if not shop_id:
        await message.answer("❌ Неверный выбор магазина. Попробуйте снова.")
        return
    
    await state.update_data(shop_id=shop_id)
    
    # Извлечение номера магазина для сообщения
    shop_num = message.text.split("№")[1].split(" ")[0]
    
    await state.set_state(ProductState.name)
    await message.answer(
        f"✅ Выбран Магазин №{shop_num}\n"
        f"Введите название товара:",
        reply_markup=None
    )

# Обработчик отмены (Cancel handler)
@router.message(F.text == "❌ Отмена")
async def cancel_product_add(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Добавление товара отменено.", reply_markup=main_menu)

# Название товара
@router.message(ProductState.name)
async def product_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❌ Название не может быть пустым. Введите название товара:")
        return
    
    await state.update_data(name=name)
    await state.set_state(ProductState.quantity)
    await message.answer("Введите количество:")

# Количество
@router.message(ProductState.quantity)
async def product_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            await message.answer("❌ Количество должно быть положительным числом. Введите количество:")
            return
        await state.update_data(quantity=quantity)
        await state.set_state(ProductState.price)
        await message.answer("Введите цену:")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число для количества:")

# Цена
@router.message(ProductState.price)
async def product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(',', '.')) # Support both . and ,
        if price <= 0:
            await message.answer("❌ Цена должна быть положительной. Введите цену:")
            return
        await state.update_data(price=price)
        await state.set_state(ProductState.size)
        await message.answer("Введите размер (см):")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число для цены:")

# Размер
@router.message(ProductState.size)
async def product_size(message: Message, state: FSMContext):
    size = message.text.strip()
    if not size:
        await message.answer("❌ Размер не может быть пустым. Введите размер (см):")
        return
    
    await state.update_data(size=size)
    await state.set_state(ProductState.color)
    await message.answer("Введите цвет:")

# Цвет
@router.message(ProductState.color)
async def product_color(message: Message, state: FSMContext):
    color = message.text.strip()
    if not color:
        await message.answer("❌ Цвет не может быть пустым. Введите цвет:")
        return
    
    await state.update_data(color=color)
    await state.set_state(ProductState.material)
    await message.answer("Введите материал:")

# Материал и сохранение
@router.message(ProductState.material)
async def product_material(message: Message, state: FSMContext):
    material = message.text.strip()
    if not material:
        await message.answer("❌ Материал не может быть пустым. Введите материал:")
        return
    
    data = await state.get_data()
    shop_id = data.get("shop_id")
    
    if not shop_id:
        await message.answer("❌ Магазин не выбран. Начните сначала.")
        await state.clear()
        return
    
    with SessionLocal() as session:
        try:
            shop = session.query(Shop).filter_by(id=shop_id).first()
            if not shop:
                await message.answer("❌ Магазин не найден. Начните сначала.")
                await state.clear()
                return
            
            product = Product(
                shop_id=shop_id,
                name=data["name"],
                quantity=data["quantity"],
                price=data["price"],
                size_cm=data["size"],
                color=data["color"],
                material=material
            )
            
            session.add(product)
            session.commit()
            session.refresh(product)
            
            await message.answer(
                f"✅ Товар успешно добавлен!\n"
                f"📦 Товар: {product.name}\n"
                f"🏪 Магазин: №{shop.shop_number}\n"
                f"📊 Количество: {product.quantity}\n"
                f"💰 Цена: {product.price:.2f}",
                reply_markup=main_menu
            )
            
        except Exception as e:
            print(f"Error saving product: {e}")
            session.rollback()
            await message.answer("❌ Ошибка при сохранении товара. Попробуйте еще раз.")
        finally:
            await state.clear()