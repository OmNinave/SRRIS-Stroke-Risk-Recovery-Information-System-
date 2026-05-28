from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Issue 4 Fix: Absolute path — always resolves to backend/srris_production_v5.db
# regardless of the CWD that uvicorn is launched from.
_DB_DIR = os.path.dirname(os.path.abspath(__file__))          # .../app/db/
_DB_PATH = os.path.join(_DB_DIR, "..", "..", "srris_production_v5.db")  # .../backend/
_DB_PATH = os.path.normpath(_DB_PATH)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{_DB_PATH}"
# For PostgreSQL later: "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=pool.NullPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
