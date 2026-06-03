from collections.abc import Callable
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from personal_context_mcp.config.settings import get_settings


def create_session_factory(database_url: str, *, echo: bool = False) -> Callable[[], Session]:
    engine = create_engine(database_url, echo=echo, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@lru_cache
def get_session_factory() -> Callable[[], Session]:
    settings = get_settings()
    return create_session_factory(
        settings.database_url,
        echo=settings.sql_echo,
    )


def get_db_session() -> Session:
    return get_session_factory()()
