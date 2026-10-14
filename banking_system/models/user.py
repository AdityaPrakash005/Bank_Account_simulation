"""User domain entity."""

import datetime
from enum import Enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from models.base import Base


class UserRole(str, Enum):
    CUSTOMER = "Customer"
    TELLER = "Teller"
    ADMIN = "Admin"
    AUDITOR = "Auditor"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    pin_hash = Column(String(128), nullable=False)
    pin_salt = Column(String(64), nullable=False)
    role = Column(String(20), default=UserRole.CUSTOMER.value, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    accounts = relationship("Account", back_populates="owner", cascade="all, delete-orphan")