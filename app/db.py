# app/db.py
from urllib.parse import quote_plus

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = ""
    db_name: str = "advocacy"
    db_user: str = "advocacy"
    db_password: str = ""
    db_host: str = ""
    db_pool_size: int = 5
    db_max_overflow: int = 2
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