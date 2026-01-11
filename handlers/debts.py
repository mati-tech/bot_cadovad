# from aiogram import Router, F
# from aiogram.types import Message
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from database import SessionLocal
# from models import Debt, Sale, Product

# router = Router()

# # State for debt payment
# class DebtPaymentState(StatesGroup):
#     waiting_for_amount = State()
#     waiting_for_sale_id = State()

# # List uncleared products/debts
# @router.message(F.text == "🕒 Uncleared Products")
# async def uncleared(message: Message):
#     with SessionLocal() as session:
#         # Get all unsettled debts with related sale and product info
#         debts = session.query(Debt).filter_by(is_settled=False).all()
        
#         if not debts:
#             await message.answer("✅ All debts are cleared!")
#             return
        
#         # Group debts by sale to show better information
#         for debt in debts:
#             # Get sale information
#             sale = session.query(Sale).filter_by(id=debt.sale_id).first()
#             product = None
#             buyer_name = "Unknown"
            
#             if sale:
#                 product = session.query(Product).filter_by(id=sale.product_id).first()
#                 buyer_name = sale.buyer_name
            
#             remaining = debt.total_amount - debt.paid_amount
            
#             await message.answer(
#                 f"📋 Debt ID: {debt.id}\n"
#                 f"👤 Buyer: {buyer_name}\n"
#                 f"📦 Product: {product.name if product else 'N/A'}\n"
#                 f"💰 Total: ${debt.total_amount:.2f}\n"
#                 f"💵 Paid: ${debt.paid_amount:.2f}\n"
#                 f"📊 Remaining: ${remaining:.2f}\n"
#                 f"📅 Created: {debt.created_at.strftime('%Y-%m-%d') if debt.created_at else 'N/A'}\n\n"
#                 f"To pay, send:\n"
#                 f"<code>pay {debt.id} AMOUNT</code>\n"
#                 f"Example: <code>pay {debt.id} 50.00</code>"
#             )

# # Handle debt payments
# @router.message(F.text.startswith("pay "))
# async def pay_debt(message: Message):
#     try:
#         # Parse command: "pay 1 50.00" or "pay 1 50"
#         parts = message.text.strip().split()
#         if len(parts) != 3:
#             await message.answer("❌ Format: <code>pay DEBT_ID AMOUNT</code>\nExample: <code>pay 1 50.00</code>")
#             return
        
#         debt_id = int(parts[1])
#         amount = float(parts[2])
        
#         if amount <= 0:
#             await message.answer("❌ Amount must be positive.")
#             return
        
#         with SessionLocal() as session:
#             # Get debt
#             debt = session.query(Debt).filter_by(id=debt_id, is_settled=False).first()
            
#             if not debt:
#                 await message.answer(f"❌ Debt #{debt_id} not found or already settled.")
#                 return
            
#             # Check if amount exceeds remaining
#             remaining = debt.total_amount - debt.paid_amount
#             if amount > remaining:
#                 await message.answer(f"❌ Amount (${amount:.2f}) exceeds remaining (${remaining:.2f}).")
#                 return
            
#             # Update payment
#             old_paid = debt.paid_amount
#             debt.paid_amount += amount
            
#             # Check if fully paid
#             if debt.paid_amount >= debt.total_amount:
#                 debt.is_settled = True
#                 debt.paid_amount = debt.total_amount  # Prevent overpayment
                
#                 # Get related info for message
#                 sale = session.query(Sale).filter_by(id=debt.sale_id).first()
#                 product = session.query(Product).filter_by(id=sale.product_id).first() if sale else None
                
#                 session.commit()
                
#                 await message.answer(
#                     f"✅ Debt #{debt.id} FULLY SETTLED!\n"
#                     f"👤 Buyer: {sale.buyer_name if sale else 'N/A'}\n"
#                     f"📦 Product: {product.name if product else 'N/A'}\n"
#                     f"💰 Total: ${debt.total_amount:.2f}\n"
#                     f"💵 Final payment: ${amount:.2f}\n"
#                     f"🎉 Debt cleared!"
#                 )
#             else:
#                 session.commit()
                
