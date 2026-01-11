# from aiogram import Router
# from aiogram.filters import Command
# from aiogram.types import Message
# from database import SessionLocal
# from models import User
# from keyboards import main_menu

# router = Router()

# @router.message(Command("start"))
# async def start_handler(message: Message):
#     with SessionLocal() as session:
#         user = session.query(User).get(message.from_user.id)
#         if not user:
#             user = User(
#                 telegram_id=message.from_user.id,  # <-- use telegram_id
#                 name="",
#                 shop_id=None,   # optional
#                 location="",    # optional
#                 language="en"
#             )
#             session.add(user)
#             session.commit()

#     await message.answer("Welcome! Please enter your name:", reply_markup=main_menu)


from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import Message
from database import SessionLocal
from models import User, Shop
from keyboards import main_menu

router = Router()

# Define FSM states
class StartStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_line = State()
    waiting_for_shop_number = State()
    waiting_for_language = State()

# Step 1: /start command
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                name="",
                location="",
                language="en"
            )
            session.add(user)
            session.commit()

    await message.answer("👋 Welcome! Please enter your full name:", reply_markup=main_menu)
    await state.set_state(StartStates.waiting_for_name)

# Step 2: Get user name
@router.message(StartStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await message.answer("🏷️ Enter your shop line/location:")
    await state.set_state(StartStates.waiting_for_line)

# Step 3: Get shop line/location
@router.message(StartStates.waiting_for_line)
async def get_line(message: Message, state: FSMContext):
    line = message.text.strip()
    await state.update_data(line=line)
    await message.answer("🔢 Enter your shop number:")
    await state.set_state(StartStates.waiting_for_shop_number)

# Step 4: Get shop number
@router.message(StartStates.waiting_for_shop_number)
async def get_shop_number(message: Message, state: FSMContext):
    shop_number = message.text.strip()
    await state.update_data(shop_number=shop_number)

    # Create buttons for language selection
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

# Step 5: Get language
# @router.message(StartStates.waiting_for_language)
# async def get_language(message: Message, state: FSMContext):
#     lang = message.text.strip().lower()
#     if lang not in ["en", "ru", "fa", "ps"]:
#         await message.answer("❌ Invalid language. Choose one: en / ru / fa / ps")
#         return  # Stay in the same state

#     await state.update_data(language=lang)

#     # Save all info to DB
#     data = await state.get_data()
#     with SessionLocal() as session:
#         user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
#         if user:
#             user.name = data.get("name", "")
#             user.location = data.get("line", "")
#             user.shop_id = data.get("shop_number", None)  # optional, can be integer
#             user.language = data.get("language", "en")
#             session.commit()

#     await message.answer(f"✅ Account setup complete!\nWelcome, {data.get('name')}!", reply_markup=main_menu)
#     await state.clear()  # Clear FSM state


# Step 5: Get language and create the shop
@router.message(StartStates.waiting_for_language)
async def get_language(message: Message, state: FSMContext):
    lang_text = message.text.strip().lower()
    lang_mapping = {
        "english (en)": "en",
        "русский (ru)": "ru",
        "فارسی (fa)": "fa",
        "پښتو (ps)": "ps"
    }

    if lang_text not in lang_mapping:
        await message.answer("❌ Invalid language. Please choose from buttons.")
        return

    lang = lang_mapping[lang_text]
    await state.update_data(language=lang)

    # Save user and create shop
    data = await state.get_data()
    with SessionLocal() as session:
        # Get or create user
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                name=data.get("name", ""),
                location=data.get("line", ""),
                language=lang
            )
            session.add(user)
            session.commit()  # Commit to get user.id

        # Create the shop linked to this user
        shop = Shop(
            shop_number=int(data.get("shop_number")),
            location=data.get("line", ""),
            owner_id=user.id  # link shop to user
        )
        session.add(shop)
        session.commit()

    await message.answer(
        f"✅ Account setup complete!\nUser: {data.get('name')}\nShop #{data.get('shop_number')} created!",
        reply_markup=main_menu
    )
    await state.clear()
