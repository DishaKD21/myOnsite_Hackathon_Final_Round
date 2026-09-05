from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...services.engine import create_full_backup, create_incremental_backup
from ...models import BackupPoint
from ...services.alternate_service import verify_alternate
from ...services.backup_service import validate_backup
from ...services.chain_service import find_alternate_delta

router = APIRouter()

def serialize(point: BackupPoint) -> dict:
    return {key: getattr(point, key) for key in ("id", "source_id", "type", "sequence", "parent_id", "start_version", "end_version", "change_count", "artifact_path", "manifest_path", "manifest_hash", "artifact_hash", "status", "created_at")}

@router.post("/backup/full")
def full(db: Session = Depends(get_db)) -> dict:
    return serialize(create_full_backup(db))

@router.post("/backup/incremental")
def incremental(db: Session = Depends(get_db)) -> dict:
    try:
        return serialize(create_incremental_backup(db))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.get("/backups")
def backups(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize(item) for item in db.query(BackupPoint).order_by(BackupPoint.sequence).all()]

@router.get("/backups/{backup_id}")
def backup(backup_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(BackupPoint, backup_id)
    if not item:
        raise HTTPException(404, "backup not found")
    return serialize(item)

@router.post("/backups/{backup_id}/validate")
def validate(backup_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(BackupPoint, backup_id)
    if not item:
        raise HTTPException(404, "backup not found")
    return validate_backup(db, item)

@router.post("/backups/{backup_id}/find-alternate")
def find_alternate(backup_id: str, db: Session = Depends(get_db)) -> dict:
    item = db.get(BackupPoint, backup_id)
    if not item:
        raise HTTPException(404, "backup not found")
    return {"original_delta": backup_id, "candidates": [serialize(candidate) for candidate in find_alternate_delta(db, item)]}

@router.post("/backups/{backup_id}/verify-alternate")
def verify_alt(backup_id: str, alternate_id: str, db: Session = Depends(get_db)) -> dict:
    original, alternate = db.get(BackupPoint, backup_id), db.get(BackupPoint, alternate_id)
    if not original or not alternate:
        raise HTTPException(404, "backup not found")
    return verify_alternate(db, original, alternate)
