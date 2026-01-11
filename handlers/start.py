from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Shop
from keyboards import main_menu

router = Router()

# FSM states
class StartStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_line = State()
    waiting_for_shop_number = State()
    waiting_for_language = State()

# Helper function for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Step 1: /start command - FIXED
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            # Create new user
            user = User(telegram_id=message.from_user.id)
            db.add(user)
            db.commit()  # Commit to get user.id
            db.refresh(user)  # Refresh to get the auto-generated id
        
        # Store user_id in state for later use
        await state.update_data(user_id=user.id)
        
    except Exception as e:
        print(f"Database error in /start: {e}")
        db.rollback()
    finally:
        db.close()
    
    await message.answer("👋 Welcome! Please enter your full name:", reply_markup=main_menu)
    await state.set_state(StartStates.waiting_for_name)

# Step 2: Get user name - FIXED
@router.message(StartStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    
    # Validate name is not empty
    if not name:
        await message.answer("❌ Name cannot be empty. Please enter your full name:")
        return
    
    await state.update_data(name=name)
    await message.answer("🏷️ Enter your shop line/location:")
    await state.set_state(StartStates.waiting_for_line)

# Step 3: Get shop line/location - FIXED
@router.message(StartStates.waiting_for_line)
async def get_line(message: Message, state: FSMContext):
    line = message.text.strip()
    
    if not line:
        await message.answer("❌ Location cannot be empty. Enter your shop line/location:")
        return
    
    await state.update_data(line=line)
    await message.answer("🔢 Enter your shop number:")
    await state.set_state(StartStates.waiting_for_shop_number)

# Step 4: Get shop number - FIXED
@router.message(StartStates.waiting_for_shop_number)
async def get_shop_number(message: Message, state: FSMContext):
    shop_number_text = message.text.strip()
    
    # Validate it's a number
    try:
        shop_number = int(shop_number_text)
        if shop_number <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Please enter a valid positive number for shop number:")
        return
    
    await state.update_data(shop_number=shop_number)
    
    # Language selection buttons
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="English (en)"), KeyboardButton(text="Русский (ru)")],
            [KeyboardButton(text="فارسی (fa)"), KeyboardButton(text="پښتو (ps)")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer("🌐 Choose your language:", reply_markup=keyboard)
    await state.set_state(StartStates.waiting_for_language)

# Step 5: Get language and save user + create shop - FIXED
@router.message(StartStates.waiting_for_language)
async def get_language(message: Message, state: FSMContext):
    lang_text = message.text.strip().lower()
    lang_mapping = {
        "english (en)": "en",
        "english": "en",
        "en": "en",
        "русский (ru)": "ru",
        "русский": "ru",
        "ru": "ru",
        "فارسی (fa)": "fa",
        "فارسی": "fa",
        "fa": "fa",
        "پښتو (ps)": "ps",
        "پښتو": "ps",
        "ps": "ps"
    }
    
    if lang_text not in lang_mapping:
        await message.answer("❌ Invalid language. Please choose from buttons:\nEnglish (en), Русский (ru), فارسی (fa), پښتو (ps)")
        return
    
    lang = lang_mapping[lang_text]
    
    # Get all data from state
    data = await state.get_data()
    user_id = data.get("user_id")
    name = data.get("name", "").strip()
    line = data.get("line", "").strip()
    shop_number = data.get("shop_number")
    
    # Validate required data
    if not all([user_id, name, line, shop_number]):
        await message.answer("❌ Missing information. Please start over with /start")
        await state.clear()
        return
    
    db = SessionLocal()
    try:
        # Get user from database
        user = db.query(User).filter_by(id=user_id).first()
        
        if not user:
            # User doesn't exist, create new one
            user = User(
                telegram_id=message.from_user.id,
                name=name,
                location=line,
                language=lang
            )
            db.add(user)
        else:
            # Update existing user
            user.name = name
            user.location = line
            user.language = lang
        
        db.commit()  # Save user changes
        db.refresh(user)  # Refresh to get updated object
        
        # Check if shop already exists for this user
        existing_shop = db.query(Shop).filter_by(owner_id=user.id).first()
        
        if existing_shop:
            # Update existing shop
            existing_shop.shop_number = shop_number
            existing_shop.location = line
            shop = existing_shop
        else:
            # Create new shop
            shop = Shop(
                shop_number=shop_number,
                location=line,
                owner_id=user.id
            )
            db.add(shop)
        
        db.commit()  # Save shop changes
        
        await message.answer(
            f"✅ Account setup complete!\n"
            f"👤 User: {user.name}\n"
            f"📍 Location: {user.location}\n"
            f"🏪 Shop #{shop.shop_number} created!\n"
            f"🌐 Language: {user.language}",
            reply_markup=main_menu
        )
        
        # Debug info (optional)
        print(f"Saved user: ID={user.id}, Name='{user.name}', Location='{user.location}', Lang='{user.language}'")
        print(f"Saved shop: ID={shop.id}, Shop#={shop.shop_number}, Location='{shop.location}'")
        
    except Exception as e:
        print(f"Database error in final step: {e}")
        db.rollback()
        await message.answer("❌ Error saving data. Please try again with /start")
    finally:
        db.close()
    
    await state.clear()