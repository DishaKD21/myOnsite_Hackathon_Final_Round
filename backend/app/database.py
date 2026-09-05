from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("BACKUPCHAIN_DATA_DIR", BASE_DIR / "data"))
BACKUPS_DIR = DATA_DIR / "backups"
SOURCE_DIR = DATA_DIR / "source"
DATABASE_URL = os.getenv("BACKUPCHAIN_DATABASE_URL", f"sqlite:///{DATA_DIR / 'backupchain.db'}")

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Session:
    return SessionLocal()

def init_db() -> None:
    from .models import BackupPoint, BackupChange, Resolution
    Base.metadata.create_all(bind=engine)