#                 remaining = debt.total_amount - debt.paid_amount
#                 await message.answer(
#                     f"✅ Partial payment received!\n"
#                     f"Debt ID: {debt.id}\n"
#                     f"💵 Payment: ${amount:.2f}\n"
#                     f"📊 Total paid: ${debt.paid_amount:.2f}\n"
#                     f"💰 Remaining: ${remaining:.2f}"
#                 )
                
#     except ValueError as e:
#         await message.answer(f"❌ Error: {str(e)}\nUse: <code>pay DEBT_ID AMOUNT</code>\nExample: <code>pay 1 50.00</code>")
#     except Exception as e:
#         print(f"Error processing payment: {e}")
#         await message.answer("❌ Error processing payment. Please try again.")

# # Alternative: Interactive payment flow
# @router.message(F.text == "💳 Pay Debt")
# async def start_payment(message: Message, state: FSMContext):
#     with SessionLocal() as session:
#         debts = session.query(Debt).filter_by(is_settled=False).all()
        
#         if not debts:
#             await message.answer("✅ All debts are cleared!")
#             return
        
#         # Create debt list
#         debt_list = ""
#         for i, debt in enumerate(debts[:10], 1):  # Limit to 10 for readability
#             sale = session.query(Sale).filter_by(id=debt.sale_id).first()
#             buyer = sale.buyer_name if sale else "Unknown"
#             remaining = debt.total_amount - debt.paid_amount
            
#             debt_list += f"{i}. #{debt.id} - {buyer} - ${remaining:.2f} remaining\n"
        
#         await message.answer(
#             f"📋 Active Debts:\n{debt_list}\n"
#             f"Reply with debt number to pay (1-{len(debts)})"
#         )
        
#         # Store debts for reference
#         debt_dict = {i+1: debt.id for i, debt in enumerate(debts)}
#         await state.update_data(debts=debt_dict)
#         await state.set_state(DebtPaymentState.waiting_for_sale_id)

# @router.message(DebtPaymentState.waiting_for_sale_id)
# async def select_debt(message: Message, state: FSMContext):
#     try:
#         choice = int(message.text.strip())
#         data = await state.get_data()
#         debts = data.get("debts", {})
        
#         if choice not in debts:
#             await message.answer("❌ Invalid choice. Please select a number from the list.")
#             return
        
#         debt_id = debts[choice]
        
#         with SessionLocal() as session:
#             debt = session.query(Debt).filter_by(id=debt_id).first()
#             if debt and not debt.is_settled:
#                 remaining = debt.total_amount - debt.paid_amount
#                 await state.update_data(debt_id=debt_id, remaining=remaining)
#                 await state.set_state(DebtPaymentState.waiting_for_amount)
#                 await message.answer(
#                     f"💳 Paying Debt #{debt_id}\n"
#                     f"💰 Remaining: ${remaining:.2f}\n"
#                     f"Enter payment amount:"
#                 )
#             else:
#                 await message.answer("❌ Debt not found or already settled.")
#                 await state.clear()
                
#     except ValueError:
#         await message.answer("❌ Please enter a valid number.")

# @router.message(DebtPaymentState.waiting_for_amount)
# async def process_payment(message: Message, state: FSMContext):
#     try:
#         amount = float(message.text.strip())
#         data = await state.get_data()
#         debt_id = data.get("debt_id")
#         remaining = data.get("remaining", 0)
        
#         if amount <= 0:
#             await message.answer("❌ Amount must be positive. Enter payment amount:")
#             return
        
#         if amount > remaining:
#             await message.answer(f"❌ Amount exceeds remaining (${remaining:.2f}). Enter smaller amount:")
#             return
        
#         with SessionLocal() as session:
#             debt = session.query(Debt).filter_by(id=debt_id).first()
#             if debt:
#                 debt.paid_amount += amount
                
#                 if debt.paid_amount >= debt.total_amount:
#                     debt.is_settled = True
#                     debt.paid_amount = debt.total_amount
                
#                 session.commit()
                
