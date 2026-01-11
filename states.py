from aiogram.fsm.state import State, StatesGroup

class RegisterState(StatesGroup):
    name = State()
    location = State()
    shop = State()

class ProductState(StatesGroup):
    name = State()
    quantity = State()
    price = State()
    size = State()
    color = State()
    material = State()



class SaleState(StatesGroup):
    buyer_name = State()
    debt_payment = State()
