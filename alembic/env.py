import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from alembic import context

from app.db import Base
from app import models, models_prior_auth 

target_metadata = Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection — generates raw SQL instead.
    Useful for reviewing what will run before applying it.
    Run with: alembic upgrade head --sql
    """
    url = os.environ["DATABASE_URL"]
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:               
    """Creates an async engine and runs migrations via run_sync()."""
    connectable = create_async_engine(                  
        os.environ["DATABASE_URL"],
        poolclass=NullPool,                            
    )

    async with connectable.connect() as connection:     
        await connection.run_sync(do_run_migrations)    


def do_run_migrations(connection) -> None:              
    """
    The actual Alembic migration call — must be a plain sync function
    because Alembic's internals are synchronous.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:                    
    asyncio.run(run_async_migrations())                 


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

