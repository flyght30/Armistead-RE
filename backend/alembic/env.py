from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.database import engine, Base

target_metadata = Base.metadata

async def run_migrations_offline():
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = engine

    async with connectable.connect() as connection:
        await connection.run_sync(target_metadata.create_all)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
