"""Central application configuration loaded from environment or defaults."""

from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class AppConfig:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/banking_system.db")
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() in ("true", "1")

    # Security
    MAX_FAILED_LOGINS: int = int(os.getenv("MAX_FAILED_LOGINS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "15"))
    HIGH_VALUE_THRESHOLD: float = float(os.getenv("HIGH_VALUE_THRESHOLD", "1000.00"))
    PBKDF2_ITERATIONS: int = 260_000

    # Paths
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    LOGS_DIR: Path = BASE_DIR / "logs"


Config = AppConfig()
Config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)