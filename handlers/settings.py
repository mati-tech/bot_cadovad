from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models import User, Shop, Payment
from datetime import datetime, timedelta
import asyncio

router = Router()

# States
class SettingsState(StatesGroup):
    waiting_for_language = State()
    waiting_for_support_message = State()
    waiting_for_payment_period = State()

# Main settings menu
@router.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 My Profile", callback_data="settings_profile")],
            [InlineKeyboardButton(text="🌐 Language", callback_data="settings_language")],
            [InlineKeyboardButton(text="💳 Payment Status", callback_data="settings_payment")],
            [InlineKeyboardButton(text="📱 Support", callback_data="settings_support")],
            [InlineKeyboardButton(text="ℹ️ About", callback_data="settings_about")]
        ]
    )
    
    await message.answer(
        "⚙️ Settings Menu\n"
        "Select an option:",
        reply_markup=keyboard
    )

# Profile information
@router.callback_query(F.data == "settings_profile")
async def show_profile(callback: CallbackQuery):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user:
            await callback.message.answer("❌ User not found. Please run /start first.")
            await callback.answer()
            return
        
        # Get user's shops
        shops = session.query(Shop).filter_by(owner_id=user.id).all()
        
        profile_text = (
            f"👤 Your Profile\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📛 Name: {user.name or 'Not set'}\n"
            f"🆔 Telegram ID: {user.telegram_id}\n"
            f"🌐 Language: {user.language.upper() if user.language else 'Not set'}\n"
            f"📍 Location: {user.location or 'Not set'}\n"
            f"📅 Joined: {user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'}\n\n"
        )
        
        if shops:
            profile_text += f"🏪 Your Shops ({len(shops)}):\n"
            for shop in shops:
                # Get shop statistics
                from models import Product, Sale
                products_count = session.query(Product).filter_by(shop_id=shop.id).count()
                sales_count = session.query(Sale).filter(
                    Sale.product_id.in_(
                        session.query(Product.id).filter_by(shop_id=shop.id)
                    )
                ).count()
                
                profile_text += (
                    f"• Shop #{shop.shop_number} - {shop.location}\n"
                    f"  📦 Products: {products_count} | 🛒 Sales: {sales_count}\n"
                )
        else:
            profile_text += "🏪 No shops yet. Use /start to create one.\n"
        
        # Add edit button
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Edit Profile", callback_data="edit_profile")],
                [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="back_to_settings")]
            ]
        )
        
        await callback.message.answer(profile_text, reply_markup=keyboard)
        await callback.answer()

# Edit profile (placeholder - you can expand this)
@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    await callback.message.answer(
        "✏️ Profile editing feature coming soon!\n"
        "For now, you can run /start again to update your information."
    )
    await callback.answer()

# Language settings
@router.callback_query(F.data == "settings_language")
async def language_settings(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="English 🇬🇧", callback_data="lang_en"),
                InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru")
            ],
            [
                InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="lang_fa"),
                InlineKeyboardButton(text="پښتو 🇦🇫", callback_data="lang_ps")
            ],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(
        "🌐 Select Language\n"
        "Choose your preferred language:",
        reply_markup=keyboard
    )
    await callback.answer()

# Handle language selection
@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    lang_names = {
        "en": "English",
        "ru": "Русский",
        "fa": "فارسی",
        "ps": "پښتو"
    }
    
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        if user:
            user.language = lang_code
            session.commit()
            
            # Get greeting in selected language
            greetings = {
                "en": "Language changed to English! ✅",
                "ru": "Язык изменен на Русский! ✅",
                "fa": "زبان به فارسی تغییر یافت! ✅",
                "ps": "ژبه پښتو ته بدله شوه! ✅"
            }
            
            await callback.message.answer(greetings.get(lang_code, "Language updated! ✅"))
        else:
            await callback.message.answer("❌ User not found.")
    
    await callback.answer()

