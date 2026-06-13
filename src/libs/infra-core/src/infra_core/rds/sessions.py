import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker


def _build_database_url() -> str:
    if database_url := os.getenv("DATABASE_URL"):
        return database_url

    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "app"),
        password=os.getenv("DB_PASSWORD", "app"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "app"),
    ).render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(
        _build_database_url(),
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_local() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)
