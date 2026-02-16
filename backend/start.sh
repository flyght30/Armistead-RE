#!/bin/sh
set -e

echo "Waiting for database to be ready..."
python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def wait():
    url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://user:pass@db/ttc')
    for i in range(30):
        try:
            engine = create_async_engine(url)
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            await engine.dispose()
            print('Database ready!')
            return
        except Exception as e:
            print(f'  attempt {i+1}/30: {e}')
            await asyncio.sleep(2)
    print('WARNING: database not ready after 60s')

asyncio.run(wait())
"

echo "Running database seed..."
python seed.py || echo "Seed skipped or already applied."

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
