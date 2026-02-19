import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from urllib.parse import quote_plus

def _build_database_url() -> str:
    # 1) Prefer explicit DATABASE_URL if present (local/dev/docker)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # 2) Otherwise build from parts (Cloud Run / Cloud SQL)
    # We will use a unix socket path via '?host=' which psycopg supports well.
    db_name = os.getenv("DB_NAME", "advocacy")
    db_user = os.getenv("DB_USER", "advocacy")
    db_pass = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST")  # expected: /cloudsql/<connectionName> OR hostname

    if db_host and db_host.startswith("/cloudsql/"):
        # unix socket connection
        return (
            f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@/"
            f"{quote_plus(db_name)}?host={quote_plus(db_host)}"
        )

    # TCP fallback (local dev, etc.)
    db_host = db_host or "localhost"
    return f"postgresql+psycopg://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}/{quote_plus(db_name)}"

DATABASE_URL = _build_database_url()

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()