# Payment status and subscription
@router.callback_query(F.data == "settings_payment")
async def payment_status(callback: CallbackQuery):
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if not user:
            await callback.message.answer("❌ User not found.")
            await callback.answer()
            return
        
        # Get latest payment
        payment = session.query(Payment).filter_by(user_id=user.id).order_by(Payment.created_at.desc()).first()
        
        if payment and payment.expires_at > datetime.now():
            # Active subscription
            days_left = (payment.expires_at - datetime.now()).days
            status_text = (
                f"💳 Payment Status: ACTIVE ✅\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: {payment.plan_type}\n"
                f"💰 Amount: ${payment.amount:.2f}\n"
                f"📅 Started: {payment.created_at.strftime('%Y-%m-%d')}\n"
                f"📅 Expires: {payment.expires_at.strftime('%Y-%m-%d')}\n"
                f"⏳ Days left: {days_left}\n\n"
                f"Your subscription is active. You can renew early below."
            )
        else:
            # No active subscription
            status_text = (
                f"💳 Payment Status: INACTIVE ❌\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ Your subscription has expired or you haven't subscribed yet.\n"
                f"Please choose a subscription plan to continue using all features."
            )
        
        # Subscription plans keyboard
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 1 Month - $9.99", callback_data="plan_1month")],
                [InlineKeyboardButton(text="💰 3 Months - $24.99", callback_data="plan_3months")],
                [InlineKeyboardButton(text="💰 6 Months - $44.99", callback_data="plan_6months")],
                [InlineKeyboardButton(text="💰 1 Year - $79.99", callback_data="plan_1year")],
                [
                    InlineKeyboardButton(text="📱 Contact Admin", callback_data="contact_admin"),
                    InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")
                ]
            ]
        )
        
        await callback.message.answer(status_text, reply_markup=keyboard)
        await callback.answer()

# Handle subscription plan selection
@router.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: CallbackQuery):
    plan_map = {
        "plan_1month": {"name": "1 Month", "price": 9.99, "days": 30},
        "plan_3months": {"name": "3 Months", "price": 24.99, "days": 90},
        "plan_6months": {"name": "6 Months", "price": 44.99, "days": 180},
        "plan_1year": {"name": "1 Year", "price": 79.99, "days": 365}
    }
    
    plan_data = plan_map.get(callback.data)
    
    if not plan_data:
        await callback.message.answer("❌ Invalid plan selected.")
        await callback.answer()
        return
    
    # For demo - in real app, this would redirect to payment gateway
    await callback.message.answer(
        f"💰 **{plan_data['name']} Subscription**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💵 Price: ${plan_data['price']:.2f}\n"
        f"📅 Duration: {plan_data['days']} days\n\n"
        f"⚠️ Payment Integration Required\n"
        f"This is a demo. In a real app, this would redirect to:\n"
        f"• Stripe / PayPal payment\n"
        f"• Bank transfer details\n"
        f"• Cryptocurrency payment\n\n"
        f"Contact admin for manual payment:\n"
        f"@admin_username"
    )
    
    # Simulate payment (for demo only - remove in production)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Simulate Payment (Demo)", callback_data=f"simulate_{callback.data}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="settings_payment")]
        ]
    )
    
    await callback.message.answer("For testing, you can simulate payment:", reply_markup=keyboard)
    await callback.answer()

# Simulate payment (DEMO ONLY - remove in production)
@router.callback_query(F.data.startswith("simulate_"))
async def simulate_payment(callback: CallbackQuery):
    plan_key = callback.data.replace("simulate_", "")
    plan_map = {
        "plan_1month": {"name": "1 Month", "price": 9.99, "days": 30},
        "plan_3months": {"name": "3 Months", "price": 24.99, "days": 90},
        "plan_6months": {"name": "6 Months", "price": 44.99, "days": 180},
        "plan_1year": {"name": "1 Year", "price": 79.99, "days": 365}
    }
    
    plan_data = plan_map.get(plan_key)
    
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
        
        if user and plan_data:
            # Create payment record
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
                f"✅ Payment Successful!\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📦 Plan: {plan_data['name']}\n"
                f"💰 Amount: ${plan_data['price']:.2f}\n"
                f"📅 Valid until: {expires_at.strftime('%Y-%m-%d')}\n\n"
                f"Thank you for your payment! All features are now unlocked."
            )
        else:
            await callback.message.answer("❌ Error processing payment.")
    
    await callback.answer()

