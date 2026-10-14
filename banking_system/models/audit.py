"""Security audit trail for non-repudiation."""

import datetime
import uuid
from sqlalchemy import Column, DateTime, String
from models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(String(500), nullable=False)
    ip_address = Column(String(45), default="127.0.0.1", nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)