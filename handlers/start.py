from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from database import SessionLocal
from models import User, Shop
from keyboards import main_menu

router = Router()

# FSM состояния
class StartStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_line = State()
    waiting_for_shop_number = State()

# Шаг 1: команда /start
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    db = SessionLocal()
    try:
        # Ищем пользователя по telegram_id
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        shop = db.query(Shop).filter_by(owner_id=user.id).first() if user else None

        # Если пользователь уже зарегистрирован и имеет магазин
        if user and user.name and shop:
            info_text = (
                "📋 **Ваш профиль:**\n"
                f"👤 Имя: {user.name}\n"
                f"📍 Расположение: {user.location}\n"
                f"🏪 Магазин №: {shop.shop_number}\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Вы можете управлять товарами через меню ниже или изменить данные профиля."
            )
            
            edit_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Редактировать профиль", callback_data="edit_profile")]
            ])
            
            # Показываем основное меню и карточку с кнопкой редактирования
            await message.answer(info_text, reply_markup=main_menu, parse_mode="Markdown")
            await message.answer("Хотите изменить данные?", reply_markup=edit_kb)
            return

        # Если новый пользователь или профиль не завершен
        await message.answer(
            "👋 Добро пожаловать! Вы еще не зарегистрированы.\n"
            "Пожалуйста, введите ваше полное имя:", 
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(StartStates.waiting_for_name)
        
    finally:
        db.close()

# Обработчик кнопки "Редактировать"
@router.callback_query(F.data == "edit_profile")
async def edit_profile_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔄 Начнем обновление данных.\nВведите ваше полное имя:", 
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(StartStates.waiting_for_name)
    await callback.answer()

# Шаг 2: Получаем имя пользователя
@router.message(StartStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❌ Имя не может быть пустым. Введите ваше имя:")
        return
    
    await state.update_data(name=name)
    await message.answer("🏷️ Теперь введите линию/расположение вашего магазина (например, 'Линия 5'):")
    await state.set_state(StartStates.waiting_for_line)

# Шаг 3: Получаем линию
@router.message(StartStates.waiting_for_line)
async def get_line(message: Message, state: FSMContext):
    line = message.text.strip()
    if not line:
        await message.answer("❌ Расположение не может быть пустым.")
        return
    
    await state.update_data(line=line)
    await message.answer("🔢 Введите номер вашего магазина (только число):")
    await state.set_state(StartStates.waiting_for_shop_number)

# Шаг 4: Финальный этап и открытие меню
@router.message(StartStates.waiting_for_shop_number)
async def get_shop_number(message: Message, state: FSMContext):
    shop_number_text = message.text.strip()
    
    try:
        shop_number = int(shop_number_text)
        if shop_number <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число для номера магазина:")
        return
    
    data = await state.get_data()
    name = data.get("name")
    line = data.get("line")
    
    db = SessionLocal()
    try:
        # Ищем пользователя по telegram_id (более надежно, чем по id из стейта)
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            user = User(telegram_id=message.from_user.id, language="ru")
            db.add(user)
            db.commit()
            db.refresh(user)

        user.name = name
        user.location = line
        db.commit()

        existing_shop = db.query(Shop).filter_by(owner_id=user.id).first()
        if existing_shop:
            existing_shop.shop_number = shop_number
            existing_shop.location = line
        else:
            new_shop = Shop(shop_number=shop_number, location=line, owner_id=user.id)
            db.add(new_shop)
        
        db.commit()
        
        await message.answer(
            f"✅ Данные успешно сохранены!\n\n"
            f"👤 Имя: {name}\n"
            f"🏪 Магазин №{shop_number}\n"
            f"📍 Расположение: {line}",
            reply_markup=main_menu
        )
        
    except Exception as e:
        print(f"Ошибка БД: {e}")
        db.rollback()
        await message.answer("❌ Ошибка при сохранении данных.")
    finally:
        db.close()
    
    await state.clear()