# Support contact
@router.callback_query(F.data == "settings_support")
async def support_menu(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Send Message to Admin", callback_data="support_message")],
            [InlineKeyboardButton(text="📞 Contact Info", callback_data="support_contact")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="support_faq")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(
        "📱 Support Center\n"
        "How can we help you?",
        reply_markup=keyboard
    )
    await callback.answer()

# Send message to admin
@router.callback_query(F.data == "support_message")
async def start_support_message(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📝 Send Message to Admin\n"
        "Please type your message (questions, feedback, issues):\n\n"
        "Type /cancel to cancel."
    )
    await state.set_state(SettingsState.waiting_for_support_message)
    await callback.answer()

# Handle support message
@router.message(SettingsState.waiting_for_support_message)
async def send_support_message(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await message.answer("❌ Message cancelled.")
        await state.clear()
        return
    
    # In a real app, you would:
    # 1. Save to database
    # 2. Notify admin via Telegram
    # 3. Send confirmation to user
    
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
        user_name = user.name if user else "Unknown User"
    
    # Simulate sending to admin (replace with actual admin notification)
    admin_notification = (
        f"🆘 New Support Message\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 From: {user_name} (ID: {message.from_user.id})\n"
        f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"💬 Message:\n{message.text}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    
    # For demo, show what would be sent
    await message.answer(
        f"✅ Message Sent to Admin!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Your message has been forwarded to the admin team.\n"
        f"We'll respond within 24 hours.\n\n"
        f"📧 Your message:\n"
        f"{message.text}\n\n"
        f"📧 Admin would receive:\n"
        f"{admin_notification[:500]}..."
    )
    
    await state.clear()

# Contact info
@router.callback_query(F.data == "support_contact")
async def contact_info(callback: CallbackQuery):
    contact_text = (
        "📞 Contact Information\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👨‍💼 Admin: @admin_username\n"
        "📧 Email: admin@example.com\n"
        "🌐 Website: https://example.com\n"
        "📱 Phone: +1 (234) 567-8900\n\n"
        "⏰ Support Hours:\n"
        "Monday - Friday: 9:00 - 18:00\n"
        "Saturday: 10:00 - 14:00\n"
        "Sunday: Closed\n\n"
        
    )
    
    await callback.message.answer(contact_text)
    await callback.answer()

# FAQ
@router.callback_query(F.data == "support_faq")
async def faq_section(callback: CallbackQuery):
    faq_text = (
        "❓ Frequently Asked Questions\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Q: How do I add a product?\n"
        "A: Go to Products → Add New Product\n\n"
        "Q: How do I mark a sale?\n"
        "A: Click on a product and select 'Mark as Sold'\n\n"
        "Q: Can I use the bot for free?\n"
        "A: Yes, basic features are free. Premium features require subscription.\n\n"
        "Q: How do I change language?\n"
        "A: Settings → Language → Select your language\n\n"
        "Q: How to contact support?\n"
        "A: Settings → Support → Send Message to Admin\n\n"
        "Q: How to check my payment status?\n"
        "A: Settings → Payment Status\n\n"
        "Q: Can I have multiple shops?\n"
        "A: Yes, run /start again to create additional shops."
    )
    
    await callback.message.answer(faq_text)
    await callback.answer()

# About section
@router.callback_query(F.data == "settings_about")
async def about_section(callback: CallbackQuery):
    with SessionLocal() as session:
        user_count = session.query(User).count()
        shop_count = session.query(Shop).count()
        from models import Product, Sale
        product_count = session.query(Product).count()
        sale_count = session.query(Sale).count()
    
    about_text = (
        "ℹ️ About QuickSell Bot\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🚀 Version: 2.0.0\n"
        "📅 Released: 2024\n"
        "👨‍💻 Developer: QuickSell Team\n\n"
        "📊 Bot Statistics:\n"
        f"👥 Users: {user_count}\n"
        f"🏪 Shops: {shop_count}\n"
        f"📦 Products: {product_count}\n"
        f"💰 Sales: {sale_count}\n\n"
        "✨ Features:\n"
        "• Product management\n"
        "• Sales tracking\n"
        "• Debt management\n"
        "• Advanced reporting\n"
        "• Multi-language support\n"
        "• Multiple shops\n\n"
        "💖 Thank you for using QuickSell!"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Rate Bot", url="https://t.me/yourbot")],
            [InlineKeyboardButton(text="📱 Share with Friends", url="https://t.me/share/url?url=Check out QuickSell Bot!")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")]
        ]
    )
    
    await callback.message.answer(about_text, reply_markup=keyboard)
    await callback.answer()

# Back to settings navigation
@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery):
    await settings_menu(callback.message)
    await callback.answer()

# Contact admin from payment section
@router.callback_query(F.data == "contact_admin")
async def contact_admin_from_payment(callback: CallbackQuery):
    await callback.message.answer(
        "👨‍💼 Contact Admin for Payment\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "For payment issues or manual payment:\n\n"
        "📱 Telegram: @admin_username\n"
        "📧 Email: payments@example.com\n"
        "💬 WhatsApp: +1 (234) 567-8900\n\n"
        "Please provide your User ID:\n"
        f"`{callback.from_user.id}`"
    )
    await callback.answer()


