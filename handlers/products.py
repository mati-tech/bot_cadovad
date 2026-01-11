# from aiogram import Router, F
# from aiogram.types import Message
# from database import SessionLocal
# from models import Product
# from keyboards import product_actions
# from states import ProductState 
# from aiogram.fsm.context import FSMContext 
# from models import User 

# router = Router()

# @router.message(F.text == "📦 All Products")
# async def list_products(message: Message):
#     with SessionLocal() as session:  # sync session
#         result = session.execute(Product.__table__.select())
#         products = result.fetchall()  # sync fetchall

#     if not products:
#         await message.answer("No products found.")
#         return

#     for p in products:
#         await message.answer(
#             f"ID: {p.id}\n"
#             f"Name: {p.name}\n"
#             f"Quantity: {p.quantity}\n"
#             f"Price: {p.price}\n"
#             f"Size: {p.size_cm} cm\n"
#             f"Color: {p.color}\n"
#             f"Material: {p.material}",
#             reply_markup=product_actions(p.id)
#         )

# @router.message(F.text == "➕ Add New Product")
# async def add_product(message: Message, state: FSMContext):
#     await state.set_state(ProductState.name)
#     await message.answer("Enter product name:")

# @router.message(ProductState.name)
# async def product_name(message: Message, state: FSMContext):
#     await state.update_data(name=message.text)
#     await state.set_state(ProductState.quantity)
#     await message.answer("Enter quantity:")

# @router.message(ProductState.quantity)
# async def product_quantity(message: Message, state: FSMContext):
#     await state.update_data(quantity=int(message.text))
#     await state.set_state(ProductState.price)
#     await message.answer("Enter price:")

# @router.message(ProductState.price)
# async def product_price(message: Message, state: FSMContext):
#     await state.update_data(price=float(message.text))
#     await state.set_state(ProductState.size)
#     await message.answer("Enter size (cm):")

# @router.message(ProductState.size)
# async def product_size(message: Message, state: FSMContext):
#     await state.update_data(size=message.text)
#     await state.set_state(ProductState.color)
#     await message.answer("Enter color:")

# @router.message(ProductState.color)
# async def product_color(message: Message, state: FSMContext):
#     await state.update_data(color=message.text)
#     await state.set_state(ProductState.material)
#     await message.answer("Enter material:")

# @router.message(ProductState.material)
# async def product_material(message: Message, state: FSMContext):
#     data = await state.get_data()

#     # Get user shop_id
#     with SessionLocal() as session:
#         user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
#         product = Product(
#             shop_id=user.shop_id,
#             name=data["name"],
#             quantity=data["quantity"],
#             price=data["price"],
#             size_cm=data["size"],
#             color=data["color"],
#             material=data["material"]
#         )
#         session.add(product)
#         session.commit()

#     await message.answer("Product added successfully ✅", reply_markup=main_menu)
#     await state.clear()


from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Product, User, Shop
from keyboards import main_menu, product_actions
from states import ProductState

router = Router()

# List products handler (unchanged)
@router.message(F.text == "📦 All Products")
async def list_products(message: Message):
    with SessionLocal() as session:
        result = session.execute(Product.__table__.select())
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
            f"Size: {p.size_cm} cm\n"
            f"Color: {p.color}\n"
            f"Material: {p.material}",
            reply_markup=product_actions(p.id)
        )

