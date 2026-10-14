"""Centralized audit logging helper."""

import datetime
from database.connection import get_db
from models.audit import AuditLog


class AuditService:
    @staticmethod
    def log(actor: str, action: str, details: str):
        try:
            with get_db() as db:
                entry = AuditLog(actor_username=actor, action=action, details=details)
                db.add(entry)
        except Exception as e:
            print(f"[Audit Failure] Could not write audit log: {e}")