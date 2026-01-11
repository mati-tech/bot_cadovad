from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# Главное меню (Main Menu)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить товар")],
        [KeyboardButton(text="📦 Все товары")],
        [KeyboardButton(text="🕒 Неоплаченные")],
        [KeyboardButton(text="📊 Проданные товары")],
        [KeyboardButton(text="⚙️ Настройки")]
    ],
    resize_keyboard=True
)

# Действия с товаром (Product Actions)
def product_actions(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Продано", callback_data=f"sold:{product_id}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{product_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete:{product_id}")
            ]
        ]
    )

# Тип оплаты (Payment Type)
def payment_type_kb(product_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Оплачено", callback_data=f"clear:{product_id}"),
                InlineKeyboardButton(text="🕒 В долг", callback_data=f"borrow:{product_id}")
            ]
        ]
    )

# Наличные или карта (Cash/Card)
def cash_card_kb(sale_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Наличные", callback_data=f"cash:{sale_id}"),
                InlineKeyboardButton(text="Карта", callback_data=f"card:{sale_id}")
            ]
        ]
    )