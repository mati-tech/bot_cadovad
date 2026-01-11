from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Add New Product")],
        [KeyboardButton(text="📦 All Products")],
        [KeyboardButton(text="🕒 Uncleared Products")],
        [KeyboardButton(text="📊 Sold Items")],
        [KeyboardButton(text="⚙️ Settings")]
    ],
    resize_keyboard=True
)

def product_actions(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Sold", callback_data=f"sold:{product_id}"),
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"edit:{product_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Delete", callback_data=f"delete:{product_id}")
            ]
        ]
    )

def payment_type_kb(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Money Clear", callback_data=f"clear:{product_id}"),
                InlineKeyboardButton(text="🕒 Borrowed", callback_data=f"borrow:{product_id}")
            ]
        ]
    )

def cash_card_kb(sale_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Cash", callback_data=f"cash:{sale_id}"),
                InlineKeyboardButton(text="Card", callback_data=f"card:{sale_id}")
            ]
        ]
    )
