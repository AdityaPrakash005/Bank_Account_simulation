"""Dynamically configurable system parameters and fee schedules."""

from sqlalchemy import Column, Float, String
from models.base import Base


class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String(50), primary_key=True)
    value = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)