#                 # Get updated info
#                 new_remaining = debt.total_amount - debt.paid_amount
                
#                 if debt.is_settled:
#                     await message.answer(f"✅ Debt #{debt_id} fully settled! 🎉")
#                 else:
#                     await message.answer(
#                         f"✅ Payment of ${amount:.2f} received!\n"
#                         f"Remaining: ${new_remaining:.2f}"
#                     )
#             else:
#                 await message.answer("❌ Debt not found.")
        
#         await state.clear()
        
#     except ValueError:
#         await message.answer("❌ Please enter a valid amount (e.g., 50.00):")

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import SessionLocal
from models import Debt, Sale, Product

router = Router()

# State for payment type selection
class PaymentState(StatesGroup):
    waiting_for_payment_type = State()

# List uncleared products/debts with RETURN/PAID buttons
@router.message(F.text == "🕒 Uncleared Products")
async def uncleared(message: Message):
    with SessionLocal() as session:
        # Get all unsettled debts with related sale and product info
        debts = session.query(Debt).filter_by(is_settled=False).all()
        
        if not debts:
            await message.answer("✅ All debts are cleared!")
            return
        
        for debt in debts:
            # Get sale information
            sale = session.query(Sale).filter_by(id=debt.sale_id).first()
            product = None
            buyer_name = "Unknown"
            
            if sale:
                product = session.query(Product).filter_by(id=sale.product_id).first()
                buyer_name = sale.buyer_name
            
            remaining = debt.total_amount - debt.paid_amount
            
            # Create inline keyboard with two options
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 Product Returned",
                            callback_data=f"return:{debt.id}:{debt.sale_id}"
                        ),
                        InlineKeyboardButton(
                            text="💰 Full Payment Received",
                            callback_data=f"full_payment:{debt.id}:{debt.sale_id}"
                        )
                    ]
                ]
            )
            
            await message.answer(
                f"📋 Debt ID: {debt.id}\n"
                f"👤 Buyer: {buyer_name}\n"
                f"📦 Product: {product.name if product else 'N/A'}\n"
                f"💰 Total Amount: ${debt.total_amount:.2f}\n"
                f"💵 Paid: ${debt.paid_amount:.2f}\n"
                f"📊 Remaining: ${remaining:.2f}\n\n"
                f"Choose action:",
                reply_markup=keyboard
            )

# Handle product return (no sale)
@router.callback_query(F.data.startswith("return:"))
async def handle_product_return(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        debt_id = int(parts[1])
        sale_id = int(parts[2])
        
        with SessionLocal() as session:
            # Get debt and related records
            debt = session.query(Debt).filter_by(id=debt_id).first()
            sale = session.query(Sale).filter_by(id=sale_id).first() if sale_id else None
            product = None
            
            if sale:
                product = session.query(Product).filter_by(id=sale.product_id).first()
                
                # Mark debt as settled (product returned, no money)
                debt.is_settled = True
                debt.paid_amount = 0  # Reset since product was returned
                
                # Update product status back to available
                if product:
                    product.status = "available"
                    product.quantity += 1  # Increase quantity since product is back
                
                # Delete the sale record (since no actual sale happened)
                session.delete(sale)
                
                session.commit()
                
                await callback.message.edit_text(
                    f"✅ Product Return Processed!\n\n"
                    f"📦 Product: {product.name if product else 'N/A'}\n"
                    f"👤 Buyer: {sale.buyer_name if sale else 'N/A'}\n"
                    f"💰 Debt #{debt.id} cleared\n"
                    f"🔄 Product status: Available\n"
                    f"📊 Quantity: +1"
                )
            else:
                await callback.message.edit_text("❌ Sale record not found.")
                
    except Exception as e:
        print(f"Error handling product return: {e}")
        await callback.message.edit_text("❌ Error processing return.")
    finally:
        await callback.answer()

# Handle full payment received
@router.callback_query(F.data.startswith("full_payment:"))
async def handle_full_payment(callback: CallbackQuery, state: FSMContext):
    try:
        parts = callback.data.split(":")
        debt_id = int(parts[1])
        sale_id = int(parts[2])
        
        with SessionLocal() as session:
            # Get debt and related records
            debt = session.query(Debt).filter_by(id=debt_id).first()
            sale = session.query(Sale).filter_by(id=sale_id).first() if sale_id else None
            
            if not debt or not sale:
                await callback.message.edit_text("❌ Debt or sale record not found.")
                await callback.answer()
                return
            
            # Store data for payment type selection
            await state.update_data(
                debt_id=debt_id,
                sale_id=sale_id
            )
            
            # Create payment type selection keyboard
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="💵 Cash", callback_data=f"pay_cash:{debt_id}:{sale_id}"),
                        InlineKeyboardButton(text="💳 Card", callback_data=f"pay_card:{debt_id}:{sale_id}")
                    ],
                    [
                        InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_pay:{debt_id}")
                    ]
                ]
            )
            
            # Get product info for message
            product = session.query(Product).filter_by(id=sale.product_id).first()
            remaining = debt.total_amount - debt.paid_amount
            
            await callback.message.edit_text(
                f"💰 Full Payment Received!\n\n"
                f"📦 Product: {product.name if product else 'N/A'}\n"
                f"👤 Buyer: {sale.buyer_name}\n"
                f"💵 Amount: ${remaining:.2f}\n\n"
                f"Select payment type:",
                reply_markup=keyboard
            )
                
    except Exception as e:
        print(f"Error handling full payment: {e}")
        await callback.message.edit_text("❌ Error processing payment.")
    finally:
        await callback.answer()

