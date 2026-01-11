from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardRemove
from sqlalchemy.orm import Session
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
    # Очищаем состояние на случай, если пользователь застрял в середине регистрации
    await state.clear()
    
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        
        if not user:
            user = User(telegram_id=message.from_user.id, language="ru")
            db.add(user)
            db.commit()
            db.refresh(user)
        
        await state.update_data(user_id=user.id)
        
    except Exception as e:
        print(f"Ошибка базы данных в /start: {e}")
        db.rollback()
    finally:
        db.close()
    
    # ИСПРАВЛЕНО: Убран reply_markup=main_menu, добавлен ReplyKeyboardRemove()
    # Это скрывает кнопки меню до завершения регистрации
    await message.answer(
        "👋 Добро пожаловать в бот управления магазином!\n\n"
        "Для начала работы необходимо пройти регистрацию.\n"
        "Пожалуйста, введите ваше полное имя:", 
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(StartStates.waiting_for_name)

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
    user_id = data.get("user_id")
    name = data.get("name")
    line = data.get("line")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
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
        
        # ТОЛЬКО ТУТ мы отправляем main_menu
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 Имя: {name}\n"
            f"🏪 Магазин №{shop_number}\n"
            f"📍 Расположение: {line}\n\n"
            f"Теперь вы можете использовать все функции бота.",
            reply_markup=main_menu
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
        await message.answer("❌ Ошибка при сохранении данных.")
    finally:
        db.close()
    
    await state.clear()