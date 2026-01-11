from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# Create sync engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# Base class for models
Base = declarative_base()

# Initialize database (create tables)
def init_db():
    from models import User, Shop, Product, Sale, Debt
    Base.metadata.create_all(bind=engine)