# Start adding product - UPDATED with shop selection
@router.message(F.text == "➕ Add New Product")
async def add_product(message: Message, state: FSMContext):
    with SessionLocal() as session:
        # Get user
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            await message.answer("❌ User not found. Please run /start first.")
            return
        
        # Get user's shops
        shops = session.query(Shop).filter_by(owner_id=user.id).all()
        
        if not shops:
            await message.answer("❌ No shops found. Please create a shop first.")
            return
        
        if len(shops) == 1:
            # If only one shop, automatically select it
            await state.update_data(shop_id=shops[0].id)
            await state.set_state(ProductState.name)
            await message.answer(
                f"Adding product to Shop #{shops[0].shop_number} ({shops[0].location})\n"
                f"Enter product name:"
            )
            return
        
        # Create shop selection keyboard
        shop_buttons = []
        for shop in shops:
            shop_buttons.append([
                KeyboardButton(text=f"Shop #{shop.shop_number} - {shop.location}")
            ])
        
        # Add cancel button
        shop_buttons.append([KeyboardButton(text="❌ Cancel")])
        
        shop_keyboard = ReplyKeyboardMarkup(
            keyboard=shop_buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        # Store shop data in state for mapping
        shop_data = {f"Shop #{shop.shop_number} - {shop.location}": shop.id for shop in shops}
        await state.update_data(shops=shop_data)
        await state.set_state("waiting_for_shop_selection")
        
        await message.answer(
            "🏪 Select a shop to add product to:",
            reply_markup=shop_keyboard
        )

# Shop selection handler - NEW
@router.message(F.text.startswith("Shop #"))
async def select_shop(message: Message, state: FSMContext):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("❌ Product addition cancelled.", reply_markup=main_menu)
        return
    
    # Get shop mapping from state
    data = await state.get_data()
    shops = data.get("shops", {})
    
    shop_id = shops.get(message.text)
    
    if not shop_id:
        await message.answer("❌ Invalid shop selection. Please try again.")
        return
    
    # Store selected shop_id
    await state.update_data(shop_id=shop_id)
    
    # Extract shop number from button text for user feedback
    shop_num = message.text.split("#")[1].split(" ")[0]
    
    await state.set_state(ProductState.name)
    await message.answer(
        f"✅ Selected Shop #{shop_num}\n"
        f"Enter product name:",
        reply_markup=None  # Remove keyboard
    )

# Cancel handler - NEW
@router.message(F.text == "❌ Cancel")
async def cancel_product_add(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Product addition cancelled.", reply_markup=main_menu)

# Product name handler
@router.message(ProductState.name)
async def product_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❌ Product name cannot be empty. Please enter product name:")
        return
    
    await state.update_data(name=name)
    await state.set_state(ProductState.quantity)
    await message.answer("Enter quantity:")

# Product quantity handler with validation
@router.message(ProductState.quantity)
async def product_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            await message.answer("❌ Quantity must be positive. Enter quantity:")
            return
        await state.update_data(quantity=quantity)
        await state.set_state(ProductState.price)
        await message.answer("Enter price:")
    except ValueError:
        await message.answer("❌ Please enter a valid number for quantity:")

# Product price handler with validation
@router.message(ProductState.price)
async def product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            await message.answer("❌ Price must be positive. Enter price:")
            return
        await state.update_data(price=price)
        await state.set_state(ProductState.size)
        await message.answer("Enter size (cm):")
    except ValueError:
        await message.answer("❌ Please enter a valid number for price:")

# Product size handler
@router.message(ProductState.size)
async def product_size(message: Message, state: FSMContext):
    size = message.text.strip()
    if not size:
        await message.answer("❌ Size cannot be empty. Enter size (cm):")
        return
    
    await state.update_data(size=size)
    await state.set_state(ProductState.color)
    await message.answer("Enter color:")

# Product color handler
@router.message(ProductState.color)
async def product_color(message: Message, state: FSMContext):
    color = message.text.strip()
    if not color:
        await message.answer("❌ Color cannot be empty. Enter color:")
        return
    
    await state.update_data(color=color)
    await state.set_state(ProductState.material)
    await message.answer("Enter material:")

# Product material handler & save - UPDATED
@router.message(ProductState.material)
async def product_material(message: Message, state: FSMContext):
    material = message.text.strip()
    if not material:
        await message.answer("❌ Material cannot be empty. Enter material:")
        return
    
    # Get all data from state
    data = await state.get_data()
    
    # Get shop_id from state (selected earlier)
    shop_id = data.get("shop_id")
    
    if not shop_id:
        await message.answer("❌ Shop not selected. Please start over.")
        await state.clear()
        return
    
    with SessionLocal() as session:
        try:
            # Verify shop exists
            shop = session.query(Shop).filter_by(id=shop_id).first()
            if not shop:
                await message.answer("❌ Shop not found. Please start over.")
                await state.clear()
                return
            
            # Create product
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
                f"✅ Product added successfully!\n"
                f"📦 Product: {product.name}\n"
                f"🏪 Shop: #{shop.shop_number}\n"
                f"📊 Quantity: {product.quantity}\n"
                f"💰 Price: ${product.price:.2f}",
                reply_markup=main_menu
            )
            
        except Exception as e:
            print(f"Error saving product: {e}")
            session.rollback()
            await message.answer("❌ Error saving product. Please try again.")
        finally:
            await state.clear()