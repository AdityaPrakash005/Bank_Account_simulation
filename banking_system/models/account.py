"""Bank Account entity supporting multiple tiers and overdraft ceilings."""

import datetime
from enum import Enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from models.base import Base


class AccountType(str, Enum):
    SAVINGS = "Savings"
    CHECKING = "Checking"
    MONEY_MARKET = "Money Market"


class AccountStatus(str, Enum):
    ACTIVE = "Active"
    FROZEN = "Frozen"
    SUSPENDED = "Suspended"
    CLOSED = "Closed"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_number = Column(String(12), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    account_type = Column(String(20), nullable=False, default=AccountType.CHECKING.value)
    status = Column(String(20), nullable=False, default=AccountStatus.ACTIVE.value)
    balance = Column(Numeric(precision=14, scale=2), default=0.00, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", order_by="desc(Transaction.timestamp)")

    @property
    def overdraft_limit(self) -> float:
        """Checking accounts maintain a $200.00 overdraft buffer."""
        if self.account_type == AccountType.CHECKING.value:
            return 200.00
        return 0.00

    @property
    def available_balance(self) -> float:
        return float(self.balance) + self.overdraft_limit