from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# Строка подключения для SQLite
DATABASE_URL = "sqlite:///ecommerce.db"

# Создаём Engine
engine = create_engine(DATABASE_URL, echo=True)

# Настраиваем фабрику сеансов
SessionLocal = sessionmaker(bind=engine)

#####################################
# Асинхронная работа с базой данных #
#####################################

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


DATABASE_URL = "postgresql+asyncpg://ecommerce_user:postgres@localhost/ecommerce_db"

async_engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = async_sessionmaker(
    async_engine, autoflush=False, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass
