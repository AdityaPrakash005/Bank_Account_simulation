"""Cryptographic operations implementing PBKDF2-HMAC-SHA256 and constant-time checks."""

import hashlib
import hmac
import secrets
from typing import Tuple
from config import Config


class CryptoManager:
    @staticmethod
    def generate_salt(length: int = 32) -> str:
        """Generates a cryptographically strong hex salt."""
        return secrets.token_hex(length)

    @classmethod
    def hash_pin(cls, pin: str, salt: str | None = None) -> Tuple[str, str]:
        """Derives a key using PBKDF2-HMAC-SHA256 with 260,000 rounds."""
        if salt is None:
            salt = cls.generate_salt()
        derived_key = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=pin.encode("utf-8"),
            salt=salt.encode("utf-8"),
            iterations=Config.PBKDF2_ITERATIONS,
        )
        return derived_key.hex(), salt

    @classmethod
    def verify_pin(cls, input_pin: str, stored_hash: str, salt: str) -> bool:
        """Verifies a PIN in constant time to thwart timing attacks."""
        check_hash, _ = cls.hash_pin(input_pin, salt)
        return hmac.compare_digest(check_hash, stored_hash)

    @staticmethod
    def generate_account_number() -> str:
        """Generates a cryptographically uniform 10-digit account number."""
        return str(secrets.randbelow(9000000000) + 1000000000)