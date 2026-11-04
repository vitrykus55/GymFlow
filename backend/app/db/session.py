from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session; callers own and explicitly commit transactions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Closing an uncommitted Session rolls back its active transaction
        # and releases the connection.
        db.close()
