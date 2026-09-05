from __future__ import annotations
from sqlalchemy.orm import Session
from .chain_service import effective_id
from .engine import state_for_point
from .validation_service import validate_backup
from ..models import BackupPoint

def restore_to_recovery_point(db: Session, recovery_point_id: str) -> dict:
    target = db.get(BackupPoint, recovery_point_id)
    if target is None: raise ValueError("recovery point not found")
    chain = []; current = target
    while current:
        actual = db.get(BackupPoint, effective_id(db, current.id))
        result = validate_backup(db, actual)
        if not result["valid"]: return {"restored": False, "recovery_point_id": current.id, "errors": result["errors"]}
        chain.append(actual); current = db.get(BackupPoint, current.parent_id) if current.parent_id else None
    state = state_for_point(db, target)
    return {"restored": True, "recovery_point_id": target.id, "files": sorted(state.values(), key=lambda item: item["file_id"])}

def verify_restored_state(restored: dict, expected: dict) -> dict:
    actual = {item["file_id"]: item for item in restored.get("files", [])}
    wanted = {item["file_id"]: item for item in expected.get("files", [])}
    mismatches = []
    if set(actual) != set(wanted): mismatches.append({"expected_file_ids": sorted(wanted), "actual_file_ids": sorted(actual)})
    for file_id in sorted(set(actual) & set(wanted)):
        if actual[file_id].get("content_hash") != wanted[file_id].get("content_hash") or actual[file_id].get("version") != wanted[file_id].get("version"): mismatches.append({"file_id": file_id, "reason": "content or version mismatch"})
    return {"verified": not mismatches, "mismatches": mismatches}
