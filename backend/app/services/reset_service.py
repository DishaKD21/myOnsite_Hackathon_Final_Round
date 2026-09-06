from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from .. import database
from ..models import BackupChange, BackupPoint, Resolution


def reset_runtime_data(db: Session) -> dict[str, int | str]:
    """Development-only reset for an empty user-owned source state."""
    db.query(BackupChange).delete()
    db.query(Resolution).delete()
    db.query(BackupPoint).delete()
    db.commit()

    for directory in (database.SOURCE_DIR, database.BACKUPS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
        for item in directory.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    return {"status": "reset", "backup_points": 0, "backup_changes": 0, "resolutions": 0, "source_files": 0, "backup_artifacts": 0}