from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models import User, Shop, Payment
from datetime import datetime, timedelta
import asyncio

router = Router()

# Состояния
class SettingsState(StatesGroup):
    waiting_for_language = State()
    waiting_for_support_message = State()
    waiting_for_payment_period = State()

# Главное меню настроек
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="settings_profile")],
            [InlineKeyboardButton(text="💳 Статус оплаты", callback_data="settings_payment")],
            [InlineKeyboardButton(text="📱 Поддержка", callback_data="settings_support")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="settings_about")]
        ]
    )
    
    await message.answer(
        "⚙️ Меню настроек\n"
        "Выберите опцию:",
        reply_markup=keyboard
    )

# Информация о профиле
@router.callback_query(F.data == "settings_profile")
async def show_profile(callback: CallbackQuery):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user:
            await callback.message.answer("❌ Пользователь не найден. Пожалуйста, сначала запустите /start")
            await callback.answer()
            return
        
        # Получаем магазины пользователя
        shops = session.query(Shop).filter_by(owner_id=user.id).all()
        
        profile_text = (
            f"👤 Ваш профиль\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📛 Имя: {user.name or 'Не установлено'}\n"
            f"🆔 Telegram ID: {user.telegram_id}\n"
            f"🌐 Язык: {user.language.upper() if user.language else 'Не установлен'}\n"
            f"📍 Местоположение: {user.location or 'Не установлено'}\n"
            f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Н/Д'}\n\n"
        )
        
        if shops:
            profile_text += f"🏪 Ваши магазины ({len(shops)}):\n"
            for shop in shops:
                # Получаем статистику магазина
                from models import Product, Sale
                products_count = session.query(Product).filter_by(shop_id=shop.id).count()
                sales_count = session.query(Sale).filter(
                    Sale.product_id.in_(
                        session.query(Product.id).filter_by(shop_id=shop.id)
                    )
                ).count()
                
                profile_text += (
                    f"• Магазин №{shop.shop_number} - {shop.location}\n"
                    f"  📦 Товаров: {products_count} | 🛒 Продаж: {sales_count}\n"
                )
        else:
            profile_text += "🏪 Магазины пока отсутствуют. Используйте /start чтобы создать магазин.\n"
        
        # Кнопка редактирования
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile")],
                [InlineKeyboardButton(text="🔙 Назад в настройки", callback_data="back_to_settings")]
            ]
        )
        
        await callback.message.answer(profile_text, reply_markup=keyboard)
        await callback.answer()

# Редактирование профиля (заглушка - можно расширить)
@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    await callback.message.answer(
        "✏️ Функция редактирования профиля скоро появится!\n"
        "Пока что вы можете запустить /start снова для обновления информации."
    )
    await callback.answer()

# Статус оплаты и подписка
@router.callback_query(F.data == "settings_payment")
async def payment_status(callback: CallbackQuery):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user:
            await callback.message.answer("❌ Пользователь не найден.")
            await callback.answer()
            return
        
        # Получаем последний платеж
        payment = session.query(Payment).filter_by(user_id=user.id).order_by(Payment.created_at.desc()).first()
        
        if payment and payment.expires_at > datetime.now():
            # Активная подписка
            days_left = (payment.expires_at - datetime.now()).days
            status_text = (
                f"💳 Статус оплаты: АКТИВНА ✅\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 Тариф: {payment.plan_type}\n"
                f"💰 Сумма: ${payment.amount:.2f}\n"
                f"📅 Начало: {payment.created_at.strftime('%d.%m.%Y')}\n"
                f"📅 Окончание: {payment.expires_at.strftime('%d.%m.%Y')}\n"
                f"⏳ Осталось дней: {days_left}\n\n"
                f"Ваша подписка активна. Вы можете продлить её досрочно ниже."
            )
        else:
            # Нет активной подписки
            status_text = (
                f"💳 Статус оплаты: НЕАКТИВНА ❌\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Ваша подписка истекла или вы ещё не подписались.\n"
                f"Пожалуйста, выберите тарифный план для продолжения использования всех функций."
            )
        
        # Клавиатура с тарифными планами
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 1 месяц - $9.99", callback_data="plan_1month")],
                [InlineKeyboardButton(text="💰 3 месяца - $24.99", callback_data="plan_3months")],
                [InlineKeyboardButton(text="💰 6 месяцев - $44.99", callback_data="plan_6months")],
                [InlineKeyboardButton(text="💰 1 год - $79.99", callback_data="plan_1year")],
                [
                    InlineKeyboardButton(text="📱 Связаться с админом", callback_data="contact_admin"),
                    InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")
                ]
            ]
        )
        
        await callback.message.answer(status_text, reply_markup=keyboard)
        await callback.answer()