# Handle cash payment
@router.callback_query(F.data.startswith("pay_cash:"))
async def handle_cash_payment(callback: CallbackQuery):
    await _process_payment(callback, "cash")

# Handle card payment  
@router.callback_query(F.data.startswith("pay_card:"))
async def handle_card_payment(callback: CallbackQuery):
    await _process_payment(callback, "card")

# Common payment processing function
async def _process_payment(callback: CallbackQuery, payment_type: str):
    try:
        parts = callback.data.split(":")
        debt_id = int(parts[1])
        sale_id = int(parts[2])
        
        with SessionLocal() as session:
            # Get debt and related records
            debt = session.query(Debt).filter_by(id=debt_id).first()
            sale = session.query(Sale).filter_by(id=sale_id).first()
            product = session.query(Product).filter_by(id=sale.product_id).first() if sale else None
            
            if not debt or not sale or not product:
                await callback.message.edit_text("❌ Record not found.")
                await callback.answer()
                return
            
            # Calculate remaining amount
            remaining = debt.total_amount - debt.paid_amount
            
            # Update debt (full payment)
            debt.paid_amount = debt.total_amount
            debt.is_settled = True
            
            # Update sale
            sale.is_cleared = True
            sale.payment_type = payment_type
            
            # Update product as sold
            product.status = "sold"
            # Note: Quantity was already decreased when marked as borrowed
            
            session.commit()
            
            await callback.message.edit_text(
                f"✅ Payment Processed Successfully!\n\n"
                f"📦 Product: {product.name}\n"
                f"👤 Buyer: {sale.buyer_name}\n"
                f"💰 Amount: ${remaining:.2f}\n"
                f"💳 Payment type: {payment_type.upper()}\n"
                f"🏷️ Product status: Sold\n"
                f"🎉 Debt fully settled!"
            )
                
    except Exception as e:
        print(f"Error processing {payment_type} payment: {e}")
        await callback.message.edit_text("❌ Error processing payment.")
    finally:
        await callback.answer()

# Handle cancel payment
@router.callback_query(F.data.startswith("cancel_pay:"))
async def handle_cancel_payment(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Payment cancelled.")
    await state.clear()
    await callback.answer()

# Keep existing pay command for backward compatibility (optional)
@router.message(F.text.startswith("pay "))
async def pay_debt(message: Message):
    # This can be removed or kept for text-based payment
    # Since we're using buttons, this might not be needed
    await message.answer("⚠️ Please use the buttons above each debt to process payments.")