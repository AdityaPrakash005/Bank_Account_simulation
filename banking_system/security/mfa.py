"""Simulated cryptographically secure Multi-Factor Authentication."""

import datetime
import secrets
from typing import Dict, Optional


class MFAService:
    _otp_cache: Dict[str, Dict] = {}  # {user_id: {"otp": str, "expires": datetime}}

    @classmethod
    def generate_otp(cls, user_id: str, lifetime_seconds: int = 180) -> str:
        otp = f"{secrets.randbelow(900000) + 100000:06d}"
        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=lifetime_seconds)
        cls._otp_cache[user_id] = {"otp": otp, "expires": expires}
        return otp

    @classmethod
    def verify_otp(cls, user_id: str, candidate_otp: str) -> bool:
        entry = cls._otp_cache.get(user_id)
        if not entry:
            return False

        if datetime.datetime.now(datetime.timezone.utc) > entry["expires"]:
            del cls._otp_cache[user_id]
            return False

        is_valid = secrets.compare_digest(entry["otp"], candidate_otp.strip())
        if is_valid:
            del cls._otp_cache[user_id]
        return is_valid