from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Automatically reconnect if the database dropped the connection
    pool_recycle=1800,       # Recycle connections every 30 minutes
    pool_size=5,             # Keep 5 connections open
    max_overflow=10          # Allow up to 10 extra temporary connections
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
