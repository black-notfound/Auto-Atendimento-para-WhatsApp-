from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./keys.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PlanType(str, enum.Enum):
    day_1  = "1"
    day_7  = "7"
    day_15 = "15"
    day_30 = "30"


class Key(Base):
    __tablename__ = "keys"

    id         = Column(Integer, primary_key=True, index=True)
    value      = Column(String, unique=True, nullable=False)
    plan       = Column(String, nullable=False)   # "1", "7", "15", "30"
    used       = Column(Boolean, default=False)
    used_by    = Column(String, nullable=True)    # phone number
    used_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def add_key(db, value: str, plan: str):
    key = Key(value=value.strip(), plan=plan)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


def get_available_key(db, plan: str):
    return db.query(Key).filter(Key.plan == plan, Key.used == False).first()


def mark_key_used(db, key: Key, phone: str):
    key.used    = True
    key.used_by = phone
    key.used_at = datetime.utcnow()
    db.commit()


def count_available(db, plan: str) -> int:
    return db.query(Key).filter(Key.plan == plan, Key.used == False).count()
