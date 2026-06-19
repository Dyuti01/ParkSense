import sys
import os
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..")
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env"), override=True)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.config import settings
from app.models.user import User
from app.routers.auth import get_password_hash
from datetime import datetime, timezone

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        
        if user:
            print("User 'admin' already exists.")
            # Reset password just in case
            user.hashed_password = get_password_hash("password123")
            await session.commit()
            print("Reset password to 'password123'")
        else:
            new_user = User(
                username="admin",
                email="admin@parksense.ai",
                hashed_password=get_password_hash("password123"),
                full_name="System Administrator",
                role="admin",
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
            await session.commit()
            print("Created test user: username='admin', password='password123'")
            
if __name__ == "__main__":
    asyncio.run(main())
