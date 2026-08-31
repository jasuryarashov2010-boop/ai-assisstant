from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
