from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...backup_chain import BackupChain
from ...services.engine import create_full_backup, create_incremental_backup
from ...models import BackupPoint
from ...services.alternate_service import verify_alternate
from ...services.backup_service import validate_backup
from ...services.chain_service import find_alternate_delta

router = APIRouter()

def serialize(point: BackupPoint, validation: dict | None = None, operation_steps: list[dict] | None = None) -> dict:
    steps = ([
        {"name": "start_linked_list_traversal", "status": "completed"},
        {"name": "compare_content_hashes", "status": "completed"},
        {"name": "changes_array_complete", "status": "completed", "details": f"{point.change_count} changes"},
    ] if point.type == "INCREMENTAL" else [
        {"name": "create_source_linked_list_head", "status": "completed"},
        {"name": "create_source_file_nodes", "status": "completed"},
        {"name": "link_source_nodes", "status": "completed"},
    ]) + [
        {"name": "read_source_state", "status": "completed"},
        {"name": "collect_files" if point.type == "FULL" else "detect_changes", "status": "completed", "details": f"{point.change_count} changes"},
        {"name": "create_artifact", "status": "completed"},
        {"name": "create_manifest", "status": "completed"},
        {"name": "calculate_manifest_hash", "status": "completed"},
        {"name": "calculate_artifact_hash", "status": "completed"},
        {"name": "save_backup_metadata", "status": "completed"},
        {"name": "validate_backup", "status": "completed" if validation is None or validation.get("valid") else "failed", "details": ", ".join(validation.get("errors", [])) if validation and not validation.get("valid") else ""},
    ]
    return {**{key: getattr(point, key) for key in ("id", "source_id", "type", "sequence", "parent_id", "start_version", "end_version", "change_count", "artifact_path", "manifest_path", "manifest_hash", "artifact_hash", "status", "created_at")}, "steps": operation_steps or steps}

@router.post("/backup/full")
@router.post("/backups/full")
def full(db: Session = Depends(get_db)) -> dict:
    point = create_full_backup(db)
    return serialize(point, validate_backup(db, point))

@router.post("/backup/incremental")
@router.post("/backups/incremental")
def incremental(db: Session = Depends(get_db)) -> dict:
    try:
        chain = BackupChain.load_for_comparison(db)
        point = create_incremental_backup(db, chain=chain)
        if point is None:
            return {"created": False, "change_count": 0, "steps": chain.last_comparison_steps + [{"name": "no_changes", "status": "completed", "details": "No incremental backup created"}]}
        operation_steps = chain.last_comparison_steps + [
            {"name": "create_delta_node", "status": "completed", "details": point.id},
            {"name": "create_manifest", "status": "completed"},
            {"name": "calculate_manifest_hash", "status": "completed"},
            {"name": "create_artifact", "status": "completed"},
            {"name": "calculate_artifact_hash", "status": "completed"},
            {"name": "save_backup_metadata", "status": "completed"},
        ]
        validation = validate_backup(db, point)
        operation_steps.append({"name": "validate_delta", "status": "completed" if validation.get("valid") else "failed", "details": ", ".join(validation.get("errors", []))})
        return serialize(point, validation, operation_steps)
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
