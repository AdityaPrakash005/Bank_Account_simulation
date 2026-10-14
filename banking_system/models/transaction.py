"""Transaction ledger records with double-entry traceability."""

import datetime
from enum import Enum
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from models.base import Base


class TransactionType(str, Enum):
    DEPOSIT = "Deposit"
    WITHDRAWAL = "Withdrawal"
    TRANSFER_SENT = "Transfer Sent"
    TRANSFER_RECEIVED = "Transfer Received"
    INTEREST_CREDITED = "Interest Credited"
    FEE_CHARGED = "Fee Charged"
    REVERSAL = "Reversal"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    type = Column(String(30), nullable=False)
    amount = Column(Numeric(precision=14, scale=2), nullable=False)
    balance_after = Column(Numeric(precision=14, scale=2), nullable=False)
    description = Column(String(255), nullable=False)
    related_account_number = Column(String(20), nullable=True)
    reference_id = Column(String(36), nullable=True)  # Links paired transfer ledger rows
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

    account = relationship("Account", back_populates="transactions")