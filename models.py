from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, BigInteger
)
from sqlalchemy.sql import func
from database import Base

# class Shop(Base):
#     __tablename__ = "shops"
#     id = Column(Integer, primary_key=True)
#     shop_number = Column(Integer)
#     location = Column(String)

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True)
#     telegram_id = Column(Integer, unique=True)
#     name = Column(String)
#     shop_id = Column(Integer, ForeignKey("shops.id"))
#     location = Column(String)
#     language = Column(String, default="en")
#     created_at = Column(DateTime, server_default=func.now())

class Shop(Base):
    __tablename__ = "shops"
    id = Column(Integer, primary_key=True)
    shop_number = Column(Integer)
    location = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))  # points to user
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    # telegram_id = Column(Integer, unique=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    name = Column(String)
    location = Column(String)  # optional
    language = Column(String, default="en")
    created_at = Column(DateTime, server_default=func.now())
    # payments = relationship("Payment", back_populates="user")

    

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    shop_id = Column(Integer)
    name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)
    size_cm = Column(String)
    color = Column(String)
    material = Column(String)
    status = Column(String, default="available")
    created_at = Column(DateTime, server_default=func.now())

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    buyer_name = Column(String)
    price = Column(Float)
    payment_type = Column(String)
    is_cleared = Column(Boolean)
    created_at = Column(DateTime, server_default=func.now())

class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer)
    total_amount = Column(Float)
    paid_amount = Column(Float, default=0)
    is_settled = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    plan_type = Column(String)  # "1 Month", "3 Months", etc.
    status = Column(String)  # "pending", "completed", "failed"
    payment_method = Column(String, nullable=True)  # "stripe", "paypal", "manual"
    transaction_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    
    # Relationship
    # user = relationship("User", back_populates="payments")