# Обработка выбора тарифного плана
@router.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: CallbackQuery):
    plan_map = {
        "plan_1month": {"name": "1 месяц", "price": 9.99, "days": 30},
        "plan_3months": {"name": "3 месяца", "price": 24.99, "days": 90},
        "plan_6months": {"name": "6 месяцев", "price": 44.99, "days": 180},
        "plan_1year": {"name": "1 год", "price": 79.99, "days": 365}
    }
    
    plan_data = plan_map.get(callback.data)
    
    if not plan_data:
        await callback.message.answer("❌ Выбран неверный план.")
        await callback.answer()
        return
    
    # Демо - в реальном приложении здесь была бы переадресация на платежный шлюз
    await callback.message.answer(
        f"💰 **Подписка на {plan_data['name']}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 Цена: ${plan_data['price']:.2f}\n"
        f"📅 Длительность: {plan_data['days']} дней\n\n"
        f"⚠️ Требуется интеграция оплаты\n"
        f"Это демо-версия. В реальном приложении это бы перенаправило на:\n"
        f"• Оплату через Stripe / PayPal\n"
        f"• Реквизиты банковского перевода\n"
        f"• Криптовалютную оплату\n\n"
        f"Свяжитесь с администратором для ручной оплаты:\n"
        f"@admin_username"
    )
    
    # Симуляция оплаты (только для демо - удалите в продакшене)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сымитировать оплату (Демо)", callback_data=f"simulate_{callback.data}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="settings_payment")]
        ]
    )
    
    await callback.message.answer("Для тестирования вы можете сымитировать оплату:", reply_markup=keyboard)
    await callback.answer()

# Симуляция оплаты (ТОЛЬКО ДЛЯ ДЕМО - удалите в продакшене)
@router.callback_query(F.data.startswith("simulate_"))
async def simulate_payment(callback: CallbackQuery):
    plan_key = callback.data.replace("simulate_", "")
    plan_map = {
        "plan_1month": {"name": "1 месяц", "price": 9.99, "days": 30},
        "plan_3months": {"name": "3 месяца", "price": 24.99, "days": 90},
        "plan_6months": {"name": "6 месяцев", "price": 44.99, "days": 180},
        "plan_1year": {"name": "1 год", "price": 79.99, "days": 365}
    }
    
    plan_data = plan_map.get(plan_key)
    
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if user and plan_data:
            # Создаем запись об оплате
            expires_at = datetime.now() + timedelta(days=plan_data['days'])
            payment = Payment(
                user_id=user.id,
                amount=plan_data['price'],
                plan_type=plan_data['name'],
                status="completed",
                expires_at=expires_at
            )
            session.add(payment)
            session.commit()
            
            await callback.message.answer(
                f"✅ Оплата успешна!\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 Тариф: {plan_data['name']}\n"
                f"💰 Сумма: ${plan_data['price']:.2f}\n"
                f"📅 Действительно до: {expires_at.strftime('%d.%m.%Y')}\n\n"
                f"Спасибо за оплату! Все функции теперь разблокированы."
            )
        else:
            await callback.message.answer("❌ Ошибка обработки оплаты.")
    
    await callback.answer()

