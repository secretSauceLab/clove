import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

def _build_database_url() -> str:
    # Prefer explicit DATABASE_URL if present (local/dev/docker)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Cloud Run / Cloud SQL connector style (unix socket)
    host = os.getenv("DB_HOST", "localhost")
    name = os.getenv("DB_NAME", "advocacy")
    user = os.getenv("DB_USER", "advocacy")
    password = os.getenv("DB_PASSWORD", "advocacy")

    # psycopg v3 URL
    return f"postgresql+psycopg://{user}:{password}@{host}/{name}"

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