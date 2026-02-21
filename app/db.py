import os
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


def build_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    db_name = os.getenv("DB_NAME", "advocacy")
    db_user = os.getenv("DB_USER", "advocacy")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST")

    if db_host and db_host.startswith("/cloudsql/"):
        return (
            f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@/"
            f"{quote_plus(db_name)}?host={quote_plus(db_host)}"
        )

    host = db_host or "localhost"
    return f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@{host}/{quote_plus(db_name)}"


DATABASE_URL = build_database_url()

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as db:
        yield db