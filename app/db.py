# app/db.py
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool


class Settings(BaseSettings):
    # Accept a full DATABASE_URL directly (local dev, tests, CI)
    database_url: str = ""

    # Or build it from discrete parts (Cloud Run style)
    db_name: str = "advocacy"
    db_user: str = "advocacy"
    db_password: str = ""
    db_host: str = ""

    # Connection pool config
    db_pool_size: int = 5
    db_max_overflow: int = 2

    # API key
    api_key: str = ""

    @computed_field
    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        if self.db_host.startswith("/cloudsql/"):
            return (
                f"postgresql+psycopg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}@/"
                f"{quote_plus(self.db_name)}?host={quote_plus(self.db_host)}"
            )

        host = self.db_host or "localhost"
        return (
            f"postgresql+psycopg://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{host}/{quote_plus(self.db_name)}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()


engine = create_async_engine(
    settings.effective_database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as db:
        yield db