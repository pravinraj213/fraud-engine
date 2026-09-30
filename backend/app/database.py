from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def configure_database(url: str) -> Engine:
    """Point SessionLocal at another database (used by tests)."""
    new_engine = make_engine(url)
    SessionLocal.configure(bind=new_engine)
    return new_engine


def create_tables() -> None:
    import app.models  # noqa: F401  (registers the tables on Base.metadata)

    Base.metadata.create_all(SessionLocal.kw["bind"])


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
