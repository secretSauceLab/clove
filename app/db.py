import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def build_database_url() -> str:
    # If explicitly set, honor it (local dev, tests, etc.)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    db_name = os.getenv("DB_NAME", "advocacy")
    db_user = os.getenv("DB_USER", "advocacy")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST")  # e.g. /cloudsql/<connectionName> in Cloud Run

    # Cloud Run + Cloud SQL connector mounts a unix socket at /cloudsql/...
    if db_host and db_host.startswith("/cloudsql/"):
        return (
            f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@/"
            f"{quote_plus(db_name)}?host={quote_plus(db_host)}"
        )

    # TCP fallback for local/dev
    host = db_host or "localhost"
    return f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@{host}/{quote_plus(db_name)}"


DATABASE_URL = build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()