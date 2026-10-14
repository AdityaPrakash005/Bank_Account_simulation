"""Database engine and transaction lifecycle coordinator."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from config import Config
from models.base import Base

engine = create_engine(Config.DATABASE_URL, echo=Config.DB_ECHO, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database context with auto-rollback."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()