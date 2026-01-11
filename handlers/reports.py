from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models import Sale, Product, Shop
from datetime import datetime, timedelta
from collections import defaultdict

router = Router()

# Состояния для выбора произвольной даты
class ReportState(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()

# Главное меню отчетов
@router.message(F.text == "📊 Отчеты")
async def reports_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="report_today")],
            [InlineKeyboardButton(text="📅 Эта неделя", callback_data="report_week")],
            [InlineKeyboardButton(text="📅 Этот месяц", callback_data="report_month")],
            [InlineKeyboardButton(text="📅 Свой период", callback_data="report_custom")],
            [InlineKeyboardButton(text="📈 Панель аналитики", callback_data="report_analytics")]
        ]
    )
    
    await message.answer(
        "📊 Отчеты и Аналитика\n"
        "Выберите период времени:",
        reply_markup=keyboard
    )

# Отчет за сегодня
@router.callback_query(F.data == "report_today")
async def today_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 Продажи за сегодня"
    )

# Отчет за неделю
@router.callback_query(F.data == "report_week")
async def week_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 Продажи за эту неделю"
    )

# Отчет за месяц
@router.callback_query(F.data == "report_month")
async def month_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today.replace(day=1), datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 Продажи за этот месяц"
    )

# Начало выбора произвольного периода
@router.callback_query(F.data == "report_custom")
async def custom_period_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📅 Введите дату начала (ГГГГ-ММ-ДД):\n"
        "Пример: 2024-01-15"
    )
    await state.set_state(ReportState.waiting_for_start_date)
    await callback.answer()

# Получение даты начала
@router.message(ReportState.waiting_for_start_date)
async def get_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        await state.update_data(start_date=start_date)
        await message.answer(
            "📅 Введите дату окончания (ГГГГ-ММ-ДД):\n"
            "Пример: 2024-01-20"
        )
        await state.set_state(ReportState.waiting_for_end_date)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД (напр. 2024-01-15):")

# Получение даты окончания и вывод отчета
@router.message(ReportState.waiting_for_end_date)
async def get_end_date(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        data = await state.get_data()
        start_date = data.get("start_date")
        
        end_date = datetime.combine(end_date.date(), datetime.max.time())
        
        await show_sales_report(
            message,
            start_date,
            end_date,
            f"📅 Период: с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД (напр. 2024-01-20):")

# Панель аналитики
@router.callback_query(F.data == "report_analytics")
async def analytics_dashboard(callback: CallbackQuery):
    with SessionLocal() as session:
        sales = session.query(Sale).filter_by(is_cleared=True).all()
        
        if not sales:
            await callback.message.answer("📭 Данные о продажах для аналитики отсутствуют.")
            await callback.answer()
            return
        
        total_revenue = sum(sale.price for sale in sales)
        total_sales = len(sales)
        avg_sale = total_revenue / total_sales if total_sales > 0 else 0
        
        product_sales = defaultdict(float)
        for sale in sales:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            if product:
                product_sales[product.name] += sale.price
        
        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        buyer_sales = defaultdict(float)
        for sale in sales:
            buyer_sales[sale.buyer_name] += sale.price
        
        top_buyers = sorted(buyer_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        daily_revenue = defaultdict(float)
        week_ago = datetime.now() - timedelta(days=7)
        recent_sales = [s for s in sales if s.created_at >= week_ago]
        
        for sale in recent_sales:
            date_str = sale.created_at.strftime('%Y-%m-%d')
            daily_revenue[date_str] += sale.price
        
        analytics_text = (
            f"📈 Панель аналитики\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Общая выручка: {total_revenue:.2f}\n"
            f"📦 Всего продаж: {total_sales} шт.\n"
            f"📊 Средний чек: {avg_sale:.2f}\n"
            f"📅 Период: За все время\n\n"
        )
        
        analytics_text += "🏆 Топ товаров по выручке:\n"
        for i, (product, revenue) in enumerate(top_products, 1):
            analytics_text += f"{i}. {product}: {revenue:.2f}\n"
        
        analytics_text += "\n👥 Топ покупателей:\n"
        for i, (buyer, spent) in enumerate(top_buyers, 1):
            analytics_text += f"{i}. {buyer}: {spent:.2f}\n"
        
        if daily_revenue:
            analytics_text += "\n📊 Выручка за последние 7 дней:\n"
            for date_str in sorted(daily_revenue.keys())[-7:]:
                analytics_text += f"{date_str}: {daily_revenue[date_str]:.2f}\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Посмотреть продажи", callback_data="report_today")],
                [InlineKeyboardButton(text="📊 Детальная аналитика", callback_data="detailed_analytics")],
                [InlineKeyboardButton(text="📈 Сравнить периоды", callback_data="compare_periods")]
            ]
        )
        
        await callback.message.answer(analytics_text, reply_markup=keyboard)
        await callback.answer()