# Центр поддержки
@router.callback_query(F.data == "settings_support")
async def support_menu(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Отправить сообщение админу", callback_data="support_message")],
            [InlineKeyboardButton(text="📞 Контактная информация", callback_data="support_contact")],
            [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="support_faq")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(
        "📱 Центр поддержки\n"
        "Чем мы можем помочь?",
        reply_markup=keyboard
    )
    await callback.answer()

# Отправить сообщение администратору
@router.callback_query(F.data == "support_message")
async def start_support_message(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📝 Отправить сообщение администратору\n"
        "Пожалуйста, введите ваше сообщение (вопросы, отзывы, проблемы):\n\n"
        "Введите /cancel для отмены."
    )
    await state.set_state(SettingsState.waiting_for_support_message)
    await callback.answer()

# Обработка сообщения в поддержку
@router.message(SettingsState.waiting_for_support_message)
async def send_support_message(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await message.answer("❌ Сообщение отменено.")
        await state.clear()
        return
    
    # В реальном приложении вы бы:
    # 1. Сохранили в базу данных
    # 2. Уведомили администратора через Telegram
    # 3. Отправили подтверждение пользователю
    
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        user_name = user.name if user else "Неизвестный пользователь"
    
    # Симуляция отправки администратору (замените на реальное уведомление)
    admin_notification = (
        f"🆘 Новое сообщение в поддержку\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 От: {user_name} (ID: {message.from_user.id})\n"
        f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"💬 Сообщение:\n{message.text}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    # Для демо, показываем что было бы отправлено
    await message.answer(
        f"✅ Сообщение отправлено администратору!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Ваше сообщение было переслано команде администраторов.\n"
        f"Мы ответим в течение 24 часов.\n\n"
        f"📧 Ваше сообщение:\n"
        f"{message.text}\n\n"
        f"📧 Администратор получил бы:\n"
        f"{admin_notification[:500]}..."
    )
    
    await state.clear()

# Контактная информация
@router.callback_query(F.data == "support_contact")
async def contact_info(callback: CallbackQuery):
    contact_text = (
        "📞 Контактная информация\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👨‍💼 Администратор: @admin_username\n"
        "📧 Email: admin@example.com\n"
        "🌐 Сайт: https://example.com\n"
        "📱 Телефон: +1 (234) 567-8900\n\n"
        "⏰ Часы работы поддержки:\n"
        "Понедельник - Пятница: 9:00 - 18:00\n"
        "Суббота: 10:00 - 14:00\n"
        "Воскресенье: выходной\n\n"
        "📍 Вопросы и предложения присылайте напрямую администратору."
    )
    
    await callback.message.answer(contact_text)
    await callback.answer()

# Частые вопросы
@router.callback_query(F.data == "support_faq")
async def faq_section(callback: CallbackQuery):
    faq_text = (
        "❓ Часто задаваемые вопросы\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "❓ Как добавить товар?\n"
        "👉 Перейдите в Товары → Добавить новый товар\n\n"
        "❓ Как отметить продажу?\n"
        "👉 Нажмите на товар и выберите 'Отметить как проданный'\n\n"
        "❓ Можно ли использовать бота бесплатно?\n"
        "👉 Да, базовые функции бесплатны. Премиум функции требуют подписки.\n\n"
        "❓ Как изменить язык?\n"
        "👉 Настройки → Язык → Выберите ваш язык\n\n"
        "❓ Как связаться с поддержкой?\n"
        "👉 Настройки → Поддержка → Отправить сообщение администратору\n\n"
        "❓ Как проверить статус оплаты?\n"
        "👉 Настройки → Статус оплаты\n\n"
        "❓ Можно ли иметь несколько магазинов?\n"
        "👉 Да, запустите /start снова чтобы создать дополнительные магазины."
    )
    
    await callback.message.answer(faq_text)
    await callback.answer()

# Раздел "О боте"
@router.callback_query(F.data == "settings_about")
async def about_section(callback: CallbackQuery):
    with SessionLocal() as session:
        user_count = session.query(User).count()
        shop_count = session.query(Shop).count()
        from models import Product, Sale
        product_count = session.query(Product).count()
        sale_count = session.query(Sale).count()
    
    about_text = (
        "ℹ️ О боте QuickSell\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🚀 Версия: 2.0.0\n"
        "📅 Выпущен: 2024\n"
        "👨‍💻 Разработчик: Команда QuickSell\n\n"
        "📊 Статистика бота:\n"
        f"👥 Пользователей: {user_count}\n"
        f"🏪 Магазинов: {shop_count}\n"
        f"📦 Товаров: {product_count}\n"
        f"💰 Продаж: {sale_count}\n\n"
        "✨ Функции:\n"
        "• Управление товарами\n"
        "• Отслеживание продаж\n"
        "• Управление долгами\n"
        "• Расширенная отчетность\n"
        "• Поддержка нескольких языков\n"
        "• Несколько магазинов\n\n"
        "💖 Спасибо что используете QuickSell!"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оценить бота", url="https://t.me/yourbot")],
            [InlineKeyboardButton(text="📱 Поделиться с друзьями", url="https://t.me/share/url?url=Попробуйте бота QuickSell!")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(about_text, reply_markup=keyboard)
    await callback.answer()

# Навигация назад в настройки
@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    await settings_menu(callback.message)
    await callback.answer()

# Связаться с администратором из раздела оплаты
@router.callback_query(F.data == "contact_admin")
async def contact_admin_from_payment(callback: CallbackQuery):
    await callback.message.answer(
        "👨‍💼 Связаться с администратором по оплате\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "По вопросам оплаты или для ручной оплаты:\n\n"
        "📱 Telegram: @admin_username\n"
        "📧 Email: payments@example.com\n"
        "💬 WhatsApp: +1 (234) 567-8900\n\n"
        "Пожалуйста, предоставьте ваш User ID:\n"
        f"`{callback.from_user.id}`"
    )
    await callback.answer()