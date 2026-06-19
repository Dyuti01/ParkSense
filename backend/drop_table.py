import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def drop():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(text('DROP TABLE IF EXISTS heatmap_grid CASCADE'))

if __name__ == '__main__':
    asyncio.run(drop())
    print("Table dropped successfully")