# Детальная аналитика
@router.callback_query(F.data == "detailed_analytics")
async def detailed_analytics(callback: CallbackQuery):
    with SessionLocal() as session:
        sales = session.query(Sale).filter_by(is_cleared=True).all()
        
        payment_methods = defaultdict(float)
        daily_sales = defaultdict(int)
        hourly_sales = defaultdict(int)
        
        for sale in sales:
            if sale.payment_type:
                payment_methods[sale.payment_type] += sale.price
            
            if sale.created_at:
                date_str = sale.created_at.strftime('%Y-%m-%d')
                daily_sales[date_str] += 1
                hour = sale.created_at.hour
                hourly_sales[hour] += 1
        
        best_day = max(daily_sales.items(), key=lambda x: x[1]) if daily_sales else ("Н/Д", 0)
        
        analytics_text = (
            f"📊 Детальная аналитика\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 Способы оплаты:\n"
        )
        
        total_m_val = sum(payment_methods.values())
        for method, amount in payment_methods.items():
            percentage = (amount / total_m_val) * 100 if total_m_val > 0 else 0
            m_name = "Наличные" if method == "cash" else "Карта" if method == "card" else method.upper()
            analytics_text += f"• {m_name}: {amount:.2f} ({percentage:.1f}%)\n"
        
        analytics_text += f"\n⏰ Пиковые часы:\n"
        for hour, count in sorted(hourly_sales.items(), key=lambda x: x[1], reverse=True)[:5]:
            analytics_text += f"• {hour:02d}:00 — {count} продаж\n"
        
        analytics_text += f"\n📅 Самый активный день:\n"
        analytics_text += f"• {best_day[0]}: {best_day[1]} продаж\n"
        
        await callback.message.answer(analytics_text)
        await callback.answer()

# Сравнение периодов
@router.callback_query(F.data == "compare_periods")
async def compare_periods(callback: CallbackQuery):
    with SessionLocal() as session:
        today = datetime.now()
        
        current_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_sales = session.query(Sale).filter(
            Sale.is_cleared == True,
            Sale.created_at >= current_start
        ).all()
        
        if current_start.month == 1:
            prev_start = current_start.replace(year=current_start.year-1, month=12)
        else:
            prev_start = current_start.replace(month=current_start.month-1)
        
        prev_end = current_start - timedelta(seconds=1)
        prev_sales = session.query(Sale).filter(
            Sale.is_cleared == True,
            Sale.created_at >= prev_start,
            Sale.created_at <= prev_end
        ).all()
        
        current_revenue = sum(s.price for s in current_sales)
        prev_revenue = sum(s.price for s in prev_sales)
        
        if prev_revenue > 0:
            change = ((current_revenue - prev_revenue) / prev_revenue) * 100
            change_text = f"{'📈 +' if change >= 0 else '📉 '}{change:.1f}%"
        else:
            change_text = "Н/Д (нет данных)"
        
        compare_text = (
            f"📊 Ежемесячное сравнение\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 Текущий месяц ({current_start.strftime('%m.%Y')}):\n"
            f"• Выручка: {current_revenue:.2f}\n"
            f"• Продажи: {len(current_sales)} шт.\n\n"
            f"📅 Прошлый месяц ({prev_start.strftime('%m.%Y')}):\n"
            f"• Выручка: {prev_revenue:.2f}\n"
            f"• Продажи: {len(prev_sales)} шт.\n\n"
            f"📈 Рост: {change_text}"
        )
        
        await callback.message.answer(compare_text)
        await callback.answer()

# Вспомогательная функция для отображения отчета
async def show_sales_report(source, start_date, end_date, title):
    with SessionLocal() as session:
        sales = session.query(Sale).filter(
            Sale.is_cleared == True,
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        ).order_by(Sale.created_at.desc()).all()
        
        if not sales:
            msg = f"📭 Продажи за период '{title}' не найдены."
            if hasattr(source, 'message'):
                await source.message.answer(msg)
                await source.answer()
            else:
                await source.answer(msg)
            return
        
        total_amount = sum(sale.price for sale in sales)
        total_items = len(sales)
        
        product_counts = defaultdict(int)
        product_revenue = defaultdict(float)
        
        for sale in sales:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            if product:
                product_counts[product.name] += 1
                product_revenue[product.name] += sale.price
        
        report_text = (
            f"{title}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}\n"
            f"💰 Общая выручка: {total_amount:.2f}\n"
            f"📦 Всего продаж: {total_items} шт.\n"
            f"📊 Средний чек: {total_amount/total_items:.2f}\n\n"
        )
        
        report_text += "🛒 Последние продажи:\n"
        for sale in sales[:5]:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            p_name = product.name if product else "Неизвестно"
            time_str = sale.created_at.strftime('%H:%M') if sale.created_at else "--:--"
            p_type = "Наличные" if sale.payment_type == "cash" else "Карта" if sale.payment_type == "card" else "Н/Д"
            
            report_text += (
                f"• {p_name} — {sale.price:.2f}\n"
                f"  👤 {sale.buyer_name} | 💳 {p_type} | ⏰ {time_str}\n"
            )
        
        if product_counts:
            top_by_count = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            report_text += "\n🏆 Топ товаров (кол-во):\n"
            for product, count in top_by_count:
                report_text += f"• {product}: {count} шт.\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📈 Аналитика", callback_data="report_analytics")],
                [
                    InlineKeyboardButton(text="📅 Сегодня", callback_data="report_today"),
                    InlineKeyboardButton(text="📅 Неделя", callback_data="report_week"),
                    InlineKeyboardButton(text="📅 Месяц", callback_data="report_month")
                ],
                [InlineKeyboardButton(text="📊 Свой период", callback_data="report_custom")]
            ]
        )
        
        if hasattr(source, 'message'):
            await source.message.answer(report_text, reply_markup=keyboard)
            await source.answer()
        else:
            await source.answer(report_text, reply_markup=keyboard)

# Совместимость со старыми пунктами меню
@router.message(F.text == "📊 Проданные товары")
async def sold_items_legacy(message: Message):
    await reports_menu(message)

@router.message(F.text == "💰 Общая выручка")
async def total_revenue_legacy(message: Message):
    await analytics_dashboard(message)

@router.message(F.text == "📈 Ежемесячный отчет")
async def monthly_report_legacy(message: Message):
    await month_report(message)

@router.message(F.text == "📅 Дневной отчет")
async def daily_report_legacy(message: Message):
    await today_report(message)