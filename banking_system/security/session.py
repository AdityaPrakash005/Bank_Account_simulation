"""Thread-safe session state tracking with auto-expiry monitor."""

import datetime
from typing import Optional
from config import Config


class UserSession:
    def __init__(self, user_id: str, username: str, role: str, full_name: str):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.full_name = full_name
        self.last_activity = datetime.datetime.now(datetime.timezone.utc)
        self.login_timestamp = datetime.datetime.now(datetime.timezone.utc)

    def record_activity(self) -> None:
        self.last_activity = datetime.datetime.now(datetime.timezone.utc)

    def is_expired(self) -> bool:
        idle_duration = datetime.datetime.now(datetime.timezone.utc) - self.last_activity
        return idle_duration.total_seconds() > (Config.SESSION_TIMEOUT_MINUTES * 60)


class SessionManager:
    _current_session: Optional[UserSession] = None

    @classmethod
    def create_session(cls, user_id: str, username: str, role: str, full_name: str) -> UserSession:
        cls._current_session = UserSession(user_id, username, role, full_name)
        return cls._current_session

    @classmethod
    def get_session(cls) -> Optional[UserSession]:
        if cls._current_session and cls._current_session.is_expired():
            cls.destroy_session()
            return None
        if cls._current_session:
            cls._current_session.record_activity()
        return cls._current_session

    @classmethod
    def destroy_session(cls) -> None:
        cls._current_session = None