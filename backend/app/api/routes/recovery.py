from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...services.recovery_service import restore_to_recovery_point, verify_restored_state
from ...models import BackupPoint
from ...schemas.recovery import RestoreInput
from ...services.source_service import SourceService
from ...database import SOURCE_DIR

router = APIRouter()
source = SourceService(SOURCE_DIR)

@router.get("/recovery-points")
def recovery_points(db: Session = Depends(get_db)) -> list[dict]:
    return [{key: getattr(item, key) for key in ("id", "source_id", "type", "sequence", "parent_id", "start_version", "end_version", "change_count", "artifact_path", "manifest_path", "manifest_hash", "artifact_hash", "status", "created_at")} for item in db.query(BackupPoint).order_by(BackupPoint.sequence).all()]

@router.post("/restore")
def restore(item: RestoreInput, db: Session = Depends(get_db)):
    try:
        return restore_to_recovery_point(db, item.recovery_point_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.post("/restore/verify")
def restore_verify(item: RestoreInput, db: Session = Depends(get_db)):
    result = restore_to_recovery_point(db, item.recovery_point_id)
    return verify_restored_state(result, source.state()) if result.get("restored") else result
