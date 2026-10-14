"""Authentication, PIN changes, and lockout logic."""

import datetime
from typing import Optional, Tuple
from config import Config
from database.connection import get_db
from models.user import User, UserRole
from security.crypto import CryptoManager
from security.session import SessionManager, UserSession
from services.audit_service import AuditService


class AuthService:
    @staticmethod
    def authenticate(username: str, pin: str) -> Tuple[bool, str, Optional[UserSession]]:
        with get_db() as db:
            user = db.query(User).filter(User.username == username.strip()).first()
            if not user:
                return False, "Invalid account username or credentials.", None

            now = datetime.datetime.utcnow()
            if user.lockout_until and user.lockout_until > now:
                remaining = int((user.lockout_until - now).total_seconds() // 60) + 1
                return False, f"Account is locked. Try again in {remaining} minute(s).", None

            if not user.is_active:
                return False, "This profile has been deactivated. Contact an administrator.", None

            # Constant-time verification
            if not CryptoManager.verify_pin(pin, user.pin_hash, user.pin_salt):
                user.failed_attempts += 1
                AuditService.log(user.username, "FAILED_LOGIN", f"Attempt #{user.failed_attempts}")
                if user.failed_attempts >= Config.MAX_FAILED_LOGINS:
                    user.lockout_until = now + datetime.timedelta(minutes=Config.LOCKOUT_DURATION_MINUTES)
                    AuditService.log(user.username, "ACCOUNT_LOCKED", "Exceeded max failed login attempts")
                    return (
                        False,
                        f"Account locked for {Config.LOCKOUT_DURATION_MINUTES} minutes due to repeated failed logins.",
                        None,
                    )
                return False, f"Invalid PIN. {Config.MAX_FAILED_LOGINS - user.failed_attempts} attempt(s) remain.", None

            # Reset attempts on success
            user.failed_attempts = 0
            user.lockout_until = None
            session = SessionManager.create_session(user.id, user.username, user.role, user.full_name)
            AuditService.log(user.username, "AUTH_SUCCESS", "User authenticated successfully")
            return True, "Authentication successful.", session

    @staticmethod
    def change_pin(user_id: str, old_pin: str, new_pin: str) -> Tuple[bool, str]:
        if len(new_pin) < 4 or not new_pin.isdigit():
            return False, "New PIN must be at least 4 digits (numeric only)."

        with get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found."

            if not CryptoManager.verify_pin(old_pin, user.pin_hash, user.pin_salt):
                AuditService.log(user.username, "PIN_CHANGE_FAIL", "Invalid old PIN provided")
                return False, "Incorrect existing PIN."

            new_hash, new_salt = CryptoManager.hash_pin(new_pin)
            user.pin_hash = new_hash
            user.pin_salt = new_salt
            AuditService.log(user.username, "PIN_CHANGE_SUCCESS", "PIN successfully rotated")
            return True, "Security PIN has been updated successfully."