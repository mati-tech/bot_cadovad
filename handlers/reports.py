from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models import Sale, Product, Shop
from datetime import datetime, timedelta
from collections import defaultdict

router = Router()

# States for custom date selection
class ReportState(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()

# Main reports menu
@router.message(F.text == "📊 Reports")
async def reports_menu(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Today", callback_data="report_today")],
            [InlineKeyboardButton(text="📅 This Week", callback_data="report_week")],
            [InlineKeyboardButton(text="📅 This Month", callback_data="report_month")],
            [InlineKeyboardButton(text="📅 Custom Period", callback_data="report_custom")],
            [InlineKeyboardButton(text="📈 Analytics Dashboard", callback_data="report_analytics")]
        ]
    )
    
    await message.answer(
        "📊 Reports & Analytics\n"
        "Select time period:",
        reply_markup=keyboard
    )

# Today's report
@router.callback_query(F.data == "report_today")
async def today_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 Today's Sales"
    )

# This week's report
@router.callback_query(F.data == "report_week")
async def week_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 This Week's Sales"
    )

# This month's report
@router.callback_query(F.data == "report_month")
async def month_report(callback: CallbackQuery):
    today = datetime.now().date()
    start_date = datetime.combine(today.replace(day=1), datetime.min.time())
    end_date = datetime.combine(today, datetime.max.time())
    
    await show_sales_report(
        callback,
        start_date,
        end_date,
        "📅 This Month's Sales"
    )

# Start custom period selection
@router.callback_query(F.data == "report_custom")
async def custom_period_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "📅 Enter start date (YYYY-MM-DD):\n"
        "Example: 2024-01-15"
    )
    await state.set_state(ReportState.waiting_for_start_date)
    await callback.answer()

# Get start date
@router.message(ReportState.waiting_for_start_date)
async def get_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        await state.update_data(start_date=start_date)
        await message.answer(
            "📅 Enter end date (YYYY-MM-DD):\n"
            "Example: 2024-01-20"
        )
        await state.set_state(ReportState.waiting_for_end_date)
    except ValueError:
        await message.answer("❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-15):")

# Get end date and show report
@router.message(ReportState.waiting_for_end_date)
async def get_end_date(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text.strip(), "%Y-%m-%d")
        data = await state.get_data()
        start_date = data.get("start_date")
        
        # Make end_date inclusive (end of day)
        end_date = datetime.combine(end_date.date(), datetime.max.time())
        
        await show_sales_report(
            message,
            start_date,
            end_date,
            f"📅 Custom Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-20):")

# Analytics dashboard
@router.callback_query(F.data == "report_analytics")
async def analytics_dashboard(callback: CallbackQuery):
    with SessionLocal() as session:
        # Get all cleared sales
        sales = session.query(Sale).filter_by(is_cleared=True).all()
        
        if not sales:
            await callback.message.answer("📭 No sales data available for analytics.")
            await callback.answer()
            return
        
        # Calculate metrics
        total_revenue = sum(sale.price for sale in sales)
        total_sales = len(sales)
        avg_sale = total_revenue / total_sales if total_sales > 0 else 0
        
        # Get top products
        product_sales = defaultdict(float)
        for sale in sales:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            if product:
                product_sales[product.name] += sale.price
        
        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get top buyers
        buyer_sales = defaultdict(float)
        for sale in sales:
            buyer_sales[sale.buyer_name] += sale.price
        
        top_buyers = sorted(buyer_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get daily trends (last 7 days)
        daily_revenue = defaultdict(float)
        week_ago = datetime.now() - timedelta(days=7)
        recent_sales = [s for s in sales if s.created_at >= week_ago]
        
        for sale in recent_sales:
            date_str = sale.created_at.strftime('%Y-%m-%d')
            daily_revenue[date_str] += sale.price
        
        # Create analytics message
        analytics_text = (
            f"📈 **Analytics Dashboard**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 Total Revenue: ${total_revenue:.2f}\n"
            f"📦 Total Sales: {total_sales} items\n"
            f"📊 Average Sale: ${avg_sale:.2f}\n"
            f"📅 Data Period: All time\n\n"
        )
        
        # Add top products
        analytics_text += "🏆 **Top Products by Revenue:**\n"
        for i, (product, revenue) in enumerate(top_products, 1):
            analytics_text += f"{i}. {product}: ${revenue:.2f}\n"
        
        analytics_text += "\n👥 **Top Buyers:**\n"
        for i, (buyer, spent) in enumerate(top_buyers, 1):
            analytics_text += f"{i}. {buyer}: ${spent:.2f}\n"
        
        # Add daily trends
        if daily_revenue:
            analytics_text += "\n📊 **Last 7 Days Daily Revenue:**\n"
            for date_str in sorted(daily_revenue.keys())[-7:]:
                analytics_text += f"{date_str}: ${daily_revenue[date_str]:.2f}\n"
        
        # Add action buttons
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 View Sales", callback_data="report_today")],
                [InlineKeyboardButton(text="📊 More Analytics", callback_data="detailed_analytics")],
                [InlineKeyboardButton(text="📈 Compare Periods", callback_data="compare_periods")]
            ]
        )
        
        await callback.message.answer(analytics_text, reply_markup=keyboard)
        await callback.answer()

