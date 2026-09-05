from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class BackupPoint(Base):
    __tablename__ = "backup_points"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(120), default="demo-source", index=True)
    type: Mapped[str] = mapped_column(String(20))
    sequence: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("backup_points.id"), nullable=True)
    start_version: Mapped[int] = mapped_column(Integer)
    end_version: Mapped[int] = mapped_column(Integer)
    change_count: Mapped[int] = mapped_column(Integer)
    artifact_path: Mapped[str] = mapped_column(Text)
    manifest_path: Mapped[str] = mapped_column(Text)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    artifact_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="VALID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    changes: Mapped[list["BackupChange"]] = relationship(back_populates="backup", cascade="all, delete-orphan")

class BackupChange(Base):
    __tablename__ = "backup_changes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    backup_id: Mapped[str] = mapped_column(ForeignKey("backup_points.id"), index=True)
    file_id: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text)
    backup: Mapped[BackupPoint] = relationship(back_populates="changes")

class Resolution(Base):
    __tablename__ = "resolutions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    original_id: Mapped[str] = mapped_column(String(120), index=True)
    replacement_id: Mapped[str] = mapped_column(String(120))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
