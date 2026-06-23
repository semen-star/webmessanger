from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite локально — файл появится в папке backend/
DATABASE_URL = "sqlite:///./semkames.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # нужно для SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency — получить сессию БД, закрыть после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