# Detailed analytics
@router.callback_query(F.data == "detailed_analytics")
async def detailed_analytics(callback: CallbackQuery):
    with SessionLocal() as session:
        sales = session.query(Sale).filter_by(is_cleared=True).all()
        
        # Payment method analysis
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
        
        # Find best day and hour
        best_day = max(daily_sales.items(), key=lambda x: x[1]) if daily_sales else ("N/A", 0)
        best_hour = max(hourly_sales.items(), key=lambda x: x[1]) if hourly_sales else ("N/A", 0)
        
        analytics_text = (
            f"📊 **Detailed Analytics**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💳 **Payment Methods:**\n"
        )
        
        for method, amount in payment_methods.items():
            percentage = (amount / sum(payment_methods.values())) * 100
            analytics_text += f"• {method.upper()}: ${amount:.2f} ({percentage:.1f}%)\n"
        
        analytics_text += f"\n⏰ **Peak Hours:**\n"
        for hour, count in sorted(hourly_sales.items(), key=lambda x: x[1], reverse=True)[:5]:
            analytics_text += f"• {hour:02d}:00 - {count} sales\n"
        
        analytics_text += f"\n📅 **Best Performing Day:**\n"
        analytics_text += f"• {best_day[0]}: {best_day[1]} sales\n"
        
        await callback.message.answer(analytics_text)
        await callback.answer()

# Compare periods
@router.callback_query(F.data == "compare_periods")
async def compare_periods(callback: CallbackQuery):
    with SessionLocal() as session:
        today = datetime.now()
        
        # Current month
        current_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_sales = session.query(Sale).filter(
            Sale.is_cleared == True,
            Sale.created_at >= current_start
        ).all()
        
        # Previous month
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
            change_text = "N/A (no previous data)"
        
        compare_text = (
            f"📊 **Monthly Comparison**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 Current Month ({current_start.strftime('%B %Y')}):\n"
            f"• Revenue: ${current_revenue:.2f}\n"
            f"• Sales: {len(current_sales)} items\n"
            f"• Avg: ${current_revenue/len(current_sales):.2f if current_sales else 0}\n\n"
            f"📅 Previous Month ({prev_start.strftime('%B %Y')}):\n"
            f"• Revenue: ${prev_revenue:.2f}\n"
            f"• Sales: {len(prev_sales)} items\n"
            f"• Avg: ${prev_revenue/len(prev_sales):.2f if prev_sales else 0}\n\n"
            f"📈 **Growth:** {change_text}"
        )
        
        await callback.message.answer(compare_text)
        await callback.answer()

# Helper function to show sales report with analytics button
async def show_sales_report(source, start_date, end_date, title):
    with SessionLocal() as session:
        # Get sales for the period
        sales = session.query(Sale).filter(
            Sale.is_cleared == True,
            Sale.created_at >= start_date,
            Sale.created_at <= end_date
        ).order_by(Sale.created_at.desc()).all()
        
        if not sales:
            if hasattr(source, 'message'):
                await source.message.answer(f"📭 No sales found for {title}.")
                await source.answer()
            else:
                await source.answer(f"📭 No sales found for {title}.")
            return
        
        # Calculate totals
        total_amount = sum(sale.price for sale in sales)
        total_items = len(sales)
        
        # Get top products in this period
        product_counts = defaultdict(int)
        product_revenue = defaultdict(float)
        
        for sale in sales:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            if product:
                product_counts[product.name] += 1
                product_revenue[product.name] += sale.price
        
        # Create report
        report_text = (
            f"{title}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
            f"💰 Total Revenue: ${total_amount:.2f}\n"
            f"📦 Total Sales: {total_items} items\n"
            f"📊 Average: ${total_amount/total_items:.2f}\n\n"
        )
        
        # Add recent sales (last 5)
        report_text += "🛒 **Recent Sales:**\n"
        for sale in sales[:5]:
            product = session.query(Product).filter_by(id=sale.product_id).first()
            product_name = product.name if product else "Unknown"
            time_str = sale.created_at.strftime('%H:%M') if sale.created_at else "N/A"
            
            report_text += (
                f"• {product_name} - ${sale.price:.2f}\n"
                f"  👤 {sale.buyer_name} | 💳 {sale.payment_type or 'N/A'} | ⏰ {time_str}\n"
            )
        
        # Add top products section
        if product_counts:
            top_by_count = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_by_revenue = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:3]
            
            report_text += "\n🏆 **Top Products by Quantity:**\n"
            for product, count in top_by_count:
                report_text += f"• {product}: {count} sales\n"
            
            report_text += "\n💰 **Top Products by Revenue:**\n"
            for product, revenue in top_by_revenue:
                report_text += f"• {product}: ${revenue:.2f}\n"
        
        # Create keyboard with analytics options
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📈 View Analytics", callback_data="report_analytics")],
                [
                    InlineKeyboardButton(text="📅 Today", callback_data="report_today"),
                    InlineKeyboardButton(text="📅 Week", callback_data="report_week"),
                    InlineKeyboardButton(text="📅 Month", callback_data="report_month")
                ],
                [InlineKeyboardButton(text="📊 Custom Period", callback_data="report_custom")]
            ]
        )
        
        # Send the message
        if hasattr(source, 'message'):
            await source.message.answer(report_text, reply_markup=keyboard)
            await source.answer()
        else:
            await source.answer(report_text, reply_markup=keyboard)

# Backward compatibility - keep old menu items
@router.message(F.text == "📊 Sold Items")
async def sold_items_legacy(message: Message):
    # Redirect to new reports system
    await reports_menu(message)

@router.message(F.text == "💰 Total Revenue")
async def total_revenue_legacy(message: Message):
    # Show analytics dashboard
    await analytics_dashboard(message)

@router.message(F.text == "📈 Monthly Report")
async def monthly_report_legacy(message: Message):
    await month_report(message)

@router.message(F.text == "📅 Daily Report")
async def daily_report_legacy(message: Message):
    await today_report(message)