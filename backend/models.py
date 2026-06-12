from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    amount = Column(Float)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    location_code = Column(Integer)
    risk_score = Column(Float, default=0.0)
    is_flagged = Column(Boolean, default=False)


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created successfully!")